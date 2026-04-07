# Guía de configuración de Automate (LlamaLab) para captura automática de movimientos

Automate es una app de automatización Android **gratuita** (hasta 30 bloques por flow).
No necesita plugins de pago. Esta guía configura un flow que captura notificaciones
bancarias y las envía a FiDo a través de NTFY.

---

## Visión general del flujo

```
App bancaria (CaixaBank / Revolut / etc.)
  └─ lanza notificación: "Pago 8,94€ en Cash Lepe *9625"
     └─ Automate intercepta la notificación
        └─ extrae importe, comercio y últimos 4 dígitos con regex
           └─ POST a https://ntfy.sh/{NTFY_TOPIC}  ←  funciona con datos móviles
              └─ FiDo recibe el mensaje (siempre conectado desde la VM)
                 └─ categoriza automáticamente y guarda el movimiento
```

El móvil **no necesita estar en casa ni en la WiFi local**. NTFY funciona con
datos móviles. FiDo siempre está conectado en la VM.

---

## Qué es un bloque en Automate

Cada pieza del diagrama (rectángulo, rombo de decisión, evento) es un bloque.
Los bloques se conectan con flechas. El flow gratuito permite hasta 30 bloques;
este flow usa aproximadamente 12.

---

## Requisitos

- **Automate** de LlamaLab (gratuita en Google Play)
- Permiso de "acceso a notificaciones" concedido a Automate en Ajustes del móvil

---

## Paso 1 — Conceder acceso a notificaciones

1. Abrir Automate → menú lateral → **Settings**
2. Pulsar **Notification access** → se abre el ajuste del sistema
3. Activar Automate en la lista

---

## Paso 2 — Crear el flow

### 2.1 Nuevo flow

1. En la pantalla principal de Automate pulsar **+** (nuevo flow)
2. Nombre: `FiDo — Gasto bancario`
3. Se abre el editor de diagrama vacío con un bloque **Flow beginning**

---

### 2.2 Bloques del flow (en orden)

Añadir los bloques uno a uno pulsando el **+** de la conexión de salida de cada
bloque anterior. El número entre paréntesis es el orden en el diagrama.

---

#### Bloque 1 — Flow beginning *(ya existe al crear el flow)*

Sin configuración. Conectar su salida al bloque 2.

---

#### Bloque 2 — Notification event

Buscar: **Notification event**

Configuración:
- **Application:** seleccionar tu app bancaria (ej: CaixaBank, Revolut…)
  *(si tienes varias, crear una copia del flow para cada una o seleccionar varias)*
- **Type:** Posted *(notificación nueva)*
- **Content filter (regex):** `(?i)(pago|compra|cargo|has paid|you paid)`
  *(solo dispara en notificaciones de gasto, ignora el resto)*

Salida: conectar al bloque 3.

> Este bloque espera indefinidamente hasta que llega una notificación que cumpla
> el filtro. Cuando llega, guarda automáticamente el texto en la variable
> `Notification.TEXT` (texto) y `Notification.TITLE` (título).

---

#### Bloque 3 — Text match (extraer importe)

Buscar: **Text match**

Configuración:
- **Text:** `Notification.TEXT`
- **Regular expression:** `(\d+[.,]\d{2})`
- **Match group:** `1`
- **Output variable:** `importe_raw`

Salidas:
- **Matched** → bloque 4
- **Not matched** → conectar de vuelta al bloque 2 *(notificación sin importe, ignorar)*

---

#### Bloque 4 — Text replace (coma → punto)

Buscar: **Text replace**

Configuración:
- **Text:** `importe_raw`
- **Regular expression:** activado
- **Search:** `,`
- **Replace:** `.`
- **Output variable:** `importe_raw`

Salida: conectar al bloque 5.

---

#### Bloque 5 — Text match (extraer descripción)

Buscar: **Text match**

Configuración:
- **Text:** `Notification.TEXT`
- **Regular expression:** *(elegir según tu banco, ver tabla al final)*
  - CaixaBank: `en (.+?)(?:\s+\*\d{4})?$`
  - Revolut: `at (.+?)$`
  - Santander: `Compra .+?€ (.+)`
- **Match group:** `1`
- **Output variable:** `descripcion`

Salidas:
- **Matched** → bloque 6
- **Not matched** → usar valor por defecto: añadir bloque **Variable set** con
  `descripcion = Sin descripcion` → conectar al bloque 6

---

#### Bloque 6 — Text match (extraer últimos 4 dígitos)

Buscar: **Text match**

Configuración:
- **Text:** `Notification.TEXT`
- **Regular expression:** `\*(\d{4})`
- **Match group:** `1`
- **Output variable:** `ultimos4`

Salidas:
- **Matched** → bloque 7
- **Not matched** → bloque 7 *(sin ultimos4; FiDo usará NTFY_CUENTA_DEFAULT)*

---

#### Bloque 7 — HTTP request (enviar a NTFY)

Buscar: **HTTP request**

Configuración:
- **URL:** `https://ntfy.sh/{NTFY_TOPIC}`
  *(sustituir `{NTFY_TOPIC}` por tu topic real, ej: `fido-mov-a3k9x2m7p1`)*
- **Method:** POST
- **Headers:**
  - Nombre: `Content-Type`
  - Valor: `application/json`
