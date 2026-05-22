# Migración FiDo/Cowork al servidor Proxmox

## Contexto

FiDo es un sistema de procesamiento automático de gastos. Actualmente funciona mediante un **scheduler de Cowork** que ejecuta un prompt cada hora en un PC con Windows. El objetivo era mover esto al servidor Proxmox para no depender del PC encendido.

---

## Qué hace el scheduler actual

- **Descripción:** FiDo - Procesar gastos Drive
- **Frecuencia:** Cada hora
- **Cuenta Google Drive:** acabellan.1868@gmail.com
- **Carpeta Pendientes ID:** `1Hzd7V4N5Gwy9_0Zy3GQsudQdOiKI_Pvn`
- **Carpeta Procesadas ID:** `1qhHxIFMCogIJGjLAjy8KwKBwRaP_FgFf`
- **Cola local actual:** `C:\fido-queue\` (scripts `.ps1` que ejecuta el Task Scheduler de Windows)

### Mapeo de tarjetas → cuenta_id

| Últimos 4 dígitos | cuenta_id | Descripción |
|---|---|---|
| 9625 | 8 | Cuenta Antonio Revolut |
| 5911 | 5 | Cuenta Antonio Caixa |
| 5155 | 3 | Cuenta Común Santander |

### Mapeo por banco (sin número de tarjeta)

| Banco | cuenta_id |
|---|---|
| Revolut | 8 |
| Santander | 3 |
| CaixaBank | 5 |
| Sin info | 5 (Caixa, por defecto) |

---

## Por qué no se puede dockerizar directamente

- Cowork es una funcionalidad de la app de escritorio de Claude (Claude Code Desktop).
- Llamar a la API de Anthropic directamente tiene coste adicional, **no está incluido en la suscripción de Claude.ai**.
- Alternativas como OCR + regex se descartaron: si cambia el formato del ticket, se rompe. La IA asume esos cambios mejor.

---

## Infraestructura actual del servidor

- **Máquina:** Dell OptiPlex 7050 (Intel i5-7500 @ 3.40GHz, 4 cores)
- **Proxmox:** pve-manager 8.3, gestionado por HTTP (sin monitor físico)
- **RAM total:** 15.49 GB (2x8GB DDR4 2400MHz en DIMM1 y DIMM2)
- **RAM usada:** ~73-74% en reposo
- **Slots libres:** DIMM3 y DIMM4 vacíos
- **Disco:** 93.93 GB (54% usado)

### VMs/contenedores en marcha

| Servicio | RAM asignada | RAM usada |
|---|---|---|
| Debian12 (Docker) | 8 GB | ~7.4 GB (92%) |
| Home Assistant OS | 4 GB | ~3.7 GB (92%) |
| VM Lubuntu 22.10 | 4 GB | **apagada** |

### Contenedores Docker relevantes

`hogar-portal`, `fido`, `medido`, `kryptonite`, `redo`, `hogar-api`, `dockmon`, `planka`, `planka-db`, `n8n`, `nodered`, `tailscale`, `mcp-sqlite-server`, `nextcloud-app`, `nextcloud-db`, `portainer`

---

## Plan para cuando se amplíe RAM

### Paso 1: Ampliar RAM

- Comprar **1x16GB DDR4 2400MHz DIMM** (no SO-DIMM) e instalar en DIMM3.
- Resultado: 32GB totales, 2 slots aún libres.
- Marcas recomendadas: Crucial, Kingston, Samsung.
- **Precio actual (mayo 2026):** ~100-130€ por los aranceles. Esperar a que bajen.
- Nota: segunda mano descartada por mala experiencia previa (módulo que impedía arranque).

### Paso 2: Arrancar la VM de Lubuntu

- Ya existe la VM (ID 103 aprox.), basada en **Ubuntu 22.10 desktop (Lubuntu)**, amd64, 64GB disco.
- Está apagada. Tiene escritorio ya instalado.
- Bajarle la RAM asignada a **2GB** antes de arrancarla.
- Confirmar versión real: `cat /etc/os-release`

### Paso 3: Instalar Claude Desktop (port no oficial)

- Proyecto: [aaddrick/claude-desktop-debian](https://github.com/aaddrick/claude-desktop-debian)
- Genera un `.deb` o AppImage a partir del binario oficial de Windows.
- Compatible con Ubuntu/Debian, arquitectura amd64.
- Acceso al escritorio via consola VNC de Proxmox (desde el navegador).

### Paso 4: Configurar Cowork

- Hacer login en Claude con la cuenta de suscripción desde la consola VNC.
- Recrear el scheduler de FiDo con el mismo prompt.
- Cambiar la cola local de `C:\fido-queue\` a un volumen en el servidor (ej. `/opt/fido-queue`).
- Cambiar los scripts de `.ps1` (PowerShell) a `.sh` (bash) con `curl` en vez de `Invoke-RestMethod`.

#### Equivalente bash del script actual

```bash
#!/bin/bash
curl -s -X POST http://192.168.31.131/finanzas/api/movimientos \
  -H "Content-Type: application/json" \
  -d '{"importe": IMPORTE, "descripcion": "DESCRIPCION", "cuenta_id": CUENTA_ID, "fecha": "FECHA", "origen": "ntfy", "estado": "revisar"}'
```

### Paso 5: Cron para procesar la cola

- Crear un cron en el servidor que ejecute los `.sh` de la cola cada X minutos.
- Sustituye al Task Scheduler de Windows que actualmente los ejecuta.

---

## Estado actual

- ✅ FiDo funcionando en Windows con Cowork
- ⏸️ Migración aparcada hasta que bajen los precios de RAM
- 🟡 VM de Lubuntu disponible pero apagada, lista para cuando haya RAM suficiente
