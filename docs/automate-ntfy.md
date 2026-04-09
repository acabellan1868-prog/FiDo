# Guía de configuración de Automate (LlamaLab) para captura automática de movimientos

Automate es una app de automatización Android **gratuita** (hasta 30 bloques por flow).
No necesita plugins de pago. Esta guía configura un flow que captura notificaciones
de Google Wallet y las envía a FiDo a través de NTFY.

> **Nota:** Esta guía usa los nombres de bloques de la versión actual de Automate
> verificados en https://llamalab.com/automate/doc/block/index.html. No existe
> bloque "Text match" — la extracción de datos se hace con expresiones `matches()`
> dentro de bloques **Variable set**.

---

## Visión general del flujo

```
Google Wallet lanza notificación:
  Título:  "EL RINCONCITO"
  Cuerpo:  "2,50 € con Visa ••9625"
     └─ Automate intercepta la notificación
        └─ extrae importe, descripción y últimos 4 dígitos
           └─ POST a https://ntfy.sh/{NTFY_TOPIC}
              └─ FiDo recibe el mensaje y guarda el movimiento
```

El móvil **no necesita estar en casa ni en la WiFi local**.

---

## Formato de notificación de Google Wallet

Google Wallet es el intermediario recomendado porque centraliza todas las tarjetas
y siempre incluye los últimos 4 dígitos.

| Campo de la notificación | Contenido | Ejemplo |
|--------------------------|-----------|---------|
| Título (Title) | Nombre del comercio | `EL RINCONCITO` |
| Cuerpo (Message) | Importe + tipo tarjeta + últimos 4 | `2,50 € con Visa ••9625` |

---

## Requisitos

- **Automate** de LlamaLab (gratuita en Google Play)
- Permiso **Notification access** concedido a Automate
- Permiso **Do not disturb** concedido a Automate

---

## Paso 1 — Conceder permisos

1. Abrir Automate → menú lateral (☰) → **Settings**
2. Pulsar **Notification access** → activar Automate en la lista del sistema
3. Pulsar **Do not disturb access** → activar Automate

---

## Paso 2 — Crear el flow

1. Pantalla principal → **+** (abajo a la derecha)
2. Nombre: `FiDo — Gasto bancario`
3. Pulsar **Create** → se abre el editor con un bloque **Flow beginning**

---

## Paso 3 — Bloques del flow

### Bloque 1 — Flow beginning *(ya existe)*

Sin configuración. Es el punto de entrada del flow.

---

### Bloque 2 — Notification posted?

Categoría: **Interface** (o buscar `Notification posted`)

> El símbolo `?` indica que es un bloque de evento — espera hasta que llega
> una notificación que cumpla los criterios.

**Input arguments** (parte superior):
- **Package:** seleccionar `Google Wallet`
- El resto: dejar vacío

**Output variables** (parte inferior — aquí defines los nombres de las variables):
- **Title** → escribir `descripcion`
- **Message** → escribir `notif_mensaje`
- El resto: dejar vacío

Pulsar **SAVE**.

---

### Bloque 3 — Variable set (extraer importe)

Buscar: `Variable set`

- **Variable:** `importe_raw`
- **Value:** `matches(notif_mensaje, ".*(\\d+[.,]\\d{2})\\s*€.*")[1]`

Extrae el número antes del símbolo €. Devuelve `null` si no hay coincidencia.

Pulsar **SAVE**.

---

### Bloque 4 — Variable set (normalizar importe)

Otro bloque **Variable set**:

- **Variable:** `importe_raw`
- **Value:** `replaceAll(importe_raw, ",", ".")`

Convierte `2,50` en `2.50` (formato numérico que espera FiDo).

Pulsar **SAVE**.

---

### Bloque 5 — Variable set (extraer últimos 4 dígitos)

Otro bloque **Variable set**:

- **Variable:** `ultimos4`
- **Value:** `matches(notif_mensaje, ".*(\\d{4})")[1]`

Extrae los 4 dígitos finales del cuerpo de la notificación.

Pulsar **SAVE**.

---

### Bloque 6 — HTTP request (enviar a NTFY)

Buscar: `HTTP request` (categoría **Connectivity**)

Configuración:
- **URL:** `https://ntfy.sh/TU_TOPIC_AQUI`
  *(sustituir por el topic real configurado en el `.env` de FiDo)*
- **Method:** `POST`
- **Request headers** (campo tipo Dictionary):
  ```
  {"Content-Type":"application/json"}
  ```
- **Request content body** (campo de expresión):
  ```
  '{"importe":-' + importe_raw + ',"descripcion":"' + descripcion + '","ultimos4":"' + ultimos4 + '"}'
  ```

