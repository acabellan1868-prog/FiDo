# Análisis — FiDo (Finanzas Domésticas)

## Qué es

FiDo es el gestor de finanzas del ecosistema **hogarOS**. Permite importar
extractos bancarios, categorizar movimientos de forma automática o manual,
y visualizar resúmenes por cuenta, miembro y categoría.

## Por qué se hace

- Centralizar la gestión financiera familiar en una sola herramienta.
- Categorizar gastos automáticamente para ver dónde se puede ahorrar.
- Facilitar la entrada de datos: si es tedioso, la app se abandona.

## Stack

| Capa       | Tecnología                                  |
|------------|---------------------------------------------|
| Backend    | Python + FastAPI + SQLite                   |
| Frontend   | HTML/CSS/JS vanilla + Alpine.js + Chart.js  |
| Parsers    | CaixaBank, Santander, Revolut (CSV)         |
| Despliegue | Docker (puerto 8080 interno)                |
| Proxy      | Nginx de hogarOS en `/finanzas/`            |

## Documentación de diseño

El fichero `finanzas-familia-resumen.md` contiene el diseño completo original
con todas las decisiones tomadas y sus motivos.
