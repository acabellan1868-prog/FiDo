# Changelog — FiDo (Finanzas Domésticas)

Registro de todos los cambios del proyecto, ordenado de más reciente a más antiguo.

---

## 2026-03-10

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
