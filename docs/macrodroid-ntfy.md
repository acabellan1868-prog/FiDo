# Guía de configuración de MacroDroid para captura automática de movimientos

MacroDroid es una app de automatización Android **gratuita** (hasta 5 macros).
No necesita plugins de pago. Esta guía configura una macro que captura
notificaciones bancarias y las envía a FiDo a través de NTFY.

---

## Visión general del flujo

```
App bancaria (CaixaBank / Revolut / etc.)
  └─ lanza notificación: "Pago 8,94€ en Cash Lepe *9625"
     └─ MacroDroid intercepta la notificación
        └─ extrae importe, comercio y últimos 4 dígitos con regex
           └─ POST a https://ntfy.sh/{NTFY_TOPIC}  ←  funciona con datos móviles
              └─ FiDo recibe el mensaje (siempre conectado desde la VM)
                 └─ categoriza automáticamente y guarda el movimiento
```

El móvil **no necesita estar en casa ni en la WiFi local**. NTFY funciona con
datos móviles. FiDo siempre está conectado en la VM.

---

## Requisitos

- **MacroDroid** (gratuita en Google Play, límite 5 macros)
- Permiso de "acceso a notificaciones" concedido a MacroDroid en Ajustes del móvil

No se necesita ningún plugin adicional.

---

## Paso 1 — Conceder acceso a notificaciones

1. Abrir MacroDroid → menú lateral → **Preferencias de MacroDroid**
2. Pulsar **Solicitar acceso a notificaciones**
3. En los ajustes del sistema, activar MacroDroid en la lista de apps con acceso

---

## Paso 2 — Crear la macro

### 2.1 Nombre y trigger (disparador)

1. En MacroDroid, pulsar **+** para nueva macro
2. Nombre: `FiDo — Gasto bancario`
3. En **Triggers** (disparadores), pulsar **+**:
   - Categoría: **Dispositivo**
   - Seleccionar: **Notificación recibida**
   - **Aplicación:** seleccionar tu app bancaria (ej: CaixaBank, Revolut…)
   - **Filtro de contenido:** activar y escribir:
     ```
     (?i)(pago|compra|cargo|has paid|you paid)
     ```
     *(regex que solo dispara en notificaciones de gasto, ignora el resto)*
   - Marcar **Usar expresión regular (regex)**

> Si tienes varias apps bancarias, puedes seleccionar varias apps en el mismo
> trigger o duplicar la macro para cada banco.

### 2.2 Acciones — extraer datos de la notificación

En **Acciones**, añadir las siguientes en orden:

---

#### Acción 1 — Guardar el texto de la notificación

- Categoría: **Variables**
- Acción: **Establecer variable**
- Tipo: **Variable local de cadena (String)**
- Nombre: `notif_texto`
- Valor: `[trigger_content]`
  *(MacroDroid rellena esto automáticamente con el texto de la notificación)*

---

#### Acción 2 — Extraer importe

- Categoría: **Variables**
- Acción: **Manipular variable**
- Variable: `notif_texto`
- Operación: **Extracción por Expresión Regular (RegEx)**
- Regex: `(\d+[.,]\d{2})`
- Grupo: `1`
- Guardar resultado en nueva variable: `importe_raw`

---

#### Acción 3 — Reemplazar coma por punto en el importe

Si tu banco muestra `8,94` en vez de `8.94`:

- Categoría: **Variables**
- Acción: **Manipular variable**
- Variable: `importe_raw`
- Operación: **Reemplazar**
- Buscar: `,`
- Reemplazar por: `.`

---

#### Acción 4 — Extraer descripción del comercio

- Categoría: **Variables**
- Acción: **Manipular variable**
- Variable: `notif_texto`
- Operación: **Extracción por Expresión Regular (RegEx)**
- Regex (ajustar según tu banco, ver tabla al final):
  - CaixaBank: `(?:en|a)\s+(.+?)(?:\s+\*\d{4})?$`
  - Revolut: `at (.+?)$`
  - Santander: `Compra .+?€ (.+)`
- Grupo: `1`
- Guardar en nueva variable: `descripcion`

---

#### Acción 5 — Extraer últimos 4 dígitos de la tarjeta

- Categoría: **Variables**
- Acción: **Manipular variable**
- Variable: `notif_texto`
- Operación: **Extracción por Expresión Regular (RegEx)**
- Regex: `\*(\d{4})`
- Grupo: `1`
- Guardar en nueva variable: `ultimos4`

