# CLAUDE.md — FiDo

## Qué es

**FiDo** (Finanzas Domésticas) es el gestor de finanzas del ecosistema hogarOS.
Importa extractos bancarios, categoriza movimientos y muestra resúmenes por cuenta y miembro.

- **GitHub:** acabellan1868-prog/FiDo
- **Ruta local:** `E:\Documentos\Desarrollo\claude\FiDo\`
- **En el servidor:** `/mnt/datos/fido-build/` (git clone, build context Docker)
- **Datos persistentes:** `/mnt/datos/fido/fido.db`

---

## Estructura del repo

```
FiDo/
├── app/
│   ├── principal.py            → Punto de entrada FastAPI
│   ├── bd.py                   → Acceso a SQLite (fido.db)
│   ├── esquema.sql             → DDL de la base de datos
│   ├── modelos.py              → Modelos Pydantic
│   ├── datos_iniciales.py      → Seed de categorías y cuentas
│   ├── parsers/
│   │   ├── base.py             → Clase base Parser
│   │   ├── caixabank.py        → Parser extractos CaixaBank (CSV, cabeceras flexibles)
│   │   ├── revolut.py          → Parser extractos Revolut (CSV)
│   │   └── santander.py        → Parser extractos Santander (CSV)
│   ├── rutas/
│   │   ├── movimientos.py      → CRUD movimientos
│   │   ├── categorias.py       → CRUD categorías
│   │   ├── cuentas.py          → CRUD cuentas
│   │   ├── miembros.py         → CRUD miembros del hogar
│   │   ├── importar.py         → POST /importar — sube y parsea extracto
│   │   ├── reglas.py           → Reglas de auto-categorización
│   │   ├── sincronizar.py      → Sincronización de datos
│   │   ├── mapeo_tarjetas.py   → Mapeo tarjeta → cuenta
│   │   ├── panel.py            → Datos para el dashboard
│   │   └── resumen.py          → Resúmenes y estadísticas
│   └── servicios/
│       ├── categorizador.py    → Lógica de categorización automática
│       └── deduplicador.py     → Deduplicación de movimientos al importar
├── static/
│   ├── index.html              → Frontend SPA
│   ├── app.js                  → Lógica principal del frontend
│   ├── api.js                  → Capa de acceso a la API
│   └── estilos.css             → CSS propio de FiDo (aún no usa hogar.css)
├── data/
│   └── .gitkeep
├── Dockerfile
├── docker-compose.yml          → Solo para desarrollo local
└── requirements.txt
```

---

## Integración con hogarOS

FiDo se sirve en `/finanzas/` a través del Nginx de hogarOS.

**Puerto:** 8080 (interno Docker, nombre de contenedor `fido`)

### CSS propio vs design system

FiDo tiene su propio `static/estilos.css` y **aún no usa `hogar.css`**.
Pendiente migrar al design system Living Sanctuary (igual que se hizo con ReDo).
Cuando se migre, aplicar el mismo patrón: `<link href="/static/hogar.css">`
y nginx servirá el fichero desde `portal/static/` vía `location /finanzas/static/`.

---

## API principal

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/movimientos` | Lista movimientos con filtros |
| POST | `/importar` | Sube extracto bancario (CSV) |
| GET/POST | `/categorias` | CRUD categorías |
| GET/POST | `/cuentas` | CRUD cuentas bancarias |
| GET | `/panel` | Datos del dashboard |
| GET | `/resumen` | Resúmenes y estadísticas |
| GET/POST | `/reglas` | Reglas de auto-categorización |

---

## Bancos soportados (parsers)

| Banco | Formato | Notas |
|---|---|---|
| CaixaBank | CSV | Cabeceras flexibles, detección automática |
| Revolut | CSV | Formato estándar Revolut |
| Santander | CSV | Formato estándar Santander |

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `FIDO_DB_PATH` | Ruta a la BD SQLite (por defecto `data/fido.db`) |
| `TZ` | Zona horaria (Europe/Madrid) |

---

## Convenciones de código

- Todo en español: variables, funciones, clases, comentarios
- Backend: Python + FastAPI + SQLite
- Frontend: HTML/CSS/JS vanilla, sin frameworks ni bundlers
