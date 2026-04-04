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
| GET | `/movimientos` | Lista con filtros |
| POST | `/importar` | Sube extracto CSV |
| GET/POST | `/categorias` | CRUD |
| GET/POST | `/cuentas` | CRUD |
| GET | `/panel` | Dashboard |
| GET | `/resumen` | Estadísticas |
| GET/POST | `/reglas` | Auto-categorización |

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `FIDO_DB_PATH` | Ruta BD SQLite (defecto `data/fido.db`) |
| `TZ` | Zona horaria (`Europe/Madrid`) |

## hogar.css
Nginx reescribe `/static/` → `/finanzas/static/` y lo sirve desde `portal/static/` de hogarOS. FiDo no sirve `hogar.css` por sí mismo.
