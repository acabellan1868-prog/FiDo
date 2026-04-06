# Changelog — FiDo (Finanzas Domésticas)

Registro de todos los cambios del proyecto, ordenado de más reciente a más antiguo.

---

## 2026-04-06

### Listener NTFY — captura automática de movimientos desde el móvil

Resuelve el problema de conectividad: el móvil no siempre está en la red local
y la VM de FiDo no tiene puertos abiertos al exterior ni TailScale permanente.
NTFY actúa de intermediario en la nube: Tasker publica en un topic privado,
FiDo escucha ese topic de forma continua y procesa cada mensaje como movimiento.

- **Añadido:** `app/servicios/ntfy_listener.py` — servicio de escucha SSE (Server-Sent
  Events, flujo de eventos del servidor) contra NTFY. Se ejecuta como tarea asyncio
  (asíncrona) en segundo plano dentro del proceso de FastAPI. Incluye:
  - Reconexión automática con espera exponencial (5s → 10s → … → 5 min máximo).
  - Recuperación de los últimos 12 horas al reconectar (`?since=12h`) para no
    perder movimientos durante caídas breves.
  - Resolución de cuenta en tres pasos: `cuenta_id` explícito → `ultimos4` en
    `mapeo_tarjetas` → `NTFY_CUENTA_DEFAULT`.
  - Auto-categorización mediante las reglas existentes.
  - Deduplicación usando el servicio ya existente (evita dobles entradas).
  - Logging (registro de eventos) detallado en el canal `fido.ntfy`.
- **Modificado:** `app/principal.py` — inicia y detiene la tarea NTFY en el
  ciclo de vida (lifespan) de la app. Llama a `migrar_bd()` antes de arrancar.
- **Modificado:** `app/bd.py` — nueva función `migrar_bd()` que detecta si la BD
  tiene el esquema antiguo y lo actualiza sin pérdida de datos (renombra la tabla,
  crea la nueva con el CHECK extendido y copia los registros).
- **Modificado:** `app/esquema.sql` — añadido `'ntfy'` al CHECK de `movimientos.origen`.
- **Modificado:** `requirements.txt` — añadida dependencia `httpx==0.27.0` para
  las peticiones HTTP asíncronas al servidor NTFY.
- **Modificado:** `CLAUDE.md` — documentadas las nuevas variables de entorno
  (`NTFY_URL`, `NTFY_TOPIC`, `NTFY_CUENTA_DEFAULT`) y el formato del mensaje JSON
  que debe enviar Tasker.

**Variables de entorno nuevas:**
```
NTFY_URL=https://ntfy.sh          # Servidor NTFY
NTFY_TOPIC=fido-mov-xxxxxxxx      # Topic privado (nombre largo = seguridad)
NTFY_CUENTA_DEFAULT=1             # ID de cuenta por defecto (opcional)
```

**Formato del mensaje que envía Tasker:**
```json
{
    "importe": -45.50,
    "descripcion": "Mercadona",
    "ultimos4": "1234",
    "fecha": "2026-04-06"
}
```

- Ficheros añadidos: `app/servicios/ntfy_listener.py`
- Ficheros modificados: `app/principal.py`, `app/bd.py`, `app/esquema.sql`,
  `requirements.txt`, `CLAUDE.md`, `roadmap.md`

---

## 2026-03-29

### Migración CSS: de Tailwind CDN a design system hogar.css

- **Eliminado:** Tailwind CDN (`<script src="https://cdn.tailwindcss.com">`) y su bloque `tailwind.config` con colores y radios personalizados. FiDo ya no depende de ningún CSS externo aparte de las fuentes de Google (que carga hogar.css).
- **Eliminado:** Todas las clases utilitarias de Tailwind (`flex`, `gap-3`, `grid-cols-2`, `px-4`, `text-sm`, `font-semibold`, `bg-white`, `text-green-600`, `rounded-xl`, `shadow`, etc.) del HTML.
- **Reescrito:** `static/estilos.css` — de 16 líneas a ~350 líneas, organizado en 20 secciones con clases propias prefijadas `fido-` que usan exclusivamente variables del design system (`--gap-md`, `--radio-sm`, `--surface-container`, `--fuente-titular`, etc.).
- **Nuevas clases CSS creadas:**
  - Utilidades: `fido-text-right`, `fido-text-center`, `fido-text-xs`, `fido-text-bold`, `fido-text-muted`, `fido-mono`, `fido-nowrap`
  - Inputs: `fido-input`, `fido-input--pill` (filtros), `fido-input--form` (formularios), `fido-input--sm`, `fido-input--flex`, `fido-input--buscar`
  - Layouts: `fido-filtros`, `fido-form-stack`, `fido-grid-2`, `fido-acciones-der`, `fido-resumen-grid`, `fido-graficas-grid`
  - Panel: `fido-resumen-tarjeta`, `fido-resumen-valor`, `fido-resumen-valor--exito`, `fido-resumen-valor--peligro`
  - Componentes: `fido-toast`, `fido-modal-overlay`, `fido-modal`, `fido-paginacion`, `fido-resultado`, `fido-lista`, `fido-cat-cabecera`, `fido-cat-hija`
  - Botones: `fido-btn-icono`, `fido-btn-texto`, `fido-boton--sm`, `fido-boton--xs`
  - Otros: `fido-titulo`, `fido-subtitulo`, `fido-label`, `fido-vacio`, `fido-footer`
