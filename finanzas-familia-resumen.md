# FinanzasFamilia — Resumen de diseño

> Documento generado tras la sesión de diseño inicial y revisado en sesiones posteriores. Recoge todas las decisiones tomadas y los motivos detrás de ellas.

---

## 1. Objetivo de la aplicación

Aplicación web para gestionar las finanzas domésticas de una familia entera. Los dos pilares fundamentales son:

- **Facilidad de entrada de datos** — si meter gastos es tedioso, la app se abandona.
- **Buena categorización** — para poder explotar los datos y ver dónde se puede ahorrar.

---

## 2. Requisitos generales

| Elemento | Decisión |
|----------|----------|
| Tipo de app | Web responsive (funciona en PC y móvil) + App Android ligera (listener) |
| Usuarios | Familia entera (varios miembros, identificados por `chat_id` de Telegram) |
| Backend | Python + FastAPI |
| Frontend | HTML/JS estático (Alpine.js + Chart.js), servido por Nginx |
| Base de datos | SQLite (fichero propio, separado del SQLite de JupyterLab) |
| Despliegue | Docker, en servidor Debian con Proxmox |
| Acceso remoto | Tailscale (VPN privada, sin puertos abiertos) |
| Autenticación | No en v1 — acceso por Tailscale (red privada), identificación por `chat_id` de Telegram |
| Bancos | Santander, CaixaBank, Revolut, Revolut X |

---

## 3. Estructura de cuentas de la familia

| Cuenta | Titular | Uso |
|--------|---------|-----|
| Cuenta Antonio | Antonio | Nómina + gastos personales |
| Cuenta Lucía | Lucía | Nómina + gastos personales |
| Cuenta Común | Ambos | Aportación mensual de cada uno + gastos familiares (hipoteca, supermercado, luz, agua, academia, extraescolares...) |
| Tarjeta Hijo (Revolut) | Antonio (titular) | Monedero del hijo, con ingresos periódicos |

### Identificación del usuario

- **Telegram:** el `chat_id` identifica quién mete el gasto. Si en el futuro Lucía quiere gestionar sus finanzas, solo tiene que hablarle al bot.
- **App Android (Wallet Listener):** identifica al usuario por el dispositivo donde está instalada. Identifica la cuenta por los últimos 4 dígitos de la tarjeta (configurables).
- **Importación CSV:** al importar, se selecciona manualmente a qué cuenta pertenece el fichero.
- **Web:** no requiere login en v1.

### Vistas de análisis

- Gastos de Antonio (cuenta personal)
- Gastos de Lucía (cuenta personal)
- Gastos comunes (cuenta común)
- Gastos del hijo (tarjeta Revolut)
- Gasto total familia (suma de todo)

---

## 4. Infraestructura

### Servidor
- Proxmox con dos máquinas virtuales:
  - **Debian con Docker** — aquí vivirá la app (junto a JupyterLab y Kryptonite)
  - **Home Assistant** — posible integración futura para notificaciones push

### Stack Docker — v1 (mínimo viable)

```
finanzas-familia/
  ├── api        → FastAPI + SQLite  (un solo contenedor)
  └── frontend   → Nginx sirviendo HTML/JS estático (Alpine.js + Chart.js)
```

**Solo dos contenedores.** Sin Traefik, sin AdGuard, sin Redis, sin Celery.

El contenedor `api` solo expone el API REST. **No incluye lógica de Telegram.** La integración con Telegram se gestiona fuera del código de FiDo, mediante la infraestructura de automatización ya existente (ver sección 5).

### Integración con Telegram (infraestructura externa)

Telegram no vive dentro de FiDo. Se reutiliza la misma arquitectura que ya funciona en el proyecto Kryptonite:

```
Entrada:   Telegram Bot → Node-RED (polling) → n8n (parseo + parámetros) → API de FiDo
Respuesta:                                      n8n (monta respuesta)     → Telegram Bot
```

Node-RED solo interviene en la entrada (polling). La respuesta la envía n8n directamente a Telegram.

| Componente | Responsabilidad |
|------------|-----------------|
| **Telegram Bot** | Recibe mensajes del usuario (comandos y texto libre) |
| **Node-RED** | Polling automático de Telegram. Enruta mensajes a n8n |
| **n8n** | Parsea el comando/texto, extrae parámetros, llama al API de FiDo, monta y envía la respuesta a Telegram |
| **API de FiDo** | Recibe la petición HTTP y registra el movimiento |

**Ventaja:** toda la lógica de Telegram se gestiona visualmente desde Node-RED y n8n, sin tocar código de la aplicación. Solo hay JavaScript ligero para parsear comandos y montar textos de respuesta.

### Persistencia de datos

El fichero SQLite vive en un **volumen Docker montado**, fuera del contenedor:

