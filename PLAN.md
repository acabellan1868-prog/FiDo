# Plan: FiDo v1 — Implementación completa

## Contexto
FiDo es una app web de finanzas domésticas familiares. El diseño está completo (finanzas-familia-resumen.md), la configuración confirmada. No hay código aún — solo documentación. Este plan cubre la implementación completa de la v1 desplegable en Docker.

**Todo el código en español:** nombres de ficheros, funciones, variables, columnas de BD, endpoints API, comentarios.

## Decisiones técnicas
- **SQLite directo** (sin SQLAlchemy) — esquema pequeño y estable, menos dependencias, queries visibles
- **Tailwind CSS via CDN** — sin build step, estilo profesional rápido, válido para red privada
- **Pydantic** para validación request/response
- **uvicorn** como servidor ASGI

## Estructura del proyecto
```
FiDo/
├── app/
│   ├── __init__.py
│   ├── principal.py            # FastAPI app, lifespan, montar estáticos
│   ├── bd.py                   # SQLite conexión, helpers, WAL mode
│   ├── esquema.sql             # CREATE TABLE (6 tablas + índices)
│   ├── datos_iniciales.py      # Categorías, reglas, miembros, cuentas seed
│   ├── modelos.py              # Pydantic schemas (Crear/Actualizar/Respuesta)
│   ├── rutas/
│   │   ├── __init__.py
│   │   ├── miembros.py         # CRUD /api/miembros
│   │   ├── cuentas.py          # CRUD /api/cuentas
│   │   ├── categorias.py       # CRUD /api/categorias (árbol 2 niveles)
│   │   ├── reglas.py           # CRUD /api/reglas
│   │   ├── movimientos.py      # CRUD /api/movimientos + filtros
│   │   ├── mapeo_tarjetas.py   # CRUD /api/mapeo-tarjetas
│   │   ├── importar.py         # POST /api/importar/csv
│   │   ├── sincronizar.py      # POST /api/sincronizar/movimientos + GET /ping
│   │   └── panel.py            # GET /api/panel/*
│   ├── servicios/
│   │   ├── __init__.py
│   │   ├── categorizador.py    # Patrón → categoria_id
│   │   └── deduplicador.py     # Huella + detección duplicados
│   └── parsers/
│       ├── __init__.py
│       ├── base.py             # Parser abstracto
│       └── santander.py        # Parser Santander
├── static/
│   ├── index.html              # SPA con tabs (Alpine.js + Tailwind + Chart.js)
│   ├── app.js                  # Lógica Alpine.js
│   ├── api.js                  # Cliente API (fetch wrappers)
│   └── estilos.css             # CSS mínimo extra
├── data/                       # Volumen Docker (.gitkeep)
├── requirements.txt            # fastapi, uvicorn, python-multipart
├── Dockerfile
└── docker-compose.yml          # Para Portainer stack
```

## Tablas SQLite (columnas en español)

### miembros
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| nombre | TEXT NOT NULL | UNIQUE |
| telegram_chat_id | TEXT | |
| creado_en | TEXT | default datetime('now') |

### cuentas
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| nombre | TEXT NOT NULL | |
| banco | TEXT | santander, caixabank, revolut |
| iban | TEXT | |
| miembro_id | INTEGER | FK → miembros(id) |
| es_compartida | INTEGER | 0/1, default 0 |
| creado_en | TEXT | default datetime('now') |

### categorias
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| nombre | TEXT NOT NULL | |
| padre_id | INTEGER | FK → categorias(id), NULL = nivel 1 |
| icono | TEXT | emoji |
| orden | INTEGER | default 0 |
| | | UNIQUE(nombre, padre_id) |

### reglas
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| patron | TEXT NOT NULL | texto a buscar (case insensitive) |
| categoria_id | INTEGER NOT NULL | FK → categorias(id) |
| prioridad | INTEGER | default 0, mayor = antes |
| creado_en | TEXT | default datetime('now') |