- **Mantenidas:** Todas las clases del design system hogar.css (`hogar-tarjeta`, `hogar-boton`, `hogar-tabla`, `hogar-badge`, `hogar-alerta`, `hogar-header`, `hogar-drawer`, etc.).
- **Migrada:** La pestaña Crypto, que antes usaba clases Tailwind puras (`bg-white`, `text-gray-400`, `bg-gray-50`, `text-green-600`, `hover:bg-gray-50`), ahora usa `hogar-tabla-wrap` / `hogar-tabla` + clases `fido-`.
- **Resultado:** FiDo sigue ahora el mismo patrón que ReDo y MediDo: solo `hogar.css` + estilos propios, sin Tailwind.
- Ficheros modificados: `static/index.html`, `static/estilos.css`

---

## 2026-03-24

### Filtros avanzados y suma de movimientos
- **Mejorado:** El filtro de categoría ahora permite seleccionar una categoría padre ("▸ Todo Compras", etc.) para filtrar todos los movimientos de esa categoría y sus subcategorías, además de poder filtrar por subcategoría individual.
- **Añadido:** Nuevo filtro por tipo de movimiento: "Gastos e ingresos" (todos), "Solo gastos" o "Solo ingresos".
- **Añadido:** Suma total (Σ) de los movimientos filtrados visible junto a la paginación, con color verde (positivo) o rojo (negativo).
- **Refactorizado:** Extraída la lógica de construcción de filtros SQL a una función compartida `_construir_filtros()` para eliminar duplicación entre los endpoints `/movimientos` y `/movimientos/total`.
- **Mejorado:** El endpoint `/movimientos/total` ahora devuelve también la suma de importes además del conteo.
- Ficheros modificados: `app/rutas/movimientos.py`, `static/app.js`, `static/index.html`

---

## 2026-03-23

### Formulario de movimientos en modal emergente
- **Mejorado:** El formulario de nuevo/editar movimiento ahora se abre como ventana emergente (modal) centrada en pantalla, en lugar de aparecer encima de la tabla.
- **Ventaja:** Al editar un movimiento, no se pierde la posición en la tabla. Antes había que hacer scroll arriba para editar y luego volver abajo.
- **Añadido:** Cierre con tecla Escape, click fuera del modal o botón Cancelar.
- **Añadido:** Labels en cada campo del formulario para mayor claridad.
- **Añadido:** Transición suave de entrada/salida (fade).
- Ficheros modificados: `static/index.html`

---

## 2026-03-19

### Pestaña "₿ Crypto" — integración con Kryptonite
- **Añadido:** Nueva pestaña "₿ Crypto" en la navegación.
- **Añadido:** Tabla de portfolio con símbolo, inversión, valor actual y rentabilidad por moneda, con totales en pie de tabla.
- **Añadido:** Gráfica comparativa 24h cargada en segundo plano (no bloquea la tabla).
- **Añadido:** Estado "⏳ Cargando..." visible al entrar en la pestaña (`cargandoCrypto: true` por defecto).
- **Añadido:** Mensaje de error en rojo si Kryptonite no responde, con el motivo exacto.
- **Añadido:** Cache-busting en `api.js` y `app.js` (`?v=2`) para forzar recarga tras despliegue.
- Los datos se consumen de `/crypto/api/portafolio` y `/crypto/api/grafica24h` (proxy nginx en hogarOS).
- Ficheros modificados: `static/index.html`, `static/app.js`