```yaml
volumes:
  - ./data:/app/data
```

Esto garantiza que los datos sobreviven a `docker-compose down`, actualizaciones y recreaciones de contenedores.

### Acceso

| Desde | URL |
|-------|-----|
| En casa | `http://192.168.x.x:8080` |
| Fuera de casa | `http://100.x.x.x:8080` (Tailscale activo) |
| Móvil día a día | Bot de Telegram (sin necesidad de Tailscale) |
| Móvil automático | App Android Wallet Listener → local + sync (WiFi casa / Tailscale) |

### Elementos aparcados para versiones futuras
- **Traefik** — reverse proxy con dominios `.local`
- **AdGuard Home** — DNS local para toda la red
- **Celery + Redis** — tareas en background
- **Flower** — monitor de tareas

---

## 5. Entrada de datos — el elemento crítico

### Vía Bot de Telegram (móvil, día a día)

El método principal para gastos pequeños y cotidianos. Sin necesidad de VPN, sin abrir el navegador.

**Flujo:** el usuario escribe al bot → Node-RED captura el mensaje (polling) → n8n parsea y llama al API de FiDo → n8n monta y envía la respuesta directamente a Telegram. La lógica de Telegram está completamente fuera del código de FiDo (ver sección 4).

**Sintaxis:**

```
[importe] [concepto] [personal|comun]
```

- Sin signo = **gasto** (por defecto)
- Con `+` = **ingreso**
- Por defecto = **personal**

**Ejemplos:**

```
2.5 desayuno personal           → gasto de 2.50€, personal
150 mercadona comun             → gasto de 150€, cuenta común
+2500 nomina personal           → ingreso de 2500€, personal
+1200 aporte_cuenta_comun comun → ingreso de 1200€, cuenta común
1200 aporte_cuenta_comun personal → gasto de 1200€, personal
26 claude personal              → gasto de 26€, personal
90 academia_ingles comun        → gasto de 90€, cuenta común
```

**Comportamiento:**
- La fecha es **hoy** por defecto.
- El concepto ayuda a la categorización automática y a la deduplicación.
- Con el tiempo, las **reglas automáticas** categorizan solos los gastos habituales ("mercadona" → Supermercado, "gasolina" → Transporte...).
- El `chat_id` del mensaje identifica al usuario (mismo mecanismo que en Kryptonite).

**Respuesta del bot:** confirma lo que ha entendido para verificar visualmente:

```
✓ 2.50€ | desayuno | Personal | Restauración > Cafeterías
```

### Vía App Android — Wallet Listener (móvil, automático)

Captura automática de gastos con tarjeta. Sin intervención del usuario: el gasto se registra en el momento de pagar.

**Cómo funciona:**

1. Google Wallet muestra una notificación tras cada pago con tarjeta (ej. "Pago de 45,30 € en MERCADONA con Visa ···1234").
2. La app Android, residente en background, intercepta la notificación usando la API `NotificationListenerService` de Android.
3. Parsea el contenido para extraer: **importe**, **comercio** y **últimos 4 dígitos de la tarjeta**.
4. Con los 4 últimos dígitos identifica a qué **cuenta** pertenece el gasto (mapeo configurable en la app).
5. **Guarda el gasto en local** (Room/SQLite del dispositivo) — esto ocurre siempre, garantizando que nunca se pierde un gasto.
6. **Intenta sincronizar** con el servidor FiDo (ver estrategia de sync más abajo).
7. Muestra una **notificación de confirmación** propia: `✓ 45.30€ | Mercadona | Alimentación > Supermercado` (indicando si se sincronizó o está pendiente).

**Datos extraídos de la notificación de Google Wallet:**

| Campo | Ejemplo | Uso |
|-------|---------|-----|
| Importe | 45,30 € | Importe del movimiento |
| Comercio | MERCADONA | Concepto + categorización automática |
| Tarjeta (4 últimos) | ···1234 | Identificar la cuenta (personal, común, etc.) |

**Configuración de la app Android:**

| Ajuste | Descripción |
|--------|-------------|
| IP del servidor FiDo | Dirección del servidor (IP de red local, ej. `192.168.1.x`) |
| IP Tailscale del servidor | Dirección Tailscale (ej. `100.x.x.x`) |
| SSID WiFi de casa | Para detectar automáticamente cuándo se está en la red local |
| Mapeo tarjeta → cuenta | Ej. ···1234 → "Cuenta Antonio", ···5678 → "Cuenta Común" |
| Miembro por defecto | Quién es el titular del dispositivo |

**Estrategia de sincronización (v1 — sin Supabase):**

La app **siempre** guarda en local primero. Después intenta sincronizar:

```
¿Puedo hacer ping al servidor FiDo? (IP local o IP Tailscale)
  └─ SÍ → Sync directo al API — vuelca todos los gastos pendientes
  └─ NO → Se queda en local, reintenta con el siguiente cambio de red
```

