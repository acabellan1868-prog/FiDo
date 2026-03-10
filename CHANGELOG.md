# Changelog — FiDo (Finanzas Domésticas)

Registro de todos los cambios del proyecto, ordenado de más reciente a más antiguo.

---

## 2026-03-10

### 14:30 — Fix gráficas pantalla completa + reglas categorización CaixaBank/Revolut
- **Corregido:** Gráficas no se mostraban en pantalla completa. Añadido contenedor con altura fija (300px) y `maintainAspectRatio: false`.
- **Añadido:** ~60 reglas de categorización nuevas para comercios habituales de CaixaBank y Revolut (Bk Hue, parkinglibre, Granier, Amazon, Claude.ai, etc.).
- **Añadido:** Las reglas nuevas se insertan automáticamente en cada arranque si no existen (idempotente).
- **Añadido:** Endpoint `POST /api/movimientos/recategorizar` para aplicar reglas a movimientos sin categoría.
- **Añadido:** Botón "Recategorizar" en la sección de importación.
- Ficheros modificados: `static/index.html`, `static/app.js`, `app/datos_iniciales.py`, `app/rutas/movimientos.py`

### 14:00 — Fix gráficas del panel no se renderizan
- **Corregido:** URL CDN de Chart.js apuntaba al paquete genérico, ahora apunta al UMD bundle específico.
- **Corregido:** `toFixed(2)` devolvía string en vez de número para datos del doughnut chart.
- **Corregido:** Protección contra `icono` null en etiquetas de categoría.
- Ficheros modificados: `static/index.html`, `static/app.js`

### 13:45 — Fix parser Revolut: soporte cabeceras en español + .gitignore temporal/
- **Corregido:** Parser Revolut ahora soporta cabeceras en español (Tipo, Importe, Descripción...) además de inglés.
- **Corregido:** Estado `COMPLETADO` aceptado además de `COMPLETED`.
- **Añadido:** Normalización automática de cabeceras ES→EN con mapeo interno.
- **Añadido:** Carpeta `temporal/` excluida de git (.gitignore).
- Ficheros modificados: `app/parsers/revolut.py`, `.gitignore`

### 13:15 — Parsers CaixaBank y Revolut para importación CSV
- **Añadido:** `app/parsers/caixabank.py` — parser para extractos CaixaBank (CSV con `;`, formato español).
- **Añadido:** `app/parsers/revolut.py` — parser para extractos Revolut (CSV con `,`, formato inglés, filtra solo Completed).
- **Añadido:** Registrar ambos parsers en `app/rutas/importar.py`.
- **Corregido:** Opciones CaixaBank y Revolut habilitadas en el selector de banco de importación (ya no dicen "próximamente").
- Ficheros modificados: `app/parsers/caixabank.py`, `app/parsers/revolut.py`, `app/rutas/importar.py`, `static/index.html`

### 12:30 — Gestión completa de cuentas en Ajustes (editar y borrar)
- **Añadido:** Botones "Editar" y "Borrar" en cada cuenta de la lista de Ajustes.
- **Añadido:** Formulario inline de edición (nombre, banco, titular, compartida) con Guardar/Cancelar.
- **Añadido:** Confirmación antes de borrar cuenta.
- Ficheros modificados: `static/index.html`, `static/app.js`

### 02:00 — Fix definitivo 405 Method Not Allowed en todas las rutas API
- **Corregido:** POST/PUT/DELETE fallaban con 405 porque las rutas FastAPI usaban `@ruta.get("/")` generando paths como `/api/cuentas/` (con barra final), pero el JS llamaba a `/api/cuentas` (sin barra). La petición no coincidía y caía en el mount de StaticFiles (solo GET → 405).
- **Solución server-side:** Cambiar `@ruta.get("/")` → `@ruta.get("")` y `@ruta.post("/")` → `@ruta.post("")` en los 6 routers CRUD (miembros, cuentas, categorías, reglas, movimientos, mapeo_tarjetas). Así las rutas coinciden directamente sin necesidad de trailing slash.
- **Revertido** el workaround del cliente (`_url()` ya no añade `/` al final) que rompía rutas como `/api/importar/csv`.
- Ficheros modificados: `app/rutas/miembros.py`, `app/rutas/cuentas.py`, `app/rutas/categorias.py`, `app/rutas/reglas.py`, `app/rutas/movimientos.py`, `app/rutas/mapeo_tarjetas.py`, `static/api.js`

