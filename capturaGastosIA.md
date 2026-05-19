# Captura automática de gastos con IA — FiDo

> Documentación del sistema de captura semiautomática de gastos desde notificaciones
> del móvil. Implementado en mayo de 2026.

---

## El problema

El objetivo era registrar automáticamente los gastos de tarjeta en FiDo en el
momento del pago, sin tener que introducirlos a mano ni esperar al extracto mensual.

### Enfoques descartados

| Enfoque | Motivo de descarte |
|---|---|
| **Automate + NTFY** | Android bloquea el contenido de notificaciones de apps financieras |
| **Node-RED → n8n → Tesseract OCR** | Tesseract no disponible en la instalación de n8n |
| **n8n → Claude Vision API** | Anthropic requiere créditos de pago, sin plan gratuito |
| **Drive → n8n → FiDo** | Problemas de configuración OAuth de Google Drive en n8n |
| **Bash/curl desde Cowork scheduler** | Entorno shell no disponible de forma consistente |
| **WebFetch (GET) a IP local** | WebFetch no alcanza IPs de red local |
| **JavaScript desde Chrome** | La extensión no permite acceder a IPs locales |

---

## Solución final

Flujo semiautomático en tres pasos:

```
📱 Usuario
   Hace captura de pantalla de la notificación de pago
   La sube a Google Drive (carpeta gastosPendientes)
         ↓
🤖 Cowork Scheduler (cada hora)
   Lee las imágenes nuevas de Drive
   Analiza visualmente con IA (Claude multimodal, sin API externa)
   Extrae: comercio, importe, tarjeta/banco, fecha
   Escribe un script .ps1 en C:\fido-queue\
   Copia la imagen a la carpeta procesadas
   Genera log en Drive
         ↓
⚙️ Windows Task Scheduler — tarea FiDo-Cola (cada 15 min)
   Ejecuta los .ps1 de C:\fido-queue\
   Cada .ps1 hace un POST a la API de FiDo
   Borra el .ps1 tras ejecutarlo con éxito
   Registra el resultado en C:\fido-queue\fido-cola.log
         ↓
✅ Movimiento creado en FiDo con estado "revisar"
```

---

## Componentes

### 1. Google Drive — carpetas

| Carpeta | Drive ID | Uso |
|---|---|---|
| `gastosPendientes/` | `1Hzd7V4N5Gwy9_0Zy3GQsudQdOiKI_Pvn` | El usuario sube las capturas aquí |
| `gastosPendientes/procesadas/` | `1qhHxIFMCogIJGjLAjy8KwKBwRaP_FgFf` | El scheduler copia las imágenes ya procesadas |

**Cuenta Google:** acabellan.1868@gmail.com

El scheduler compara los títulos de las imágenes en `pendientes` con los de
`procesadas` para no reprocesar la misma captura dos veces. Las imágenes no se
borran — se mueven a `procesadas` como marcador.

### 2. Cowork Scheduler — tarea

**Nombre:** FiDo — Procesar gastos Drive (tarea en Cowork UI)
**Frecuencia:** cada hora
**Carpeta conectada:** `C:\fido-queue\` (conectada en Cowork para que el sandbox pueda escribir)

#### Mapeo de tarjetas → cuenta_id

| Últimos 4 | cuenta_id | Cuenta |
|---|---|---|
| 9625 | 8 | Cuenta Antonio (Revolut) |
| 5911 | 5 | Cuenta Antonio (Caixa) |
| 5155 | 3 | Cuenta Común (Santander) |

#### Mapeo por banco (cuando no aparece número de tarjeta)

| Banco en notificación | cuenta_id | Cuenta |
|---|---|---|
| Revolut | 8 | Cuenta Antonio (Revolut) |
| Santander | 3 | Cuenta Común |
| CaixaBank | 5 | Cuenta Antonio (Caixa) |
| Sin información | 5 | Caixa (por defecto) |

> Nota: Google Wallet siempre muestra el banco. Revolut añade una segunda
> notificación con los últimos 4 dígitos. Santander solo muestra el banco,
> sin número de tarjeta.

#### Lectura de imágenes

El scheduler intenta leer la imagen con `read_file_content`. Si devuelve vacío
(ocurre con fondos oscuros), descarga el fichero con `download_file_content`,
decodifica el base64 y analiza visualmente el contenido. Claude es multimodal —
no necesita OCR externo.

#### Log en Drive

Tras cada ejecución con imágenes pendientes, crea un fichero
`fido-log-YYYY-MM-DD-HHMM.txt` en `gastosPendientes/` con:
- Fecha y hora de ejecución
- Datos extraídos de cada imagen
- Resultado: script creado o error
- Totales

Si no hay imágenes pendientes, termina silenciosamente sin crear log.

### 3. Scripts .ps1 — cola de procesamiento

El scheduler genera un fichero `.ps1` por cada gasto en `C:\fido-queue\`:

**Nombre:** `gasto-YYYYMMDD-HHMMSS.ps1`

**Contenido:**
```powershell
Invoke-RestMethod -Uri 'http://192.168.31.131/finanzas/api/movimientos' `
  -Method POST -ContentType 'application/json' `
  -Body '{"importe": -4.95, "descripcion": "GRANIER", "cuenta_id": 8, "fecha": "2026-05-16", "origen": "ntfy", "estado": "revisar"}'
