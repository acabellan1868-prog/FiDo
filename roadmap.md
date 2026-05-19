# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-05-15

**Fase 4 completada ✅** — captura automática de gastos desde el móvil funcionando.

**Flujo activo:**
1. Usuario hace captura de pantalla de la notificación (Google Wallet, Revolut…)
2. La sube a Google Drive: `Proyectos/Desarrollo/hogarOS/FiDo/gastosPendientes/`
3. Tarea programada `fido-gastos-drive` en Cowork corre cada 30 min (:17 y :47)
4. Claude lee la imagen directamente (multimodal), extrae importe/comercio/tarjeta
5. Resuelve la cuenta por mapeo de tarjeta (ver CLAUDE.md) y llama a la API de FiDo
6. Copia la imagen a la carpeta `procesadas/` para no reprocesar

**Prueba end-to-end superada:** BAR CASA MIGUEL -7.10€ (Revolut 9625 → cuenta_id 8).

**Próximo paso:** Fase 5 (resúmenes, exportación, presupuestos) o mejoras de usabilidad.

Ver documentación detallada en `capturaGastosIA.md`.

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
