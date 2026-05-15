# CLAUDE.md — FiDo

## Qué es
Gestor de finanzas domésticas. Importa extractos bancarios, categoriza movimientos, muestra resúmenes por cuenta y miembro.

- **Repo:** acabellan1868-prog/FiDo
- **Local:** `Desarrollo/FiDo/`
- **Servidor:** `/mnt/datos/fido-build/` (build context), `/mnt/datos/fido/fido.db` (datos)
- **Proxy:** `/finanzas/` → `fido:8080`

## Estructura

```
FiDo/
├── app/
│   ├── principal.py
│   ├── bd.py
│   ├── esquema.sql
│   ├── modelos.py
│   ├── datos_iniciales.py
│   ├── parsers/
│   │   ├── base.py
│   │   ├── caixabank.py        ← cabeceras flexibles, detección automática
│   │   ├── revolut.py
│   │   └── santander.py
│   ├── rutas/
│   │   ├── movimientos.py
│   │   ├── categorias.py
│   │   ├── cuentas.py
│   │   ├── miembros.py
│   │   ├── importar.py
│   │   ├── reglas.py
│   │   ├── sincronizar.py
│   │   ├── mapeo_tarjetas.py
│   │   ├── panel.py
│   │   └── resumen.py
│   └── servicios/
│       ├── categorizador.py
│       └── deduplicador.py
├── static/
│   ├── index.html
│   ├── app.js
│   ├── api.js                  ← autodetecta prefijo (/finanzas/ o /)
│   └── estilos.css             ← prefijo fido-, usa variables de hogar.css
└── Dockerfile
```

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/movimientos` | Lista con filtros (`mes`, `cuenta_id`, `categoria_id`, `tipo`, `estado`, `buscar`) |
| GET | `/movimientos/total` | Cuenta y suma de importes (para paginación) |
| GET/PUT/DELETE | `/movimientos/{id}` | Obtener, editar o borrar un movimiento |
| PUT | `/movimientos/{id}/estado` | Cambiar estado: `ok` \| `revisar` |
| POST | `/movimientos/recategorizar` | Recategoriza los movimientos sin categoría |
| POST | `/importar` | Sube extracto CSV |
| GET/POST | `/categorias` | CRUD de categorías |
| GET/POST | `/cuentas` | CRUD de cuentas |
| GET/POST/DELETE | `/mapeo_tarjetas` | Mapeo últimos 4 dígitos → cuenta |
| GET | `/panel` | Dashboard |
| GET | `/resumen` | Estadísticas por categoría y cuenta |
| GET/POST | `/reglas` | Auto-categorización por palabras clave |
| GET | `/sincronizar/ping` | Health-check (sondeo de disponibilidad) para la app Android |
| POST | `/sincronizar/movimientos` | Recibe lote de movimientos desde app Android |

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `FIDO_DB_PATH` | Ruta BD SQLite (defecto `data/fido.db`) |
| `TZ` | Zona horaria (`Europe/Madrid`) |
| `NTFY_URL` | URL base del servidor NTFY (defecto `https://ntfy.sh`) |
| `NTFY_TOPIC` | Topic privado para recibir movimientos desde el móvil. Si está vacío, el listener se desactiva. El valor real está en `docker-compose.yml` (no en el repositorio público). |
| `NTFY_CUENTA_DEFAULT` | ID de cuenta a usar cuando el mensaje NTFY no especifica cuenta ni tarjeta |

## Listener NTFY — captura automática desde el móvil

FiDo incluye un listener que se suscribe a un topic privado de NTFY mediante
SSE (Server-Sent Events, flujo de eventos del servidor). Cuando Tasker (app
Android) detecta una notificación bancaria, la parsea y la publica en ese topic.
FiDo la recibe y la inserta como movimiento automáticamente.

Esto resuelve el problema de conectividad: el móvil no necesita estar en la red
local. NTFY actúa de intermediario en la nube; FiDo siempre está conectado
desde la VM.

### Formato del mensaje que envía Tasker

El body del mensaje NTFY debe ser un JSON con estos campos:

