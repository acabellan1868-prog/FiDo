# Guía de configuración de Tasker para captura automática de movimientos

Esta guía explica cómo configurar Tasker (app Android de automatización) para
que capture notificaciones bancarias y las envíe automáticamente a FiDo
a través de NTFY como intermediario.

---

## Visión general del flujo

```
App bancaria (CaixaBank / Santander / etc.)
  └─ lanza notificación: "Pago 45,50€ en Mercadona *1234"
     └─ Tasker intercepta la notificación
        └─ extrae importe, comercio y últimos 4 dígitos con regex
           └─ POST a https://ntfy.sh/{NTFY_TOPIC}  ←  funciona con datos móviles
              └─ FiDo recibe el mensaje (siempre conectado desde la VM)
                 └─ categoriza automáticamente y guarda el movimiento
```

El móvil **no necesita estar en casa ni en la WiFi local**. NTFY funciona con
datos móviles. FiDo está siempre conectado en la VM y escucha el topic de forma
continua.

---

## Requisitos

- **Tasker** (app de pago, ~4€ en Google Play)
- **AutoNotification** (plugin de Tasker, ~3€) — para capturar notificaciones
  con mayor control y precisión
- Permiso de "acceso a notificaciones" concedido a Tasker en Ajustes del móvil

---

## Paso 1 — Crear el topic privado en NTFY

El nombre del topic actúa como contraseña (quien lo conoce puede publicar y
leer). Usar un nombre largo y aleatorio.

Ejemplo: `{NTFY_TOPIC}`

Anótalo. Lo usarás en:
- La variable `NTFY_TOPIC` del `docker-compose.yml` de FiDo
- La URL del POST de Tasker

---

## Paso 2 — Configurar variables de entorno en FiDo

En el `docker-compose.yml` (o en el stack de Portainer), añadir al servicio `fido`:

```yaml
environment:
  - NTFY_URL=https://ntfy.sh
  - NTFY_TOPIC={NTFY_TOPIC}
  - NTFY_CUENTA_DEFAULT=1    # ID de la cuenta principal (opcional)
```

Reiniciar el contenedor para que tome los nuevos valores.

---

## Paso 3 — Crear el perfil en Tasker

### 3.1 Perfil: notificación de CaixaBank

**Nombre del perfil:** `FiDo — CaixaBank`

**Condición de disparo:**
- Tipo: `Plugin` → `AutoNotification` → `Intercept`
- App: `CaixaBank` (o el nombre exacto de la app en tu móvil)
- Filtro de texto (regex): `(?i)(pago|compra|cargo).+?\d`
  *(captura notificaciones que mencionan pagos con importes)*

**Tarea vinculada:** `FiDo — Enviar movimiento` (ver sección 3.3)

### 3.2 Perfil: notificación de Santander

Igual que el anterior pero con la app `Santander` y ajustando el regex si el
formato de notificación es diferente.

### 3.3 Tarea: `FiDo — Enviar movimiento`

Esta tarea se ejecuta cuando un perfil dispara. Recibe el texto de la notificación,
extrae los datos y los envía a NTFY.

#### Acción 1 — Extraer importe (Variable Set)

- **Variable:** `%importe_raw`
- **To (valor):** `%an_text` *(texto completo de la notificación, proporcionado por AutoNotification)*
- **Regex Match:** activado
- **Match:** `(\d+[.,]\d{2})` *(patrón para capturar números con decimales, ej: 45,50)*
- **Store Matches In:** `%importe_match`

#### Acción 2 — Normalizar importe (Variable Set)

- **Variable:** `%importe`
- **To:** `-%importe_match1` *(negativo porque es un gasto; cambiar a positivo para ingresos)*
- Reemplazar `,` por `.` usando `Variable Search Replace` si tu banco usa coma decimal

#### Acción 3 — Extraer descripción (Variable Set)

- **Variable:** `%descripcion`
- **To:** `%an_text`
- **Regex Match:** activado
- **Match:** Depende del formato de tu banco. Ejemplos:
  - CaixaBank: `(?:en|a)\s+(.+?)(?:\s+\*\d{4})?$`
  - Santander: `Compra en (.+?) por`