En la práctica: el usuario llega a casa, el móvil se conecta al WiFi, la app detecta el servidor y vuelca todo. Si necesita los datos antes, activa Tailscale manualmente.

**Cuándo se dispara la sincronización:**

| Evento | Acción |
|--------|--------|
| Nuevo gasto capturado | Intenta sync inmediato |
| Cambio de red (WiFi conectado/desconectado) | Reintenta sync de todo lo pendiente |
| Periódico (cada 15 min si hay pendientes) | Reintenta sync |
| Apertura manual de la app | Reintenta sync |

**Estados de un gasto en la app:**

| Estado | Significado | Icono |
|--------|-------------|-------|
| `pending` | Guardado en local, pendiente de sync | 🔴 |
| `synced` | Registrado en el servidor FiDo | 🟢 |

**Notificación de confirmación:**

```
✓ 45.30€ | Mercadona | Alimentación > Supermercado  🟢
✓ 12.00€ | Parking    | Transporte > Parking         🔴 (pendiente)
```

**Requisitos:**

- Permiso de Android: **"Acceso a notificaciones"** (se concede una vez en Ajustes).
- No requiere puertos abiertos ni Tailscale permanente.
- Funciona 100% offline — los gastos nunca se pierden.

**Tecnología:**

- App nativa Android en **Kotlin**.
- `NotificationListenerService` — captura de notificaciones de Google Wallet.
- `Room` — base de datos local SQLite del dispositivo.
- `WorkManager` — sincronización periódica y por eventos de red.
- `ConnectivityManager` — detección de cambios de red y ping al servidor.
- Retrofit/OkHttp — llamadas HTTP al API de FiDo.
- Sin interfaz compleja — solo una pantalla de configuración y lista de gastos pendientes.
- Servicio en foreground con notificación persistente para que Android no lo mate.

**Ventaja clave:** elimina por completo la necesidad de meter manualmente los gastos con tarjeta, que son la mayoría. El usuario paga y el gasto queda registrado. Sin depender de puertos abiertos ni VPN permanente. Solo quedan para entrada manual los gastos en efectivo (vía Telegram) y el histórico (vía CSV).

### Vía importación CSV (PC, periódicamente)

Para ponerse al día y para el histórico. Al importar, se selecciona a qué cuenta pertenece el CSV. Formatos soportados:
- **Santander** — formato CSV propio
- **CaixaBank** — formato CSV propio
- **Revolut** — formato CSV/Excel (incluye categorías propias de Revolut)
- **Revolut X** — exchange de crypto

### Vía formulario web manual (PC)

Para gastos que no pasan por el banco (efectivo, etc.) o correcciones.

### Edición y borrado de movimientos

Desde la web. No es algo diario, pero necesario para corregir errores. Una tabla de movimientos con opciones de editar y borrar.

### Lo que NO se hace en v1
- Conexión directa a APIs bancarias (PSD2) — demasiado mantenimiento
- OCR de tickets — resultado mediocre, más trabajo que beneficio
- Predicción de gastos con IA
- Informes PDF por email

---

## 6. Deduplicación de datos

**El problema:** un gasto puede llegar por varios canales (Telegram manual, Wallet Listener automático, CSV bancario). El mismo gasto podría duplicarse.

**La solución:** cada movimiento tiene una "huella" compuesta por importe + fecha ± 1 día + comercio (coincidencia aproximada). Al recibir un movimiento por cualquier canal, la app:

1. Busca coincidencias con entradas existentes.
2. Si encuentra una → muestra ambas y pregunta **"¿Es el mismo gasto?"** (en CSV) o fusiona automáticamente (Wallet Listener + CSV, al ser datos fiables de ambas fuentes).
3. Si el usuario confirma → fusiona los dos registros, conservando la categoría manual y los datos del banco.
4. Si no hay coincidencia → inserta el movimiento como nuevo.

**Origen del movimiento (`source`):** cada movimiento guarda por qué canal entró: `telegram`, `wallet_listener`, `csv_import`, `web_manual`. Esto facilita la deduplicación y la trazabilidad.

| Situación | Resultado |
|-----------|-----------|
| Telegram + CSV mismo gasto | Pregunta y fusiona |
| Wallet Listener + CSV mismo gasto | Fusión automática (ambos son datos bancarios fiables) |
| Telegram + Wallet Listener mismo gasto | Pregunta y fusiona (el manual podría ser diferente) |
| Entrada sin coincidencia | Se inserta normal |

---

## 7. Categorización

Árbol de dos niveles: **categoría principal → subcategoría**. Configurable desde la app (añadir, renombrar, eliminar, mover subcategorías).

### Categorías iniciales

