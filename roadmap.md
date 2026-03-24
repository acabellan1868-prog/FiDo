# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-03-24

El proyecto está funcional y desplegado. En esta sesión se han añadido
filtros avanzados en movimientos: filtro por categoría padre/subcategoría,
filtro por tipo (gasto/ingreso) y suma total de los movimientos filtrados.

**Próximo paso:** Pendiente migración al design system Living Sanctuary
(hogar.css).

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
- [ ] Migración al design system Living Sanctuary (hogar.css)
- [ ] Drawer lateral con navegación entre apps

### Fase 4 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