```json
{
    "importe": -45.50,
    "descripcion": "Mercadona",
    "ultimos4": "1234",
    "fecha": "2026-04-06"
}
```

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `importe` | Sí | Negativo = gasto, positivo = ingreso |
| `descripcion` | No | Nombre del comercio. Defecto: "Sin descripción" |
| `cuenta_id` | No* | ID directo de la cuenta en FiDo |
| `ultimos4` | No* | Últimos 4 dígitos de la tarjeta (se busca en mapeo_tarjetas) |
| `fecha` | No | Formato YYYY-MM-DD. Defecto: hoy |
| `categoria_id` | No | Si no se envía, se auto-categoriza por las reglas |
| `notas` | No | Texto libre |

*Al menos uno de `cuenta_id`, `ultimos4` o `NTFY_CUENTA_DEFAULT` debe estar disponible.

### Lógica de resolución de cuenta

1. `cuenta_id` explícito en el mensaje
2. `ultimos4` → búsqueda en la tabla `mapeo_tarjetas`
3. Variable de entorno `NTFY_CUENTA_DEFAULT`

### Reconexión automática

Si la conexión con NTFY se pierde, el listener reintenta con espera exponencial
(5s → 10s → 20s → … → máximo 5 min). Al reconectar, recupera los mensajes de
las últimas 12 horas para no perder movimientos durante caídas breves.

### Archivo del listener

`app/servicios/ntfy_listener.py`

### Configuración de Tasker (app Android)

Ver la guía completa de configuración en `docs/macrodroid-ntfy.md` (MacroDroid, gratuito).
La guía original de Tasker sigue disponible en `docs/tasker-ntfy.md`.

## Captura automática de gastos — Drive + Claude Vision (Fase 4)

El flujo activo para capturar gastos desde el móvil:

1. Usuario sube captura de pantalla a Google Drive
2. Tarea `fido-gastos-drive` en Cowork corre a :17 y :47 cada hora (persiste entre sesiones)
3. Claude lee la imagen, extrae datos y llama a `POST /finanzas/api/movimientos`

### Carpetas Drive (cuenta acabellan.1868@gmail.com)

| Carpeta | Drive ID |
|---------|----------|
| Pendientes | `1Hzd7V4N5Gwy9_0Zy3GQsudQdOiKI_Pvn` |
| Procesadas | `1qhHxIFMCogIJGjLAjy8KwKBwRaP_FgFf` |

### Mapeo tarjeta → cuenta_id

| Últimos 4 | cuenta_id | Descripción |
|-----------|-----------|-------------|
| 9625 | 8 | Cuenta Antonio (Revolut) |
| 5911 | 5 | Cuenta Antonio (Caixa) |
| 5155 | 3 | Cuenta Común |
| (otros) | 5 | Caixa por defecto |

### Parámetros del POST

```json
{
  "importe": -7.10,
  "descripcion": "BAR CASA MIGUEL",
  "cuenta_id": 8,
  "fecha": "2026-04-15",
  "origen": "ntfy",
  "estado": "revisar"
}
```

---

## hogar.css y header compartido

Nginx reescribe `/static/` → `/finanzas/static/` y lo sirve desde `portal/static/` de hogarOS.
FiDo no sirve `hogar.css` por sí mismo.

### Header — clases de hogar.css

FiDo usa las clases del header Cockpit definidas en `hogar.css` (sección 7b), las mismas
que el portal hogarOS. **No hay estilos de cabecera en `estilos.css`.**

Clases en uso: `.ck-header`, `.ck-hdr-izq`, `.ck-hdr-der`, `.ck-marca-box`, `.ck-marca-dot`,
`.ck-marca-txt`, `.ck-marca-sub`, `.ck-sep`, `.ck-nav`, `.ck-reloj`, `.ck-reloj__hora`,
`.ck-reloj__fecha`, `.ck-tema-btn`.

La nav usa `<button>` con Alpine.js (`:class="pestana === 'X' ? 'activo' : ''"`) en lugar
de `<a>` como en el portal.

Ver la estructura completa y el snippet del reloj en `hogarOS/CLAUDE.md`
(sección "Header Cockpit compartido").