**🏠 Hogar**
- Hipoteca
- Luz
- Agua
- Gas
- Internet
- Comunidad
- Seguro hogar
- Mantenimiento

**🛒 Alimentación**
- Supermercado
- Frutería
- Carnicería
- Panadería
- Otros alimentación

**🚗 Transporte**
- Combustible
- ITV
- Seguro coche
- Taller
- Transporte público
- Parking
- Peajes

**🍽️ Restauración**
- Restaurantes
- Cafeterías
- Comida rápida
- Comida a domicilio

**🏨 Viajes**
- Alojamiento
- Vuelos / Transporte
- Actividades
- Comidas en viaje

**🎭 Ocio**
- Cine / Teatro
- Suscripciones (Netflix, Spotify...)
- Deporte
- Eventos

**💊 Salud**
- Farmacia
- Médico
- Dentista
- Óptica
- Seguro médico

**👕 Ropa**
- Adultos
- Niños
- Calzado

**📚 Educación**
- Colegio
- Libros
- Extraescolares
- Academia

**🛠️ Tecnología**
- Software
- Hardware
- Suscripciones tech

**💰 Ingresos**
- Nómina
- Freelance
- Devoluciones
- Otros ingresos

**🔄 Transferencias**
- Aporte cuenta común

### Reglas de categorización automática

Las reglas se definen una vez y se aplican en cada importación CSV y en cada mensaje del bot. Son un mapeo de texto → categoría (ej. "mercadona" → Alimentación > Supermercado, "gasolina" → Transporte > Combustible).

---

## 8. Funcionalidades v1

### Imprescindibles
- [ ] Gestión de cuentas bancarias (alta, asociación a titular)
- [ ] Integración Telegram vía Node-RED + n8n (entrada rápida de gastos e ingresos)
- [ ] Flujo n8n: parseo de mensaje, llamada al API, respuesta de confirmación
- [ ] App Android Wallet Listener (captura automática de pagos con tarjeta)
- [ ] Importación CSV Santander, CaixaBank, Revolut
- [ ] Categorías editables en dos niveles (configurables desde la web)
- [ ] Reglas de categorización automática
- [ ] Deduplicación al importar y entre canales (Telegram, Wallet Listener, CSV)
- [ ] Edición y borrado de movimientos desde la web
- [ ] Dashboard con gráficas básicas (por categoría, por mes)
- [ ] Filtros por mes, categoría, cuenta y miembro

### Fuera de v1 (posibles v2, v3...)
- Supabase como cola cloud intermedia para el Wallet Listener (sync sin WiFi ni Tailscale)
- Autenticación (si más miembros de la familia usan la web)
- Telegram como dashboard (comandos tipo `/gastos marzo`, `/resumen semana`)
- Presupuestos mensuales con alertas
- Metas de ahorro
- Predicción de gastos con IA
- Informes PDF por email
- OCR de tickets
- Conexión directa a APIs bancarias (PSD2)
- Notificaciones push vía Home Assistant
- Traefik + AdGuard para acceso cómodo sin puertos

---

## 9. Filosofía del proyecto

> **"El uso dará pistas de qué necesito y dónde volcar los esfuerzos."**

- Empezar simple. Añadir complejidad solo si el uso real lo justifica.
- Dos contenedores Docker, no ocho.
- La app tiene que ser útil antes de ser perfecta.
- Si meter un gasto es tedioso, la app se abandona. La facilidad de entrada de datos es la prioridad número uno.
- **Tres canales de entrada, cada uno con su rol:**
  - **Wallet Listener** → gastos con tarjeta (automático, sin intervención).
  - **Telegram** → gastos en efectivo y ajustes manuales rápidos.
  - **CSV** → histórico, reconciliación y respaldo.
- La web es para consultar, importar y corregir.

---

## 10. Pendiente para arrancar el desarrollo

- [ ] Confirmar IP fija del servidor Debian
- [ ] Confirmar directorio de instalación (ej. `/opt/finanzas-familia`)
- [ ] Confirmar token del bot de Telegram (o si se crea uno nuevo)
- [ ] Revisar y ajustar las categorías iniciales
- [ ] Definir las reglas de categorización automática iniciales
- [ ] Confirmar SSID del WiFi de casa (para detección automática en la app Android)
- [ ] Verificar formato exacto de las notificaciones de Google Wallet en español

---

*Documento generado el 06/03/2026 — sesión de diseño inicial.*
*Revisado el 06/03/2026 — segunda sesión de revisión.*
*Revisado el 07/03/2026 — añadido canal Wallet Listener (app Android).*
*Revisado el 07/03/2026 — estrategia de sync por capas (local → API directo). Supabase aplazado a v2.*
*Revisado el 07/03/2026 — Telegram fuera del contenedor Docker. Integración vía Node-RED + n8n (patrón Kryptonite).*