### Parser CaixaBank — reescritura flexible
- **Corregido:** El parser antiguo usaba `;` como delimitador y esperaba 4 columnas fijas. El extracto real usa `,` con 6 columnas y campos entrecomillados.
- **Mejorado:** Nuevo diseño basado en cabeceras: detecta el delimitador automáticamente (`,`, `;`, tabulador) y localiza las columnas por nombre, no por posición.
- **Mejorado:** Compatible con cualquier número de columnas y orden arbitrario (exportación directa del banco o convertida desde Excel).
- **Mejorado:** Descripción construida combinando "Movimiento" + "Más datos" si existe.
- Ficheros modificados: `app/parsers/caixabank.py`

### Deduplicación — fix para movimientos idénticos en el mismo lote
- **Corregido:** Dos transacciones legítimas con misma fecha, importe y descripción dentro del mismo fichero (ej. dos recargas de 100€ el mismo día) eran incorrectamente marcadas: la segunda como duplicado de la primera.
- **Solución:** Contador de ocurrencias por huella dentro del lote. La primera ocurrencia usa la huella base; la segunda añade sufijo `_1`, la tercera `_2`, etc. Al reimportar el mismo fichero los sufijos coinciden y se detectan como duplicados correctamente.
- Ficheros modificados: `app/rutas/importar.py`

---

## 2026-03-10

### 14:30 — Fix gráficas pantalla completa + reglas categorización CaixaBank/Revolut
- **Corregido:** Gráficas no se mostraban en pantalla completa. Añadido contenedor con altura fija (300px) y `maintainAspectRatio: false`.
- **Añadido:** ~60 reglas de categorización nuevas para comercios habituales de CaixaBank y Revolut (Bk Hue, parkinglibre, Granier, Amazon, Claude.ai, etc.).
- **Añadido:** Las reglas nuevas se insertan automáticamente en cada arranque si no existen (idempotente).
- **Añadido:** Endpoint `POST /api/movimientos/recategorizar` para aplicar reglas a movimientos sin categoría.
- **Añadido:** Botón "Recategorizar" en la sección de importación.
- Ficheros modificados: `static/index.html`, `static/app.js`, `app/datos_iniciales.py`, `app/rutas/movimientos.py`

### 14:00 — Fix gráficas del panel no se renderizan
- **Corregido:** URL CDN de Chart.js apuntaba al paquete genérico, ahora apunta al UMD bundle específico.
- **Corregido:** `toFixed(2)` devolvía string en vez de número para datos del doughnut chart.
- **Corregido:** Protección contra `icono` null en etiquetas de categoría.
- Ficheros modificados: `static/index.html`, `static/app.js`

### 13:45 — Fix parser Revolut: soporte cabeceras en español + .gitignore temporal/
- **Corregido:** Parser Revolut ahora soporta cabeceras en español (Tipo, Importe, Descripción...) además de inglés.
- **Corregido:** Estado `COMPLETADO` aceptado además de `COMPLETED`.
- **Añadido:** Normalización automática de cabeceras ES→EN con mapeo interno.
- **Añadido:** Carpeta `temporal/` excluida de git (.gitignore).
- Ficheros modificados: `app/parsers/revolut.py`, `.gitignore`

### 13:15 — Parsers CaixaBank y Revolut para importación CSV
- **Añadido:** `app/parsers/caixabank.py` — parser para extractos CaixaBank (CSV con `;`, formato español).
- **Añadido:** `app/parsers/revolut.py` — parser para extractos Revolut (CSV con `,`, formato inglés, filtra solo Completed).
- **Añadido:** Registrar ambos parsers en `app/rutas/importar.py`.
- **Corregido:** Opciones CaixaBank y Revolut habilitadas en el selector de banco de importación (ya no dicen "próximamente").
- Ficheros modificados: `app/parsers/caixabank.py`, `app/parsers/revolut.py`, `app/rutas/importar.py`, `static/index.html`

### 12:30 — Gestión completa de cuentas en Ajustes (editar y borrar)
- **Añadido:** Botones "Editar" y "Borrar" en cada cuenta de la lista de Ajustes.
- **Añadido:** Formulario inline de edición (nombre, banco, titular, compartida) con Guardar/Cancelar.
- **Añadido:** Confirmación antes de borrar cuenta.
- Ficheros modificados: `static/index.html`, `static/app.js`