### 01:15 — Fix seed parcial: cada tabla se siembra independientemente
- **Corregido:** La función `sembrar_si_vacio()` solo comprobaba si había categorías. Si categorías se insertaban pero miembros/cuentas fallaban, nunca se reintentaba.
- **Solución:** Ahora cada sección (categorías, reglas, miembros, cuentas) comprueba su propia tabla por separado. Si una ya tiene datos y otra no, solo siembra la vacía.
- Ficheros modificados: `app/datos_iniciales.py`

### 00:08 — Fix bug importación: dropdown cuenta vacío + CSV de prueba
- **Corregido:** El desplegable "Cuenta destino" en la pestaña Importar aparecía vacío porque `<template x-for>` dentro de `<select>` con `id` estático no renderizaba las opciones.
- **Solución:** Cambiar los `<select>` de importar a `x-model` de Alpine.js (`importarCuentaId`, `importarBanco`) y añadir las variables reactivas correspondientes en `app.js`.
- **Actualizada** la función `importarCSV()` para usar `this.importarCuentaId` y `this.importarBanco` en vez de `document.getElementById`.
- **Añadido** fichero `test_santander_febrero.csv` con 54 movimientos reales de febrero 2026 para pruebas de importación.
- Ficheros modificados: `static/index.html`, `static/app.js`
- Ficheros añadidos: `test_santander_febrero.csv`

## 2026-03-09

### 23:40 — Implementar FiDo v1 completa: backend, frontend y Docker
- **Backend completo:** FastAPI + SQLite con WAL mode. 9 routers, 6 tablas, validación Pydantic.
- **Frontend SPA:** Alpine.js + Tailwind CSS (CDN) + Chart.js (CDN). 6 pestañas: Panel, Movimientos, Importar, Categorías, Reglas, Ajustes.
- **Lógica de negocio:** Categorizador automático por reglas con prioridad, deduplicador por huella SHA-256 + fuzzy matching.
- **Parser Santander:** Importación de CSV del Banco Santander (punto y coma, DD/MM/YYYY, decimales con coma).
- **API de sincronización:** Endpoints para la app Android (ping + batch de movimientos).
- **Panel/Dashboard:** Resumen con tarjetas, gráfica donut por categoría, barras de evolución mensual.
- **Datos iniciales:** 13 categorías padre con ~40 subcategorías, 27 reglas de auto-categorización, 2 miembros, 4 cuentas.
- **Docker:** Dockerfile (python:3.12-slim) + docker-compose.yml para Portainer stack.
- 32 ficheros, ~2800 líneas de código. Todo en español (variables, funciones, endpoints, columnas BD, comentarios).

## 2026-03-07

### 20:24 — Simplificar a un solo contenedor Docker
- Decisión de arquitectura: FastAPI sirve tanto la API como el frontend estático en un solo contenedor.
- Eliminada la necesidad de un servidor web separado (Nginx/Caddy).

### 19:52 — Corregir flujo Telegram
- n8n envía la respuesta directamente al usuario, sin pasar de vuelta por Node-RED.
- Simplificación del flujo de mensajería.

### 19:47 — Telegram desacoplado de FiDo
- Integración Telegram diseñada con Node-RED (polling) + n8n (parseo/respuesta) — patrón Kryptonite.
- FiDo solo expone API REST, no gestiona Telegram directamente.

### 19:33 — Diseño inicial del proyecto
- Documento de diseño completo: `finanzas-familia-resumen.md`.
- Definición de arquitectura, stack tecnológico, esquema de BD, endpoints API.
- Decisiones: SQLite, Alpine.js, sin autenticación en v1, categorías 2 niveles.

### 19:24 — Initial commit
- Repositorio creado con README.md, .gitignore, LICENSE.