### movimientos
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| fecha | TEXT NOT NULL | YYYY-MM-DD |
| fecha_valor | TEXT | YYYY-MM-DD |
| importe | REAL NOT NULL | negativo = gasto |
| descripcion | TEXT NOT NULL | limpia |
| descripcion_original | TEXT | tal cual viene del banco |
| categoria_id | INTEGER | FK → categorias(id) |
| cuenta_id | INTEGER NOT NULL | FK → cuentas(id) |
| origen | TEXT NOT NULL | CHECK: telegram, wallet, csv, web |
| origen_ref | TEXT | ID externo para dedup |
| huella | TEXT | SHA-256 truncado, indexado |
| notas | TEXT | |
| creado_en | TEXT | default datetime('now') |

### mapeo_tarjetas
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| ultimos4 | TEXT NOT NULL | UNIQUE |
| cuenta_id | INTEGER NOT NULL | FK → cuentas(id) |
| etiqueta | TEXT | |

**Índices:** fecha, cuenta_id, categoria_id, huella en movimientos. patron en reglas.
**Pragmas:** journal_mode=WAL + foreign_keys=ON.

## Endpoints API (en español)

### CRUD básico
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/miembros` | Listar / Crear miembro |
| PUT/DELETE | `/api/miembros/{id}` | Editar / Borrar |
| GET/POST | `/api/cuentas` | Listar / Crear cuenta |
| PUT/DELETE | `/api/cuentas/{id}` | Editar / Borrar |
| GET/POST | `/api/categorias` | Árbol completo / Crear categoría |
| PUT/DELETE | `/api/categorias/{id}` | Editar / Borrar |
| GET/POST | `/api/reglas` | Listar / Crear regla |
| PUT/DELETE | `/api/reglas/{id}` | Editar / Borrar |
| GET/POST | `/api/movimientos` | Listar (con filtros) / Crear |
| PUT/DELETE | `/api/movimientos/{id}` | Editar / Borrar |
| GET/POST | `/api/mapeo-tarjetas` | Listar / Crear mapeo |
| PUT/DELETE | `/api/mapeo-tarjetas/{id}` | Editar / Borrar |

### Filtros de movimientos
`?mes=2026-03&cuenta_id=1&categoria_id=5&origen=csv&buscar=mercadona&offset=0&limite=50`

### Importación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/importar/csv` | Multipart: fichero + cuenta_id + banco |

### Sincronización (app Android)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/sincronizar/ping` | Health check → {"estado": "ok"} |
| POST | `/api/sincronizar/movimientos` | Batch de movimientos desde la app |