> **IMPORTANTE — problema con copiar/pegar desde WhatsApp u otras apps:**
> WhatsApp y muchas apps convierten las comillas rectas `'` en comillas tipográficas
> `'` `'` que Automate no reconoce y da error. Escribir siempre desde el teclado
> del móvil directamente en Automate.
>
> Las comillas del body son **todas simples rectas** `'` (la tecla normal del teclado).
> Las comillas dentro del JSON (alrededor de los valores) son **dobles** `"`.

Pulsar **SAVE**.

---

### Bloque 7 — Volver al inicio (bucle)

No añadir un bloque nuevo. **Conectar la salida del bloque HTTP request de vuelta
al bloque 2 (Notification posted?)** pulsando y arrastrando la flecha de salida
hasta ese bloque. Así el flow permanece activo indefinidamente.

---

## Diagrama final

```
[Flow beginning]
      │
      ▼
[Notification posted?] ◄─────────────────────────────┐
  Package: Google Wallet                              │
  Title → descripcion                                 │
  Message → notif_mensaje                             │
      │                                               │
      ▼                                               │
[Variable set]                                        │
  importe_raw = matches(notif_mensaje, ...)[1]        │
      │                                               │
      ▼                                               │
[Variable set]                                        │
  importe_raw = replaceAll(importe_raw, ",", ".")     │
      │                                               │
      ▼                                               │
[Variable set]                                        │
  ultimos4 = matches(notif_mensaje, ...)[1]           │
      │                                               │
      ▼                                               │
[HTTP request → NTFY]                                 │
  POST JSON con importe, descripcion, ultimos4        │
      │                                               │
      └─────────────────────────────────────────────►─┘
```

Total: **7 bloques** (límite gratuito: 30).

---

## Paso 4 — Activar el flow

1. Guardar el flow (tick o botón Save del editor)
2. En la pantalla principal, pulsar **Play (▶)** en el flow
3. El flow aparece como **Running** — ya está escuchando

Para que sobreviva a reinicios del móvil:
- **Settings** → **Run on system startup** → activar el flow

---

## Paso 5 — Probar sin notificación real

Desde una terminal (PC o Termux en el móvil):

```bash
curl -d '{"importe":-8.94,"descripcion":"Cash Lepe","ultimos4":"9625"}' \
     https://ntfy.sh/TU_TOPIC_AQUI
```

El movimiento debería aparecer en FiDo en unos segundos.

Para verificar que FiDo lo recibe:

```bash
docker logs fido -f | grep ntfy
```

Líneas esperadas:
```
INFO  fido.ntfy  Conexión NTFY establecida. Escuchando movimientos...
INFO  fido.ntfy  Movimiento NTFY importado: Cash Lepe -8.94€ (2026-04-07)
```

---

## Depuración

### El flow no dispara con notificaciones de Google Wallet

1. Verificar permisos: Notification access y Do not disturb activos para Automate
2. En Xiaomi/MIUI: desactivar optimización de batería para Automate
3. En Samsung One UI: añadir Automate a "Apps no optimizadas"
4. Probar dejando el campo **Package** vacío temporalmente para confirmar
   que el bloque captura notificaciones de cualquier app

### Error en el campo body del HTTP request

- Verificar que todas las comillas son **rectas** `'` `"`, no tipográficas `'` `"`
- Escribir directamente en Automate, no copiar desde WhatsApp ni navegador
- El campo acepta una **expresión**, no texto plano

### importe_raw es null

La notificación no tiene el formato esperado. Usar un bloque temporal
**Dialog — Message** después del Notification posted? para mostrar el valor
de `notif_mensaje` y ver el texto exacto que llega. Luego ajustar el regex.

### Movimiento sin categoría o con estado "Por revisar"

Normal la primera vez. FiDo no tiene una regla para ese comercio.
Ir a FiDo → Reglas y añadir una regla para la descripción. En el siguiente
pago se categorizará automáticamente.

---

## Estado de la configuración (2026-04-07)

| # | Bloque | Estado |
|---|--------|--------|
| 1 | Flow beginning | ✅ |
| 2 | Notification posted? (Google Wallet) | ✅ |
| 3 | Variable set — importe_raw (matches) | ✅ |
| 4 | Variable set — importe_raw (replaceAll) | ✅ |
| 5 | Variable set — ultimos4 | ✅ |
| 6 | HTTP request → NTFY | ⚠ Pendiente (body sin terminar) |
| 7 | Bucle de retorno al bloque 2 | ⏳ Pendiente |

**Pendiente:** Escribir el campo **Request content body** del bloque 6 directamente
desde el teclado del móvil (no copiar/pegar):

```
'{"importe":-' + importe_raw + ',"descripcion":"' + descripcion + '","ultimos4":"' + ultimos4 + '"}'
```
