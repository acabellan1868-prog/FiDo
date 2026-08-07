# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-08-07

**Fase 4 completada ✅** — captura automática de gastos desde el móvil funcionando (ver detalle del flujo Drive + Claude Vision en `capturaGastosIA.md`).

**Trabajo de hoy:**
1. Importación de extractos ampliada a Excel (`.xlsx` y `.xls`), además de CSV/TSV — detección automática por extensión, sin tocar los parsers de banco.
2. Investigadas y corregidas dos causas de movimientos duplicados: race condition en el listener NTFY durante redeploys (19 grupos, ya limpiados en producción) y duplicado cruzado CSV↔NTFY sin detectar (5 casos confirmados, sin limpiar aún). Añadido índice único sobre `huella` para bloquear la primera causa a nivel de base de datos.

Ver el detalle completo en `bitacora.md` (entrada 2026-08-07).

**Próximo paso concreto:**
1. Redesplegar el contenedor para que la migración v6 (índice único) se aplique en producción — está en el código pero aún no activa.
2. Diseñar la reconciliación de duplicados cruzados CSV↔NTFY: margen de días direccional y configurable por cuenta/banco (CaixaBank liquida con retraso, Revolut al instante), y siempre marcar como `estado='revisar'` en vez de auto-fusionar.

---

## Fases

### Fase 1 — MVP funcional ✅

- [x] Backend FastAPI con SQLite
- [x] Parsers de extractos: CaixaBank, Santander, Revolut
- [x] CRUD de movimientos con filtros
- [x] Sistema de categorías jerárquico (padre/hija)
- [x] Auto-categorización por reglas de patrón
- [x] Deduplicación de movimientos al importar
- [x] Dashboard con gráficos (Chart.js)
- [x] Gestión de cuentas y miembros
- [x] Mapeo de tarjetas a cuentas

### Fase 2 — Integración hogarOS ✅

- [x] Docker con proxy Nginx en `/finanzas/`
- [x] api.js con autodetección de prefijo

### Fase 3 — Mejoras de usabilidad (en curso)

- [x] Desplegables de categorías agrupados por padre (2026-03-22)
- [x] Formulario de movimientos en modal emergente (2026-03-23)
- [x] Filtros avanzados: categoría padre/sub, tipo gasto/ingreso, suma total (2026-03-24)
- [x] Migración al design system Living Sanctuary (hogar.css) (2026-03-29)
- [x] Drawer lateral con navegación entre apps (2026-03-22)
- [x] Selección múltiple y borrado en bloque de movimientos (2026-05-14)
- [x] Importación de extractos en Excel (.xlsx y .xls) (2026-08-07)
- [x] Índice único sobre huella + limpieza de duplicados NTFY (2026-08-07)

### Fase 4 — Captura automática desde el móvil (rediseñada)

> ⚠ El enfoque original (Automate + NTFY) fue descartado el 2026-05-15.
> Android impide leer el contenido de notificaciones de apps financieras.
> Nuevo enfoque: foto de pantalla → Telegram → n8n → Claude Vision → FiDo API.

**Infraestructura NTFY ya construida (reutilizable):**
- [x] Listener NTFY en segundo plano dentro de FiDo (2026-04-06)
- [x] Migración de BD para soportar origen 'ntfy' (2026-04-06)
- [x] Campo `estado` (ok | revisar) con asignación automática (2026-04-07)
- [x] Flujo de revisión en la UI: icono ⚠/✓ en tabla, campo en modal (2026-04-07)
- [x] Gestión de datos sensibles: `.env` / `.env.example` (2026-04-07)

**Nuevo flujo — Drive + Claude Vision (implementado 2026-05-15):**
- [x] Carpeta Drive `gastosPendientes` creada 🤖
- [x] Carpeta Drive `procesadas` creada 🤖
- [x] Tarea programada `fido-gastos-drive` creada en Cowork (persiste entre sesiones) 🤖
- [x] Prueba end-to-end: captura real de BAR CASA MIGUEL -7.10€ procesada correctamente 👤🤖
- [x] Mapeo de tarjetas documentado en CLAUDE.md 🤖

### Fase 5 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
- [ ] Reconciliación de duplicados cruzados CSV↔NTFY (margen de liquidación configurable por cuenta/banco, siempre a revisión manual)