### Panel (dashboard)
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/panel/resumen` | Ingresos, gastos, balance, nº movimientos |
| GET | `/api/panel/por-categoria` | Gastos agrupados por categoría padre+hija |
| GET | `/api/panel/por-mes` | Evolución mensual (últimos 12 meses) |
| GET | `/api/panel/por-cuenta` | Totales por cuenta |

## Funciones Python (nombres en español)

### bd.py
- `obtener_conexion()` → sqlite3.Connection
- `inicializar_bd()` → ejecuta esquema.sql
- `consultar_todos(sql, params)` → list[dict]
- `consultar_uno(sql, params)` → dict | None
- `ejecutar(sql, params)` → int (lastrowid)
- `ejecutar_varios(sql, lista_params)` → None

### servicios/categorizador.py
- `categorizar(descripcion)` → categoria_id | None

### servicios/deduplicador.py
- `calcular_huella(fecha, importe, descripcion)` → str
- `buscar_duplicados(fecha, importe, descripcion)` → list[dict]

### datos_iniciales.py
- `sembrar_si_vacio()` → inserta categorías, reglas, miembros, cuentas si la BD está vacía

## Fases de implementación

### Fase 1: Cimientos (BD + API CRUD + Docker)
**Ficheros:**
- `requirements.txt` — fastapi, uvicorn[standard], python-multipart
- `app/__init__.py` — vacío
- `app/esquema.sql` — 6 tablas + índices
- `app/bd.py` — conexión, helpers, WAL, foreign_keys
- `app/datos_iniciales.py` — seed de 13 categorías padre, ~40 hijas, 27 reglas, 2 miembros, 4 cuentas
- `app/modelos.py` — Pydantic: Crear/Actualizar/Respuesta por entidad
- `app/principal.py` — FastAPI, lifespan (inicializar_bd + sembrar), routers, StaticFiles
- `app/rutas/__init__.py` — vacío
- `app/rutas/miembros.py` — CRUD
- `app/rutas/cuentas.py` — CRUD
- `app/rutas/categorias.py` — CRUD con árbol
- `app/rutas/reglas.py` — CRUD
- `app/rutas/movimientos.py` — CRUD con filtros y paginación
- `app/rutas/mapeo_tarjetas.py` — CRUD
- `Dockerfile` — python:3.12-slim, uvicorn :8080
- `docker-compose.yml` — volumen /mnt/datos/fido, TZ, restart
- `data/.gitkeep`

### Fase 2: Lógica de negocio
**Ficheros:**
- `app/servicios/__init__.py`
- `app/servicios/categorizador.py` — match patrón en reglas, por prioridad
- `app/servicios/deduplicador.py` — huella SHA-256 + fuzzy (importe + fecha ±1 día)
- `app/parsers/__init__.py`
- `app/parsers/base.py` — clase abstracta
- `app/parsers/santander.py` — parser formato Santander
- `app/rutas/importar.py` — upload + parse + categorizar + dedup + insertar

### Fase 3: Sync y Panel
**Ficheros:**
- `app/rutas/sincronizar.py` — ping + batch movimientos
- `app/rutas/panel.py` — resumen, por-categoria, por-mes, por-cuenta

### Fase 4: Frontend
**Ficheros:**
- `static/index.html` — SPA: 6 tabs con Tailwind + Alpine.js + Chart.js (CDN)
- `static/api.js` — cliente fetch
- `static/app.js` — componente Alpine.js completo
- `static/estilos.css` — ajustes mínimos

**Tabs:**
1. **Panel** — tarjetas resumen + gráfica donut por categoría + barras por mes
2. **Movimientos** — tabla filtrable (mes, cuenta, categoría, búsqueda), editar/borrar
3. **Importar** — subir fichero, seleccionar cuenta y banco, resultados
4. **Categorías** — árbol colapsable, añadir/editar/borrar
5. **Reglas** — tabla con patrón, categoría, prioridad, CRUD
6. **Ajustes** — miembros, cuentas, mapeo tarjetas

### Fase 5: Pulido
- Manejo errores (IntegrityError → 409, NotFound → 404, BadRequest → 400)
- Auto-categorización en todos los caminos de creación
- Responsive mobile
- Crear directorio data/ si no existe al arrancar

## Docker-compose (para Portainer stack)
```yaml
version: "3.8"
services:
  fido:
    build: .
    container_name: fido
    ports:
      - "8080:8080"
    volumes:
      - /mnt/datos/fido:/app/data
    environment:
      - TZ=Europe/Madrid
      - FIDO_DB_PATH=/app/data/fido.db
    restart: always
```

## Verificación
1. `docker-compose up` → app arranca, crea fido.db, inserta seed
2. `http://192.168.31.131:8080/docs` → Swagger UI con todos los endpoints en español
3. `http://192.168.31.131:8080/` → Frontend con panel
4. Crear movimiento manual desde web → aparece en lista
5. Importar extracto Santander → movimientos categorizados + dedup
6. GET `/api/sincronizar/ping` → `{"estado": "ok"}`
7. POST `/api/sincronizar/movimientos` → batch insertado
8. Panel muestra gráficas con datos reales
