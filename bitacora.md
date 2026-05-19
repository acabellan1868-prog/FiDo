# Changelog — FiDo (Finanzas Domésticas)

Registro de todos los cambios del proyecto, ordenado de más reciente a más antiguo.

---

## 2026-05-19 — Sistema de captura semiautomática en producción ✅

Implementación completa del flujo Drive → Cowork Scheduler → Windows Task Scheduler → FiDo.
Documentado en `capturaGastosIA.md`.

Componentes en producción:
- Cowork scheduler "FiDo — Procesar gastos Drive": lee imágenes de Drive, extrae datos con visión IA, escribe scripts .ps1 en `C:\fido-queue\`
- Windows Task Scheduler "FiDo-Cola": ejecuta los .ps1 cada 15 min y registra en `fido-cola.log`
- Mapeo tarjeta→cuenta: 9625→Revolut, 5911→Caixa, 5155→Común; fallback por banco cuando no hay número
- Gestión de imágenes con fondo oscuro: fallback a download_file_content + base64

---

## 2026-05-15 — Prueba end-to-end Fase 4 superada ✅

### Resultado

La tarea programada `fido-gastos-drive` procesó correctamente la captura real:

- **Imagen:** `Screenshot_2026-04-15-14-25-58-698_com.miui.home.jpg`
- **Datos extraídos:** BAR CASA MIGUEL, -7.10€, tarjeta Revolut 9625
- **Cuenta resuelta:** cuenta_id 8 (Revolut) por mapeo de tarjeta
- **Movimiento creado:** ID 852 en FiDo con `estado: revisar`
- **Imagen copiada** a carpeta procesadas (ID `1qhHxIFMCogIJGjLAjy8KwKBwRaP_FgFf`)

La tarea se creó a través de Cowork Scheduled Tasks y **persiste entre sesiones** — no es necesario recrearla manualmente al iniciar sesión.

El flujo completo está operativo. Fase 4 cerrada.

---

## 2026-05-15 — Implementación Fase 4: captura de gastos vía Google Drive + Claude Vision

### Solución final acordada

Se descarta todo el pipeline Node-RED → n8n → OCR. Solución mucho más simple:

1. Usuario captura pantalla de la notificación (Wallet, Revolut, banco)
2. La sube a Google Drive: `Proyectos/Desarrollo/hogarOS/FiDo/gastosPendientes/`
3. Claude (agente con cron) revisa la carpeta cada 30 minutos
4. Lee la imagen directamente (Claude es multimodal, no necesita OCR)
5. Extrae importe, descripción y últimos 4 dígitos
6. Llama a `POST /finanzas/api/movimientos` en FiDo
7. Copia la imagen a `gastosPendientes/procesadas/` para no reprocesar

### Carpetas Drive

- **Pendientes:** ID `1Hzd7V4N5Gwy9_0Zy3GQsudQdOiKI_Pvn`
- **Procesadas:** ID `1qhHxIFMCogIJGjLAjy8KwKBwRaP_FgFf`
- **Cuenta:** acabellan.1868@gmail.com

### Cron (Claude Code)

El agente se programa con `CronCreate` al iniciar sesión. Se ejecuta a las :17 y :47 de cada hora.
**⚠️ El cron es session-only — hay que recrearlo cada sesión de Claude Code.**

Para recrearlo al inicio de sesión, ejecutar en Claude Code:
> "Reactiva el cron de FiDo para procesar gastos de Drive cada 30 minutos"

### Estado

- Cron activo (job `6c4047b9`) — se pierde al cerrar Claude Code
- Pendiente: prueba end-to-end con captura real

---

## 2026-05-15 — Cambio Fase 4: OCR Tesseract en lugar de Claude Vision API

### Decisión

Tras intentar crear API key en console.anthropic.com, se descubrió que Anthropic
ya no permite crear nuevas keys con plan "gratuito" — ahora requiere créditos pagos
($5 USD mínimo).

Se opta por **Tesseract OCR gratuito** en su lugar:
- Es código abierto, sin costes
- Para imágenes claras de notificaciones bancarias, el OCR debería ser suficiente
- n8n tiene nodo integrado para Tesseract (sin instalación adicional en contenedor)

### Flujo revisado

1. Usuario → captura pantalla de Wallet/Revolut → Telegram
2. Node-RED → detecta foto → pasa file_id a webhook n8n
3. **n8n → descarga imagen → Tesseract OCR** (nodo integrado)
4. n8n → parsea texto con regex/Code → extrae `{importe, descripcion, ultimos4, fecha}`
5. n8n → POST `/movimientos` a FiDo API
6. n8n → Telegram responde confirmando el alta

### Próximos pasos

1. Montar flow n8n: Webhook → HTTP (descarga imagen Telegram) → Tesseract → Code (parsear) → HTTP (FiDo API) → Telegram
2. Probar con captura real de notificación para ajustar regex si es necesario
3. Añadir nodo switch en Node-RED para separar fotos (FiDo) de texto (Kryptonite)

---

## 2026-05-15 — Rediseño Fase 4: descarte de Automate + NTFY, nuevo enfoque Telegram + Claude Vision

### Decisión

El flow de Automate (LlamaLab) para capturar notificaciones de Google Wallet fue
descartado definitivamente. Android bloquea el acceso al contenido de notificaciones
de apps financieras, por lo que las variables `descripcion` y `notif_mensaje` del
flow llegaban vacías. No es un problema de configuración — es una restricción del SO.

El mismo problema aplica a MacroDroid y Tasker sin el plugin AutoNotification de pago.
El enfoque basado en SMS también fue descartado: los bancos no mandan SMS por gastos
pequeños (ej. 2,50€ en una cafetería).

### Nuevo enfoque acordado

1. El usuario hace una captura de pantalla de la notificación de pago (banco o Google Wallet)
2. La envía al bot de Telegram existente
3. Node-RED (que ya hace polling de Telegram) detecta que el mensaje es una foto
4. Node-RED pasa el `file_id` a un webhook nuevo de n8n
5. n8n descarga la imagen desde Telegram → envía a Claude Vision API (Anthropic) con
   un prompt que extrae JSON: `{importe, descripcion, ultimos4, fecha}`
6. n8n llama a `POST /movimientos` en FiDo con los datos extraídos
7. n8n responde al usuario en Telegram confirmando el alta

### Estado al cerrar sesión

- Cuenta en console.anthropic.com verificada (plan gratuito, suficiente para el uso previsto)
- API key **aún no creada** — será lo primero en la próxima sesión
- Bot de Telegram y routing Node-RED → n8n ya existen (se usan para Kryptonite)
- No se ha tocado código

### Próximos pasos concretos

1. Crear API key en `console.anthropic.com` → guardarla como secret en n8n
2. Montar flow n8n: Webhook → HTTP (getFile Telegram) → HTTP (Claude Vision) → Code (parsear JSON) → HTTP (FiDo API) → Telegram respuesta
3. Añadir nodo switch en Node-RED para separar mensajes foto (→ webhook FiDo) de texto (→ flujo Kryptonite)

---

## 2026-05-14 — Fix caché api.js

Bumped `api.js?v=2` → `?v=3` en `static/index.html` para forzar que el
navegador descargue la versión actualizada del fichero (que incluye `borrarLote`).
Sin este cambio, el navegador servía la versión cacheada anterior y `borrarSeleccionados`
lanzaba `API.borrarLote is not a function`.

---

## 2026-05-14 — Fix selección múltiple y borrado en bloque (segunda iteración)

Tras el primer intento fallido, se diagnosticó y corrigió de forma definitiva.

### Diagnóstico final

La causa era que Alpine.js al usar `x-model` con `:value="mov.id"` (número)
siempre almacena el valor del DOM como cadena (`el.value`). Los métodos
`toggleTodos()` y la expresión inline de la cabecera insertaban números en el
array. La mezcla cadena/número hacía que `includes()` fallara.

El segundo intento (`:checked` + `@change` con `toggleMovimiento`) usaba
`push()` sobre el array reactivo, que en Alpine 3 puede no disparar el
re-renderizado. Además eliminaba `x-model` sin resolver el problema de fondo.

### Solución definitiva

- **Fila individual:** vuelve a `x-model="movSeleccionados"` pero con
  `:value="String(mov.id)"`. Alpine almacena cadenas → comparaciones consistentes.
- **Cabecera:** expresión inline con `$event.target.checked` para leer el estado
  real del clic (sin ambigüedad de timing), y comparación `includes(String(m.id))`.
- **Clase de fila:** `movSeleccionados.includes(String(mov.id))` (cadena).
- **API:** `movSeleccionados.map(Number)` al llamar `borrarLote` (el backend
  espera enteros).
- Eliminados `toggleMovimiento`, `todosSeleccionados`, `toggleTodos` — ya
  no se usan.

Verificado en preview con datos de prueba:
- Selección individual: array recibe cadenas, botón de borrar se habilita.
- Seleccionar/deseleccionar todos: funcionan en ambas direcciones.
- IDs enviados al backend son números.

---

## 2026-05-14 — Fix selección múltiple y borrado en bloque de movimientos

Los checkboxes y el botón de borrado en bloque añadidos el día anterior no
funcionaban de forma fiable: el check de "seleccionar todos" no marcaba las
filas individuales y el borrado en bloque parecía no hacer nada.

### Causa raíz

Mezcla de tipos en `movSeleccionados`. Alpine.js, al usar
`x-model="movSeleccionados"` con `:value="mov.id"`, guarda el `el.value` del DOM
(siempre cadena). Pero `toggleTodos()` y la expresión inline del check de
cabecera insertaban números. La comparación interna de Alpine
(`arr.includes(el.value)`) fallaba al confrontar `[1,2,3]` con `"1"`, dejando
las filas visualmente sin marcar aunque sus IDs estuvieran en el array.

### Solución

Eliminar `x-model` en los checkboxes y usar binding explícito con
`:checked` + `@change`. Así el array siempre contiene números y el comparador
es nuestro, no el de Alpine.

### `static/index.html`

- Checkbox de fila: sustituido `x-model="movSeleccionados" :value="mov.id"` por
  `:checked="movSeleccionados.includes(mov.id)" @change="toggleMovimiento(mov.id)"`.
- Checkbox de cabecera: sustituidas las expresiones inline complejas
  (`movimientos.every(...) ? (...) : (...)`) por llamadas a métodos:
  `:checked="todosSeleccionados()" @change="toggleTodos()"`.
- `:class` de la fila simplificado: `movSeleccionados.includes(mov.id)` (sin
  `.map(Number)`).

### `static/app.js`

- Nuevo método `toggleMovimiento(id)`: añade o quita el id del array.
- `todosSeleccionados()`, `toggleTodos()` y `borrarSeleccionados()` limpiados
  de los `.map(Number)` defensivos — ya no hacen falta porque el array es
  homogéneo (siempre números).

---

## 2026-05-13 — Corrección parser Santander: soporte CSV con separador coma

### `app/parsers/santander.py`
- El parser solo admitía tabulador y punto y coma como separadores. El nuevo
  formato de exportación del Santander usa coma (`,`) con campos entrecomillados
  cuando contienen comas internas (conceptos, importes como `"-165,00"`).
- Cambiado el parseo línea a línea por `csv.reader` (módulo estándar), que
  gestiona correctamente los campos entrecomillados con cualquier separador.
- Añadido método `_detectar_separador`: prueba `\t`, `;` y `,` en orden.
- El parseo de importes y fechas no cambia; ya soportaba el formato sin `EUR`.

---

## 2026-05-07 — Mejoras responsive y corrección de bugs en móvil

### `static/estilos.css` — Font-size adaptativo

- `html { font-size }` cambiado de fijo `150%` (declarado dos veces por duplicado) a tres escalones: `150%` (≥1301px), `125%` (portátiles ≤1300px), `100%` (tablet/móvil ≤900px). Eliminada la declaración duplicada.

### `static/estilos.css` — Fix overlay bloqueaba toda interacción en portrait

- Causa raíz: `.fido-mobile-only { display: flex !important; }` en la media query de ≤767px sobreescribía el `display: none` que Alpine.js pone mediante `x-show` en el overlay del drawer. El overlay quedaba fijo sobre toda la pantalla en portrait, impidiendo cualquier toque.
- Fix: quitado el `!important` de `.fido-mobile-only`. Sin él, el `display: none` inline de Alpine prevalece cuando el drawer está cerrado.

### `static/estilos.css` — Columnas del panel proporcionales

- `.fido-panel-grid` cambiado de `grid-template-columns: 210px 1fr 230px` (anchos fijos en píxeles) a `1fr 2fr 1fr` (proporcional), alineando las proporciones con las del portal hogarOS.

---

## 2026-05-05

### Adopción del header Cockpit unificado de hogar.css

La cabecera de FiDo tenía sus propias clases (`fido-header__*`) con dimensiones
diferentes a las del portal hogarOS: altura 3.5rem (≈52px con font-size 150%)
en lugar de 48px, padding menor, reloj sin fecha, y fuentes distintas.

**Cambios realizados:**

- `static/index.html`: reemplazado `<header id="fido-header">` por `<header class="ck-header">`.
  Ahora usa exactamente la misma estructura HTML que el portal:
  `.ck-hdr-izq` / `.ck-hdr-der`, `.ck-marca-box`, `.ck-marca-txt`, `.ck-sep`,
  `.ck-nav` con `<button>` (en lugar de `<a>`), `.ck-reloj__hora` + `.ck-reloj__fecha`,
  `.ck-tema-btn`.

- `static/estilos.css`: eliminados todos los estilos propios del header
  (~100 líneas de `.fido-header__*`, `.fido-nav__*`, etc.).

- Reloj actualizado: muestra hora con segundos (`HH:MM:SS`) y fecha en
  mayúsculas con año (`MAR, 05 MAY 2026`), idéntico al portal.

**Resultado:** la cabecera de FiDo es visualmente idéntica a la del portal.
Los estilos viven en `hogar.css` — cualquier cambio de diseño en el header
se propaga automáticamente a todas las apps que lo adopten.

## 2026-05-01

### Transferencias internas — cuentas vinculadas

Se implementa el sistema de detección y exclusión de transferencias internas
entre cuentas propias (caso concreto: Caixa → Revolut).

**Motivación:** al importar extractos de ambas cuentas, las recargas a Revolut
aparecían como gasto en Caixa y como ingreso en Revolut, inflando ambos totales
en todos los informes.

**Solución:**
- Nueva tabla `cuentas_vinculadas`: define la relación entre cuentas y los
  patrones de descripción que identifican cada lado de la transferencia.
- Nueva columna `es_transferencia_interna` en `movimientos` (por defecto 0).
- Nuevo servicio `detector_transferencias.py`: busca pares no marcados
  (mismo importe, mismo día ±1, patrones de descripción coincidentes) y los marca.
- La detección se lanza automáticamente al importar cualquier CSV.
- Todos los informes (`/api/panel/*` y `/api/resumen`) filtran los movimientos marcados.

**Patrones configurados (se crean vía API, no en código):**
- Caixa → descripcion LIKE `Recarga`
- Revolut → descripcion LIKE `Recargas: Pago de ANTONIO%`
- Tolerancia: 1 día

**Ficheros nuevos:**
- `app/servicios/detector_transferencias.py`
- `app/rutas/transferencias.py`

**Ficheros modificados:**
- `app/esquema.sql` — tabla `cuentas_vinculadas`
- `app/bd.py` — migraciones v4
- `app/rutas/importar.py` — llama al detector tras importar
- `app/rutas/panel.py` — filtro en resumen, por-categoria, por-mes, por-cuenta
- `app/rutas/resumen.py` — filtro en resumen hogarOS
- `app/principal.py` — registra ruta `/api/transferencias`

---

## 2026-04-27

### Resumen semanal — nuevo parámetro `?periodo=semana`

Añadido parámetro `periodo` a `GET /api/resumen` para soportar el briefing diario
de hogarOS, que necesita el gasto de la semana en curso.

- `?periodo=mes` (por defecto): comportamiento previo sin cambios.
- `?periodo=semana`: devuelve gastos/ingresos/balance desde el lunes de la semana
  actual hasta hoy. La etiqueta `semana` describe el rango, p.ej. "Semana del 21 al 27 abr".
- El portal hogarOS sigue usando `?periodo=mes` (con filtro de cuenta), sin cambios en él.

## 2026-04-25

### AGENTS.md local para Codex

Creado `AGENTS.md` en el repo de FiDo a partir de `CLAUDE.md`, con estructura,
API, variables de entorno, listener NTFY y gotchas operativos.

Añadidas dos normas locales:
- Las transferencias internas duplican ingresos/gastos si se agregan todas las cuentas.
- No subir capturas, logs ni flows de `docs/` sin confirmación explícita.

---

## 2026-04-25

### Resumen mensual filtrable por cuenta

El endpoint `GET /api/resumen` ahora acepta filtros opcionales `cuenta_id`, `cuenta_nombre`
y `banco`. Sin filtros mantiene el comportamiento anterior: suma todas las cuentas.

Motivo: la portada de hogarOS necesita mostrar una visión operativa del mes basada solo
en `Cuenta Antonio (Caixa)`, porque sumar todas las cuentas duplica transferencias internas
y falsea ingresos/gastos.

Ficheros modificados: `app/rutas/resumen.py`

---

## 2026-04-16

### Fix: parser Revolut no extraía la descripción del comercio

**Síntoma:** al importar un extracto de Revolut, todos los movimientos quedaban
sin categoría y la descripción mostraba solo el tipo ("Pago con tarjeta") en
lugar del nombre del comercio.

**Causa:** mojibake (doble codificación de caracteres) en las cabeceras del CSV.
Revolut exporta en UTF-8, pero los bytes de los caracteres acentuados (`C3 B3`
para `ó`) son a la vez UTF-8 válido, así que Python los decodifica sin error y
obtiene `DescripciÃ³n` en lugar de `Descripción`. Eso hace que el mapeo de
cabeceras no encuentre la columna `Description` y la deje vacía.

**Solución** (`app/parsers/revolut.py` → `_normalizar_fila`): antes de buscar en
el mapeo, se intenta revertir el mojibake codificando la clave como Latin-1 y
decodificando como UTF-8. Si falla (clave ya correcta), se usa tal cual.
Afecta también a `Fecha de finalización` y `Comisión`.

---

## 2026-04-08

### Configuración Automate — flow FiDo Gastos

- Recuperado el flow exportado `docs/FiDo - Gastos.flo` y analizado su contenido.
- Verificado que el flow tiene 6 bloques: Flow beginning → When notification (Google Wallet) → Set variable importe_raw (regex) → Set variable importe_raw (replace coma→punto) → Set variable ultima4 (regex) → HTTP request POST a NTFY.
- Identificados dos bugs en los regex:
  - `importe_raw`: carácter corrupto en lugar de `{2}` → corrección: `.*(\d+[.,]\d{2})\s*€.*`
  - `ultima4`: `.*(\d)` solo capturaba 1 dígito → corrección: `\*(\d{4})`
- NTFY_TOPIC configurado en el bloque HTTP request (sustituido el placeholder `TU_TOPIC`).
- Prueba con `curl` exitosa: el servidor FiDo recibe y procesa el movimiento correctamente.
- **Pendiente:** corregir los dos regex en Automate y probar con notificación bancaria real.

---

## 2026-04-07

### Configuración de Automate en el móvil — sesión en curso

Configurando el flow de Automate (LlamaLab) en el móvil para captura automática
de notificaciones de Google Wallet → NTFY → FiDo.

**Decisiones tomadas en esta sesión:**
- Se elige **Google Wallet** como fuente de notificaciones (centraliza todas las
  tarjetas, siempre incluye los últimos 4 dígitos en el cuerpo).
- Formato real confirmado: Título = comercio, Cuerpo = `2,50 € con Visa ••9625`.
- No existe bloque "Text match" en Automate — la extracción regex se hace con
  la función `matches()` dentro de bloques **Variable set**.
- El campo **Request headers** del HTTP request acepta formato diccionario JSON:
  `{"Content-Type":"application/json"}`
- **Problema detectado:** copiar expresiones desde WhatsApp convierte comillas
  rectas `'` en tipográficas `'` que Automate no reconoce → hay que escribir
  el body directamente desde el teclado del móvil.

**Estado del flow al terminar la sesión:**

| # | Bloque | Estado |
|---|--------|--------|
| 1 | Flow beginning | ✅ |
| 2 | Notification posted? (Google Wallet) | ✅ |
| 3 | Variable set — importe_raw (matches) | ✅ |
| 4 | Variable set — importe_raw (replaceAll) | ✅ |
| 5 | Variable set — ultimos4 | ✅ |
| 6 | HTTP request → NTFY | ⚠ Body pendiente |
| 7 | Bucle de retorno | ⏳ Pendiente |

**Próximo paso:** Abrir el bloque HTTP request, campo **Request content body**,
y escribir desde el teclado del móvil (no copiar/pegar):
```
'{"importe":-' + importe_raw + ',"descripcion":"' + descripcion + '","ultimos4":"' + ultimos4 + '"}'
```
Luego conectar la salida del HTTP request de vuelta al bloque Notification posted?

Ver guía completa actualizada en `docs/automate-ntfy.md`.

---

### Campo estado en movimientos — flujo de revisión

Añadido campo `estado` (`ok` | `revisar`) a los movimientos para identificar
entradas que necesitan revisión humana antes de darse por buenas.

**Criterios de asignación automática (listener NTFY):**
- `revisar` — si no se encontró categoría tras auto-categorización
- `revisar` — si se usó la cuenta por defecto (sin `ultimos4` ni `cuenta_id` explícito)
- `ok` — si categoría y cuenta se resolvieron con confianza

**Backend:**
- `app/esquema.sql` — columna `estado TEXT NOT NULL DEFAULT 'ok' CHECK(ok|revisar)`
- `app/bd.py` — migración v3: `ALTER TABLE ADD COLUMN` (no recreación de tabla)
- `app/modelos.py` — campo `estado` en `MovimientoCrear`, `MovimientoActualizar`, `MovimientoRespuesta`
- `app/rutas/movimientos.py` — filtro `?estado=` en listado y total, nuevo endpoint `PUT /{id}/estado`
- `app/servicios/ntfy_listener.py` — lógica de asignación automática de estado
- `app/rutas/sincronizar.py` — `estado` incluido en el INSERT

**Frontend:**
- Filtro "Por revisar / Confirmados / Todos" en la barra de filtros
- Icono ⚠ naranja en cada fila con estado `revisar`, clicable para confirmar (marcar como ok)
- Icono ✓ verde en cada fila con estado `ok`, clicable para marcar como "por revisar"
- Modal de edición/creación: campo "Estado" con selector Confirmado / Por revisar
- Badge `ntfy` con color diferenciado (azul secundario) en la columna origen

---

### Guía MacroDroid (alternativa gratuita a Tasker)

- Añadida `docs/macrodroid-ntfy.md` — guía completa para capturar notificaciones
  bancarias con MacroDroid (gratuito, sin plugins). Cubre triggers, extracción
  de datos con regex, HTTP Request a NTFY y depuración por banco.
- MacroDroid no requiere plugins de pago; Tasker + AutoNotification costarían ~7€.
- `docs/tasker-ntfy.md` se mantiene como referencia alternativa.

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
