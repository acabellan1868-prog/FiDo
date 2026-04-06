"""
FiDo — Listener de NTFY para captura automática de movimientos desde el móvil.

Flujo completo:
  1. Una app bancaria lanza una notificación en el móvil.
  2. Tasker (app Android) intercepta la notificación, extrae importe y comercio
     mediante una expresión regular (patrón de búsqueda) y publica un JSON
     en un topic privado de NTFY.
  3. Este listener, corriendo en segundo plano dentro de FiDo, está suscrito
     a ese topic mediante SSE (Server-Sent Events, flujo de eventos del servidor).
  4. Al recibir el mensaje, lo valida, busca la cuenta correspondiente,
     auto-categoriza la descripción y lo inserta como movimiento nuevo.
  5. El deduplicador (detector de duplicados) evita dobles entradas si el mensaje
     llega más de una vez.

Esto funciona con el móvil fuera de la red local: NTFY actúa de intermediario
en la nube. En cuanto FiDo tiene internet (siempre, en la VM), el mensaje llega.

────────────────────────────────────────────────────────────────
FORMATO DEL MENSAJE QUE ENVÍA TASKER (body del mensaje NTFY en JSON):
────────────────────────────────────────────────────────────────
{
    "importe": -45.50,           ← negativo = gasto, positivo = ingreso
    "descripcion": "Mercadona",  ← nombre del comercio o concepto
    "cuenta_id": 1,              ← ID de cuenta (opcional)
    "ultimos4": "1234",          ← últimos 4 dígitos de tarjeta (alternativa a cuenta_id)
    "fecha": "2026-04-06"        ← opcional, por defecto hoy
}

Si no se envía ni cuenta_id ni ultimos4, se usa NTFY_CUENTA_DEFAULT.
────────────────────────────────────────────────────────────────

Variables de entorno necesarias:
  NTFY_URL             → URL base del servidor NTFY (defecto: https://ntfy.sh)
  NTFY_TOPIC           → Nombre del topic privado (ej: fido-mov-a3f8c2d1)
                         Si está vacío, el listener se desactiva.
  NTFY_CUENTA_DEFAULT  → ID de cuenta a usar si el mensaje no especifica ninguna.
"""

import asyncio
import json
import logging
import os
from datetime import date

import httpx

from app import bd
from app.servicios.categorizador import categorizar
from app.servicios.deduplicador import calcular_huella, buscar_duplicados

logger = logging.getLogger("fido.ntfy")

NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_CUENTA_DEFAULT = os.environ.get("NTFY_CUENTA_DEFAULT", "")

# Segundos de espera entre reintentos de conexión (crece exponencialmente)
_REINTENTO_BASE = 5
_REINTENTO_MAX = 300  # máximo 5 minutos


def _resolver_cuenta(datos: dict) -> int | None:
    """Determina el cuenta_id a usar para el movimiento.

    Prioridad:
      1. cuenta_id explícito en el mensaje
      2. ultimos4 → búsqueda en la tabla mapeo_tarjetas
      3. Variable de entorno NTFY_CUENTA_DEFAULT
    """
    if "cuenta_id" in datos:
        return int(datos["cuenta_id"])

    if "ultimos4" in datos:
        mapeo = bd.consultar_uno(
            "SELECT cuenta_id FROM mapeo_tarjetas WHERE ultimos4 = ?",
            (str(datos["ultimos4"]),)
        )
        if mapeo:
            return mapeo["cuenta_id"]
        logger.warning(f"Tarjeta '{datos['ultimos4']}' no encontrada en mapeo_tarjetas.")

    if NTFY_CUENTA_DEFAULT:
        return int(NTFY_CUENTA_DEFAULT)

    return None