*(Si la notificación no incluye los últimos 4 dígitos, omitir esta acción.
FiDo usará `NTFY_CUENTA_DEFAULT` o habrá que incluir `cuenta_id` en el JSON.)*

---

#### Acción 6 — Enviar a NTFY

- Categoría: **Conectividad**
- Acción: **Solicitud HTTP (HTTP Request)**
- **URL:** `https://ntfy.sh/{NTFY_TOPIC}`
  *(sustituir por tu topic real)*
- **Método:** POST
- **Cabeceras (Headers):** añadir:
  - Nombre: `Content-Type`
  - Valor: `application/json`
- **Cuerpo (Body):**
  ```
  {"importe":-[importe_raw],"descripcion":"[descripcion]","ultimos4":"[ultimos4]"}
  ```

> MacroDroid sustituye `[importe_raw]`, `[descripcion]` y `[ultimos4]`
> automáticamente con los valores extraídos antes de enviar la petición.
>
> El `-` delante de `[importe_raw]` convierte el importe en negativo (gasto).
> Para ingresos, crear una macro separada sin el signo menos.

---

### 2.3 Guardar la macro

Pulsar el tick (✓) para guardar. Asegurarse de que la macro está **activada**
(interruptor en verde).

---

## Paso 3 — Probar

### Prueba sin notificación real

Enviar un JSON directamente desde una terminal o desde la app NTFY:

```bash
curl -d '{"importe":-8.94,"descripcion":"Cash Lepe","ultimos4":"9625"}' \
     https://ntfy.sh/{NTFY_TOPIC}
```

El movimiento debería aparecer en FiDo en unos segundos.

### Prueba con notificación real

1. Hacer un pago pequeño con la tarjeta
2. Comprobar que MacroDroid dispara (icono de actividad en la notificación)
3. Verificar el movimiento en FiDo

### Prueba manual desde MacroDroid

Abrir la macro → botón de **Ejecutar** (play) — MacroDroid pedirá introducir
el texto de prueba para `[trigger_content]` si el trigger no está activo.

---

## Depuración (búsqueda de problemas)

### Ver los logs de FiDo en tiempo real

```bash
docker logs fido -f | grep ntfy
```

Líneas esperadas:
```
INFO  fido.ntfy  Conexión NTFY establecida. Escuchando movimientos...
INFO  fido.ntfy  Movimiento NTFY importado: Cash Lepe -8.94€ (2026-04-07)
```

### MacroDroid no dispara

1. Verificar que tiene el permiso de "acceso a notificaciones"
2. En Xiaomi/MIUI: desactivar optimización de batería para MacroDroid
3. En Samsung One UI: añadir MacroDroid a "Apps no optimizadas"
4. Comprobar el filtro de contenido — probar sin el filtro primero para
   confirmar que la notificación se captura

### El importe sale mal

Usar el **registro de MacroDroid** (menú lateral → Registro de macros) para
ver qué valor tienen las variables tras cada acción.

### Movimiento sin categoría o con estado "Por revisar"

Es normal la primera vez. Significa que FiDo no tiene una regla que haga match
(coincidencia) con esa descripción. Entrar en FiDo → Reglas y añadir una regla
para ese comercio. En el siguiente movimiento se categorizará automáticamente.

---

## Formatos de notificación por banco (referencia)

| Banco | Ejemplo de notificación | Regex importe | Regex descripción |
|-------|------------------------|---------------|-------------------|
| CaixaBank | `Pago 8,94€ en Cash Lepe *9625` | `(\d+[.,]\d{2})` | `en (.+?)(?:\s+\*\d{4})?$` |
| Santander | `Compra 12,30€ Carrefour` | `(\d+[.,]\d{2})` | `Compra \d+[.,]\d+€ (.+)` |
| Revolut | `You paid €8.50 at Cafe` | `(\d+[.,]\d{2})` | `at (.+?)$` |

El formato exacto puede variar según la versión de la app. Lo más fiable es:
1. Recibir una notificación real
2. En MacroDroid → Registro → copiar el texto capturado
3. Ajustar el regex sobre ese texto real

---

## Consideraciones de seguridad

- El topic de NTFY es el único mecanismo de autenticación. Usar un nombre
  largo y aleatorio (16+ caracteres).
- No compartir el nombre del topic.
- Los mensajes en `ntfy.sh` (servidor público) se almacenan 12 horas. Para
  mayor privacidad, se puede desplegar NTFY en la propia VM y configurar
  `NTFY_URL` apuntando a él.
