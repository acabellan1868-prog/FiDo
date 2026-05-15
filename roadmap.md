# Roadmap — FiDo

## Estado actual

**Fecha:** 2026-05-15

El enfoque de Automate + NTFY para captura automática de notificaciones bancarias
ha sido descartado: Android impide que apps de automatización lean el contenido
de notificaciones de apps financieras (Google Wallet, banca). El flow de Automate
queda obsoleto.

**Nuevo enfoque acordado (Fase 4 rediseñada v2):** captura manual mínima vía foto + OCR.
El usuario hace una captura de pantalla de la notificación/confirmación de pago
y la envía al bot de Telegram. Node-RED la recibe (ya hace polling), pasa el
`file_id` a un webhook de n8n. n8n descarga la imagen, **aplica Tesseract OCR gratuito**
para extraer texto, parsea con regex para obtener importe/comercio/últimos 4 dígitos,
y llama a la API de FiDo para guardar el movimiento. Telegram responde confirmando.

**Cambio de Claude Vision API a Tesseract OCR:**
Anthropic ahora requiere créditos pagos ($5+ USD) incluso para "plan gratuito".
Tesseract OCR es gratuito, open source, y suficiente para imágenes claras de notificaciones.

**Próximo paso:**
1. Montar el flow en n8n: webhook → descarga foto de Telegram → Tesseract OCR → Code (parse regex) → FiDo API
2. Probar con captura real de notificación
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

**Nuevo flujo (pendiente) — OCR Tesseract:**
- [ ] Flow n8n: webhook → descarga foto Telegram → Tesseract OCR → Code (parse) → FiDo API 🤖
- [ ] Prueba con captura real de notificación (Wallet/Revolut) para validar OCR 👤
- [ ] Ajustar regex si es necesario basándose en resultados OCR 🤖
- [ ] Nodo switch en Node-RED: foto → webhook FiDo / texto → flujo Kryptonite 🤖

### Fase 5 — Futuro

- [ ] Resúmenes por período y comparativas
- [ ] Exportación de datos
- [ ] Presupuestos por categoría