def procesar_mensaje(mensaje_body: str) -> dict:
    """Parsea el body de un mensaje NTFY e inserta el movimiento en la BD.

    Devuelve un dict con el resultado: {'estado': 'importado'|'duplicado', ...}
    Lanza ValueError si faltan campos obligatorios o la cuenta no se puede resolver.
    """
    datos = json.loads(mensaje_body)

    # Campos obligatorios
    if "importe" not in datos:
        raise ValueError("El mensaje no contiene el campo 'importe'.")

    importe = float(datos["importe"])
    descripcion = str(datos.get("descripcion", "Sin descripción")).strip()
    fecha = str(datos.get("fecha", date.today().isoformat()))

    cuenta_id = _resolver_cuenta(datos)
    if cuenta_id is None:
        raise ValueError(
            "No se pudo resolver la cuenta destino. "
            "Incluye 'cuenta_id', 'ultimos4' en el mensaje, "
            "o configura la variable NTFY_CUENTA_DEFAULT."
        )

    # Auto-categorización (si no viene ya en el mensaje)
    categoria_id = datos.get("categoria_id") or categorizar(descripcion)

    # Determinar si hay dudas que requieren revisión humana:
    # - Sin categoría: la descripción no coincidió con ninguna regla
    # - Cuenta resuelta por defecto: no había ultimos4 ni cuenta_id explícito
    uso_cuenta_default = "cuenta_id" not in datos and "ultimos4" not in datos
    estado = "revisar" if (not categoria_id or uso_cuenta_default) else "ok"

    # Deduplicación: evita dobles entradas
    huella = calcular_huella(fecha, importe, descripcion)
    if buscar_duplicados(fecha, importe, descripcion):
        logger.info(f"Movimiento duplicado ignorado: {descripcion} {importe}€ ({fecha})")
        return {"estado": "duplicado", "descripcion": descripcion, "importe": importe}

    bd.ejecutar(
        """INSERT INTO movimientos
           (fecha, fecha_valor, importe, descripcion, descripcion_original,
            categoria_id, cuenta_id, origen, origen_ref, huella, notas, estado)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'ntfy', ?, ?, ?, ?)""",
        (
            fecha,
            datos.get("fecha_valor"),
            importe,
            descripcion,
            datos.get("descripcion_original", descripcion),
            categoria_id,
            cuenta_id,
            datos.get("origen_ref"),
            huella,
            datos.get("notas"),
            estado,
        )
    )

    logger.info(f"Movimiento NTFY {'⚠ revisar' if estado == 'revisar' else '✓'}: {descripcion} {importe:+.2f}€ ({fecha})")
    return {"estado_proceso": "importado", "estado_revision": estado, "descripcion": descripcion, "importe": importe}


async def escuchar():
    """Tarea asyncio (asíncrona) que mantiene la suscripción al topic NTFY.

    Se conecta al endpoint de streaming SSE de NTFY y procesa cada mensaje
    entrante. Si la conexión se pierde, reintenta con espera exponencial
    (5s → 10s → 20s → ... → máx 5 min).

    Se detiene limpiamente cuando la aplicación para (CancelledError).
    """
    if not NTFY_TOPIC:
        logger.info("NTFY_TOPIC no configurado — listener de movimientos desactivado.")
        return

    # ?since=12h para recuperar mensajes recibidos mientras FiDo estuvo parado
    url = f"{NTFY_URL}/{NTFY_TOPIC}/json?since=12h"
    reintento = _REINTENTO_BASE
    logger.info(f"Listener NTFY iniciado → {NTFY_URL}/{NTFY_TOPIC}")

    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as cliente:
                async with cliente.stream("GET", url) as respuesta:
                    respuesta.raise_for_status()
                    reintento = _REINTENTO_BASE  # Resetear espera tras conexión exitosa
                    logger.info("Conexión NTFY establecida. Escuchando movimientos...")

                    async for linea in respuesta.aiter_lines():
                        if not linea:
                            continue

                        try:
                            evento = json.loads(linea)
                        except json.JSONDecodeError:
                            continue

                        # NTFY emite un evento 'open' al conectar — ignorarlo
                        if evento.get("event") != "message":
                            continue

                        mensaje_body = evento.get("message", "")
                        try:
                            resultado = procesar_mensaje(mensaje_body)
                            logger.info(f"Resultado NTFY: {resultado}")
                        except (ValueError, KeyError) as e:
                            logger.warning(f"Mensaje NTFY inválido: {e} | body: {mensaje_body!r}")
                        except Exception as e:
                            logger.error(f"Error inesperado procesando mensaje NTFY: {e}")

        except asyncio.CancelledError:
            logger.info("Listener NTFY detenido correctamente.")
            return
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP en NTFY ({e.response.status_code}). Reintentando en {reintento}s...")
        except Exception as e:
            logger.warning(f"Conexión NTFY perdida: {e}. Reintentando en {reintento}s...")

        await asyncio.sleep(reintento)
        reintento = min(reintento * 2, _REINTENTO_MAX)