### 02:00 — Fix definitivo 405 Method Not Allowed en todas las rutas API
- **Corregido:** POST/PUT/DELETE fallaban con 405 porque las rutas FastAPI usaban `@ruta.get("/")` generando paths como `/api/cuentas/` (con barra final), pero el JS llamaba a `/api/cuentas` (sin barra). La petición no coincidía y caía en el mount de StaticFiles (solo GET → 405).
- **Solución server-side:** Cambiar `@ruta.get("/")` → `@ruta.get("")` y `@ruta.post("/")` → `@ruta.post("")` en los 6 routers CRUD (miembros, cuentas, categorías, reglas, movimientos, mapeo_tarjetas). Así las rutas coinciden directamente sin necesidad de trailing slash.
- **Revertido** el workaround del cliente (`_url()` ya no añade `/` al final) que rompía rutas como `/api/importar/csv`.
- Ficheros modificados: `app/rutas/miembros.py`, `app/rutas/cuentas.py`, `app/rutas/categorias.py`, `app/rutas/reglas.py`, `app/rutas/movimientos.py`, `app/rutas/mapeo_tarjetas.py`, `static/api.js`

### 01:15 — Fix seed parcial: cada tabla se siembra independientemente
- **Corregido:** La función `sembrar_si_vacio()` solo comprobaba si había categorías. Si categorías se insertaban pero miembros/cuentas fallaban, nunca se reintentaba.
- **Solución:** Ahora cada sección (categorías, reglas, miembros, cuentas) comprueba su propia tabla por separado. Si una ya tiene datos y otra no, solo siembra la vacía.
- Ficheros modificados: `app/datos_iniciales.py`

### 00:08 — Fix bug importación: dropdown cuenta vacío + CSV de prueba
- **Corregido:** El desplegable "Cuenta destino" en la pestaña Importar aparecía vacío porque `<template x-for>` dentro de `<select>` con `id` estático no renderizaba las opciones.
- **Solución:** Cambiar los `<select>` de importar a `x-model` de Alpine.js (`importarCuentaId`, `importarBanco`) y añadir las variables reactivas correspondientes en `app.js`.
- **Actualizada** la función `importarCSV()` para usar `this.importarCuentaId` y `this.importarBanco` en vez de `document.getElementById`.
- **Añadido** fichero `test_santander_febrero.csv` con 54 movimientos reales de febrero 2026 para pruebas de importación.
- Ficheros modificados: `static/index.html`, `static/app.js`
- Ficheros añadidos: `test_santander_febrero.csv`

## 2026-03-09

### 23:40 — Implementar FiDo v1 completa: backend, frontend y Docker
- **Backend completo:** FastAPI + SQLite con WAL mode. 9 routers, 6 tablas, validación Pydantic.
- **Frontend SPA:** Alpine.js + Tailwind CSS (CDN) + Chart.js (CDN). 6 pestañas: Panel, Movimientos, Importar, Categorías, Reglas, Ajustes.
- **Lógica de negocio:** Categorizador automático por reglas con prioridad, deduplicador por huella SHA-256 + fuzzy matching.
- **Parser Santander:** Importación de CSV del Banco Santander (punto y coma, DD/MM/YYYY, decimales con coma).
- **API de sincronización:** Endpoints para la app Android (ping + batch de movimientos).
- **Panel/Dashboard:** Resumen con tarjetas, gráfica donut por categoría, barras de evolución mensual.
- **Datos iniciales:** 13 categorías padre con ~40 subcategorías, 27 reglas de auto-categorización, 2 miembros, 4 cuentas.
- **Docker:** Dockerfile (python:3.12-slim) + docker-compose.yml para Portainer stack.
- 32 ficheros, ~2800 líneas de código. Todo en español (variables, funciones, endpoints, columnas BD, comentarios).

## 2026-03-07

### 20:24 — Simplificar a un solo contenedor Docker
- Decisión de arquitectura: FastAPI sirve tanto la API como el frontend estático en un solo contenedor.
- Eliminada la necesidad de un servidor web separado (Nginx/Caddy).

### 19:52 — Corregir flujo Telegram
- n8n envía la respuesta directamente al usuario, sin pasar de vuelta por Node-RED.
- Simplificación del flujo de mensajería.

### 19:47 — Telegram desacoplado de FiDo
- Integración Telegram diseñada con Node-RED (polling) + n8n (parseo/respuesta) — patrón Kryptonite.
- FiDo solo expone API REST, no gestiona Telegram directamente.

### 19:33 — Diseño inicial del proyecto
- Documento de diseño completo: `finanzas-familia-resumen.md`.
- Definición de arquitectura, stack tecnológico, esquema de BD, endpoints API.
- Decisiones: SQLite, Alpine.js, sin autenticación en v1, categorías 2 niveles.

### 19:24 — Initial commit
- Repositorio creado con README.md, .gitignore, LICENSE.
