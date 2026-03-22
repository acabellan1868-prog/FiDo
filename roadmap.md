# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-03-22

El proyecto está funcional y desplegado. En esta sesión se han agrupado los
desplegables de categorías (movimientos, formulario nuevo/editar y reglas)
usando `<optgroup>` por categoría padre con subcategorías ordenadas
alfabéticamente. Commit `4dc4036` subido a GitHub.

**Próximo paso:** Desplegar en la VM 101 y verificar que los desplegables
agrupados funcionan correctamente. Pendiente migración al design system
Living Sanctuary (hogar.css).

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
- [ ] Migración al design system Living Sanctuary (hogar.css)
- [ ] Drawer lateral con navegación entre apps

### Fase 4 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