- **Store Matches In:** `%desc_match`
- Usar `%desc_match1` como descripción

#### Acción 4 — Extraer últimos 4 dígitos (Variable Set)

- **Variable:** `%ultimos4`
- **To:** `%an_text`
- **Regex Match:** activado
- **Match:** `\*(\d{4})`
- **Store Matches In:** `%tarjeta_match`

#### Acción 5 — Construir JSON (Variable Set)

- **Variable:** `%json_body`
- **To:**
```
{"importe":%importe,"descripcion":"%desc_match1","ultimos4":"%tarjeta_match1"}
```

*(Tasker reemplaza las variables automáticamente al ejecutar)*

#### Acción 6 — Enviar a NTFY (HTTP Request)

- **Método:** POST
- **URL:** `https://ntfy.sh/{NTFY_TOPIC}`
  *(sustituir por tu topic real)*
- **Headers:**
  - `Content-Type` : `application/json`
- **Body:** `%json_body`
- **Timeout:** 30 segundos

---

## Paso 4 — Probar manualmente

Antes de que llegue una notificación real, puedes probar enviando un mensaje
directamente desde el navegador o desde una terminal:

```bash
curl -d '{"importe":-12.50,"descripcion":"Prueba Tasker","ultimos4":"1234"}' \
     https://ntfy.sh/{NTFY_TOPIC}
```

Si todo está bien, el movimiento aparecerá en FiDo en unos segundos.

También puedes publicar desde la app de NTFY en el móvil para verificar que
FiDo lo recibe sin necesidad de configurar Tasker primero.

---

## Depuración (búsqueda de problemas)

### Ver los logs de FiDo en tiempo real

```bash
docker logs fido -f | grep ntfy
```

Deberías ver líneas como:
```
INFO  fido.ntfy  Conexión NTFY establecida. Escuchando movimientos...
INFO  fido.ntfy  Movimiento NTFY importado: Mercadona -45.50€ (2026-04-06)
```

### El movimiento no aparece en FiDo

1. Comprobar que `NTFY_TOPIC` está bien configurado en el contenedor.
2. Verificar que el JSON es válido (probar con `curl` como en el paso 4).
3. Revisar que `cuenta_id`, `ultimos4` o `NTFY_CUENTA_DEFAULT` están configurados.
4. Consultar los logs: `docker logs fido --tail=50`

### Tasker no captura la notificación

1. Verificar que Tasker tiene el permiso de "acceso a notificaciones".
2. En algunos móviles (Xiaomi, Samsung con One UI), hay que desactivar la
   optimización de batería para Tasker y AutoNotification.
3. Activar el modo "Monitorización de notificaciones" en AutoNotification.

---

## Consideraciones de seguridad

- El topic de NTFY es el único mecanismo de autenticación. Usar un nombre
  suficientemente largo y aleatorio (16+ caracteres).
- No compartir el nombre del topic.
- Los mensajes NTFY en `ntfy.sh` (servidor público) se almacenan durante
  12 horas. Para mayor privacidad, se puede desplegar NTFY en la propia
  infraestructura (en la VM, por ejemplo) y usar `NTFY_URL` apuntando a él.

---

## Formatos de notificación por banco (referencia)

| Banco | Ejemplo de notificación | Regex importe | Regex descripción |
|-------|------------------------|---------------|-------------------|
| CaixaBank | `Pago 45,50€ en Mercadona *1234` | `(\d+[.,]\d{2})€` | `en (.+?) \*\d` |
| Santander | `Compra 12,30€ Carrefour` | `(\d+[.,]\d{2})€` | `Compra \d+[.,]\d+€ (.+)` |
| Revolut | `You paid €8.50 at Cafe` | `€(\d+\.\d{2})` | `at (.+)$` |

Estos son ejemplos orientativos. El formato exacto puede variar según la versión
de la app. Lo mejor es recibir una notificación real, copiar el texto completo
y ajustar el regex sobre ese ejemplo concreto.