```

### 4. Windows Task Scheduler — tarea FiDo-Cola

| Parámetro | Valor |
|---|---|
| Nombre | FiDo-Cola |
| Script | `C:\fido-queue\procesar.ps1` |
| Frecuencia | Cada 15 minutos |
| Usuario | OPTIPLEX3070\acabe |
| Privilegios | Máximos |

**Creación (PowerShell como administrador):**
```powershell
$accion = New-ScheduledTaskAction -Execute "PowerShell.exe" `
  -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File C:\fido-queue\procesar.ps1"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) `
  -Once -At (Get-Date)
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
  -StartWhenAvailable
Register-ScheduledTask -TaskName "FiDo-Cola" -Action $accion -Trigger $trigger `
  -Settings $settings -RunLevel Highest -Force
```

### 5. Script procesar.ps1

Ubicación: `C:\fido-queue\procesar.ps1`

Lógica:
1. Busca ficheros `gasto-*.ps1` en `C:\fido-queue\`, ordenados por nombre (= por fecha)
2. Si no hay ninguno, sale sin hacer nada
3. Para cada fichero: lo ejecuta, registra el resultado en el log y lo borra
4. Si falla, **no borra el fichero** — quedará para el siguiente ciclo de 15 min

**Log:** `C:\fido-queue\fido-cola.log`

```
2026-05-18 18:09:24 [OK]    gasto-20260518-160309.ps1 -> ID 861
2026-05-18 20:09:25 [OK]    gasto-20260518-163000.ps1 -> ID 862
2026-05-18 20:09:25 [OK]    gasto-20260518-163001.ps1 -> ID 863
```

---

## Movimientos creados en FiDo

Los movimientos llegan con:
- `origen: ntfy` (notificación de móvil)
- `estado: revisar` — el usuario los revisa y confirma en la UI de FiDo

El campo `origen` se mantiene como `ntfy` aunque el transporte haya cambiado,
porque semánticamente el dato sigue siendo una notificación de pago capturada
desde el móvil.

---

## Mantenimiento

### Añadir nueva tarjeta al mapeo
Editar el prompt del Cowork scheduler y añadir la línea correspondiente en
la sección `MAPEO TARJETAS`.

### Añadir nueva cuenta Santander (si se incorpora otro miembro)
1. Crear la cuenta en FiDo (`/api/cuentas`)
2. Actualizar el `MAPEO POR BANCO` en el prompt del scheduler

### Verificar que la tarea de Windows está activa
```powershell
Get-ScheduledTask -TaskName "FiDo-Cola" | Get-ScheduledTaskInfo | Select-Object LastRunTime, NextRunTime, LastTaskResult
```

### Ver log de procesamiento
Abrir `C:\fido-queue\fido-cola.log` con cualquier editor de texto.

### Si un .ps1 no se ejecutó (error de red, FiDo caído)
El fichero permanece en `C:\fido-queue\`. En el siguiente ciclo de 15 minutos
se reintentará automáticamente.

---

## Limitaciones conocidas

- **El Cowork scheduler requiere Claude Code abierto** para ejecutarse.
  Windows Task Scheduler funciona independientemente (solo necesita el PC encendido).
- **Máximo de delay:** una hora (scheduler) + 15 min (Windows) = 75 minutos desde
  que se sube la captura hasta que aparece en FiDo.
- **Santander sin número de tarjeta:** se asigna a Cuenta Común por defecto.
  Revisar en FiDo si el gasto corresponde a otra cuenta.
- **Imágenes con fondo oscuro:** `read_file_content` puede devolver vacío.
  El scheduler hace fallback a descarga y decodificación de base64 automáticamente.
