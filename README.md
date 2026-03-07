# FiDo — Finanzas Domésticas

Aplicación web + app Android para gestionar las finanzas domésticas de toda la familia.

## Objetivo

Controlar los gastos e ingresos familiares con **dos prioridades claras**:

1. **Facilidad de entrada de datos** — si meter gastos es tedioso, la app se abandona.
2. **Buena categorización** — para ver dónde se va el dinero y dónde se puede ahorrar.

## Tres canales de entrada

| Canal | Tipo | Uso |
|-------|------|-----|
| **Wallet Listener** (App Android) | Automático | Captura pagos con tarjeta desde las notificaciones de Google Wallet |
| **Bot de Telegram** | Manual rápido | Gastos en efectivo y ajustes rápidos desde el móvil |
| **Importación CSV** | Periódico | Histórico bancario (Santander, CaixaBank, Revolut) |

La **web** es para consultar, analizar, importar y corregir.

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Backend | Python + FastAPI |
| Frontend | HTML/JS (Alpine.js + Chart.js) servido por FastAPI (StaticFiles) |
| Base de datos | SQLite |
| App Android | Kotlin (NotificationListenerService + Room + WorkManager) |
| Integración Telegram | Node-RED (polling) + n8n (parseo y respuesta) — externa a FiDo |
| Despliegue | Docker (1 contenedor) en servidor Debian con Proxmox |
| Acceso remoto | Tailscale (VPN privada) |

## Funcionalidades principales

- Gestión de cuentas bancarias y miembros de la familia
- Captura automática de pagos con tarjeta (Google Wallet)
- Bot de Telegram para entrada rápida de gastos
- Importación de CSV bancarios con deduplicación inteligente
- Categorización en dos niveles con reglas automáticas
- Dashboard con gráficas por categoría, mes, cuenta y miembro
- Edición y borrado de movimientos desde la web

## Arquitectura de sync (App Android)

La app Android guarda los gastos en local y sincroniza con el servidor cuando detecta conectividad:

```
¿Ping al servidor FiDo? (WiFi de casa o Tailscale)
  └─ SÍ → Vuelca todos los gastos pendientes al API
  └─ NO → Se queda en local, reintenta con el siguiente cambio de red
```

Sin puertos abiertos. Sin VPN permanente. Los gastos nunca se pierden.

## Estado del proyecto

En fase de diseño. El documento de diseño completo está en [`finanzas-familia-resumen.md`](finanzas-familia-resumen.md).

## Licencia

Proyecto privado de uso familiar.
