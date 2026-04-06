# FiDo — Finanzas Domésticas

Aplicación web + app Android para gestionar las finanzas domésticas de toda la familia.

## Objetivo

Controlar los gastos e ingresos familiares con **dos prioridades claras**:

1. **Facilidad de entrada de datos** — si meter gastos es tedioso, la app se abandona.
2. **Buena categorización** — para ver dónde se va el dinero y dónde se puede ahorrar.

## Tres canales de entrada

| Canal | Tipo | Uso |
|-------|------|-----|
| **Tasker + NTFY** | Automático | Captura notificaciones bancarias en el móvil y las envía a FiDo a través de NTFY como intermediario |
| **Bot de Telegram** | Manual rápido | Gastos en efectivo y ajustes rápidos desde el móvil (previsto) |
| **Importación CSV** | Periódico | Histórico bancario (Santander, CaixaBank, Revolut) |

La **web** es para consultar, analizar, importar y corregir.

## Stack técnico

| Componente | Tecnología |
|------------|------------|
| Backend | Python + FastAPI |
| Frontend | HTML/JS (Alpine.js + Chart.js) servido por FastAPI (StaticFiles) |
| Base de datos | SQLite |
| Captura desde móvil | Tasker (app Android de automatización) + NTFY como intermediario |
| Despliegue | Docker (1 contenedor) en VM Proxmox |

## Funcionalidades principales

- Gestión de cuentas bancarias y miembros de la familia
- Captura automática de notificaciones bancarias desde el móvil vía NTFY
- Importación de CSV bancarios con deduplicación inteligente
- Categorización en dos niveles con reglas automáticas
- Dashboard con gráficas por categoría, mes, cuenta y miembro
- Edición y borrado de movimientos desde la web

## Arquitectura de captura desde el móvil

Sin app nativa, sin puertos abiertos, sin VPN permanente:

```
Notificación bancaria (en cualquier lugar, con datos móviles)
  └─ Tasker parsea el texto y extrae importe + comercio
     └─ POST a NTFY topic privado (configurado en docker-compose.yml)
        └─ FiDo escucha el topic de forma continua desde la VM
           └─ Categoriza automáticamente y guarda el movimiento
```

Ver guía de configuración de Tasker en [`docs/tasker-ntfy.md`](docs/tasker-ntfy.md).

## Estado del proyecto

En producción. Ver [`roadmap.md`](roadmap.md) para el estado de cada fase.

## Licencia

Proyecto privado de uso familiar.
