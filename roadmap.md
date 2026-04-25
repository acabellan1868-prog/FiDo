# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-04-08

El flow de Automate (LlamaLab) está creado con 6 bloques y el topic NTFY configurado.
La prueba con `curl` es exitosa — el servidor recibe y procesa movimientos correctamente.
Pendiente corregir dos regex en el flow y hacer la prueba end-to-end con notificación bancaria real.

**Nota 2026-04-25:** `GET /api/resumen` acepta filtros de cuenta para que hogarOS pueda
mostrar la lectura mensual de `Cuenta Antonio (Caixa)` sin duplicar transferencias internas.

**Próximo paso:** Corregir regex de `importe_raw` y `ultima4` en Automate, luego probar con un pago real con tarjeta.

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

### Fase 4 — Captura automática desde el móvil (en curso)

- [x] Listener NTFY en segundo plano dentro de FiDo (2026-04-06)
- [x] Migración de BD para soportar origen 'ntfy' (2026-04-06)
- [x] Campo `estado` (ok | revisar) con asignación automática (2026-04-07)
- [x] Flujo de revisión en la UI: icono ⚠/✓ en tabla, campo en modal (2026-04-07)
- [x] Gestión de datos sensibles: `.env` / `.env.example` en todos los proyectos (2026-04-07)
- [x] Guías de configuración: `docs/macrodroid-ntfy.md`, `docs/tasker-ntfy.md` y `docs/automate-ntfy.md` (2026-04-07)
- [ ] Configurar app de automatización en el móvil (Tasker / MacroDroid / Automate)
- [ ] Pruebas end-to-end con notificaciones bancarias reales

### Fase 5 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