- **Request body:**
  ```
  {"importe":-{importe_raw},"descripcion":"{descripcion}","ultimos4":"{ultimos4}"}
  ```
  *(Automate sustituye `{nombre_variable}` por el valor de la variable)*

> El `-` delante de `{importe_raw}` convierte el importe en negativo (gasto).
> Para ingresos, crear un flow separado sin el signo menos y con filtro de
> contenido distinto (ej: `(?i)(ingreso|transferencia recibida|abono)`).

Salida: conectar al bloque 8.

---

#### Bloque 8 — Flow beginning (bucle)

No añadir un nuevo bloque. **Conectar la salida del bloque 7 de vuelta al
bloque 2** (Notification event). Así el flow permanece activo y escucha la
siguiente notificación sin necesidad de relanzarlo.

---

### 2.3 Diagrama final

```
[Flow beginning]
      │
      ▼
[Notification event] ◄────────────────────────────┐
      │ (notificación detectada)                   │
      ▼                                            │
[Text match — importe]                             │
      │ Matched          Not matched               │
      ▼                       └──────────────────►─┘
[Text replace — coma→punto]
      │
      ▼
[Text match — descripción]
      │ Matched     Not matched
      ▼                   ▼
[Text match — ultimos4]  [Variable set descripcion="Sin descripcion"]
      │ Matched / Not matched                      │
      └─────────────────────────────────────────►──┘
                                                   ▼
                                        [HTTP request → NTFY]
                                                   │
                                                   └──► (vuelve a Notification event)
```

---

### 2.4 Guardar y activar el flow

1. Pulsar el tick o **Save** para guardar
2. En la pantalla principal, pulsar el botón **Play** (▶) del flow
3. El flow aparecerá en estado **Running** — ya está escuchando

> **Importante:** Para que el flow sobreviva a reinicios del móvil, ir a
> **Settings** → **Run on system startup** y activarlo para este flow.

---

## Paso 3 — Probar

### Prueba sin notificación real

Enviar un JSON directamente desde una terminal:

```bash
curl -d '{"importe":-8.94,"descripcion":"Cash Lepe","ultimos4":"9625"}' \
     https://ntfy.sh/{NTFY_TOPIC}
```

El movimiento debería aparecer en FiDo en unos segundos.

### Prueba manual desde Automate

Con el flow parado (no en Running), pulsar **Run** — Automate ejecutará el flow
pero el bloque "Notification event" necesita que llegue una notificación real
para continuar. Lo más práctico es la prueba con `curl` de arriba.

### Prueba con notificación real

1. Hacer un pago pequeño con la tarjeta
2. Comprobar que el flow tiene actividad (icono de running en Automate)
3. Verificar el movimiento en FiDo

---

## Depuración

### Ver los logs de FiDo en tiempo real

```bash
docker logs fido -f | grep ntfy
```

Líneas esperadas:
```
INFO  fido.ntfy  Conexión NTFY establecida. Escuchando movimientos...
INFO  fido.ntfy  Movimiento NTFY importado: Cash Lepe -8.94€ (2026-04-07)
```

### El flow no dispara con la notificación bancaria

1. Verificar que Automate tiene permiso de "acceso a notificaciones"
2. Probar desactivando el **filtro de contenido** temporalmente para confirmar
   que la notificación se captura
3. En Xiaomi/MIUI: desactivar la optimización de batería para Automate
   (Ajustes → Batería → buscar Automate → Sin restricciones)
4. En Samsung One UI: añadir Automate a "Apps no optimizadas"

### Ver qué texto captura Automate

Añadir un bloque **Notification log** o conectar temporalmente un bloque
**Dialog — Alert** después del bloque 2 para mostrar `Notification.TEXT`
en pantalla y confirmar el texto exacto que llega.

### El importe sale mal o la descripción está vacía

Copiar el texto exacto de la notificación bancaria y probar el regex en
[regex101.com](https://regex101.com) antes de configurarlo en Automate.

### Movimiento sin categoría o con estado "Por revisar"

Es normal la primera vez. FiDo no tiene una regla que coincida con esa
descripción. Ir a FiDo → Reglas y añadir una regla para ese comercio.
En el siguiente movimiento se categorizará automáticamente.

---

## Formatos de notificación por banco (referencia)

| Banco | Ejemplo de notificación | Regex importe | Regex descripción |
|-------|------------------------|---------------|-------------------|
| CaixaBank | `Pago 8,94€ en Cash Lepe *9625` | `(\d+[.,]\d{2})` | `en (.+?)(?:\s+\*\d{4})?$` |
| Santander | `Compra 12,30€ Carrefour` | `(\d+[.,]\d{2})` | `Compra \d+[.,]\d+€ (.+)` |
| Revolut | `You paid €8.50 at Cafe` | `(\d+[.,]\d{2})` | `at (.+?)$` |

El formato exacto puede variar según la versión de la app. Lo más fiable es:
1. Recibir una notificación real del banco
2. Usar el truco del bloque **Dialog — Alert** para ver el texto capturado
3. Ajustar el regex sobre ese texto real en regex101.com

---

## Consideraciones de seguridad

- El topic de NTFY es el único mecanismo de autenticación. Usar un nombre
  largo y aleatorio (16+ caracteres).
- No compartir el nombre del topic.
- Los mensajes en `ntfy.sh` (servidor público) se almacenan 12 horas. Para
  mayor privacidad, se puede desplegar NTFY en la propia VM y configurar
  `NTFY_URL` apuntando a él.
