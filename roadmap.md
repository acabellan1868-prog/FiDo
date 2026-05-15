# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-05-15

El enfoque de Automate + NTFY para captura automática de notificaciones bancarias
ha sido descartado: Android impide que apps de automatización lean el contenido
de notificaciones de apps financieras (Google Wallet, banca). El flow de Automate
queda obsoleto.

**Nuevo enfoque acordado (Fase 4 rediseñada):** captura manual mínima vía foto.
El usuario hace una captura de pantalla de la notificación/confirmación de pago
y la envía al bot de Telegram. Node-RED la recibe (ya hace polling), pasa el
`file_id` a un webhook de n8n, que descarga la imagen, la envía a Claude Vision
(API de Anthropic) para extraer importe/comercio/últimos 4 dígitos, y llama a
la API de FiDo para guardar el movimiento. Telegram responde confirmando el alta.

**Próximo paso:**
1. Crear la API key en `console.anthropic.com` (cuenta ya existe, plan gratuito suficiente)
2. Montar el flow en n8n: webhook → descarga foto de Telegram → Claude Vision → FiDo API
3. Añadir nodo switch en Node-RED para separar mensajes de foto (FiDo) de texto (Kryptonite)

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

**Nuevo flujo (pendiente):**
- [ ] Crear API key en console.anthropic.com 👤
- [ ] Flow n8n: webhook → descarga foto Telegram → Claude Vision → FiDo API 🤖
- [ ] Nodo switch en Node-RED: foto → webhook FiDo / texto → flujo Kryptonite 🤖
- [ ] Prueba end-to-end con captura real de notificación bancaria 👤

### Fase 5 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
