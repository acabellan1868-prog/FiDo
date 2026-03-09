"""FiDo — Servicio de deduplicación de movimientos."""

import hashlib
from app import bd


def calcular_huella(fecha: str, importe: float, descripcion: str) -> str:
    """Genera una huella SHA-256 truncada a partir de fecha + importe + descripción."""
    descripcion_normalizada = descripcion.lower().strip()
    cadena = f"{fecha}|{importe:.2f}|{descripcion_normalizada}"
    return hashlib.sha256(cadena.encode()).hexdigest()[:16]


def buscar_duplicados(fecha: str, importe: float, descripcion: str) -> list[dict]:
    """Busca movimientos duplicados: primero por huella exacta, luego fuzzy (±1 día, mismo importe)."""
    huella = calcular_huella(fecha, importe, descripcion)

    # Coincidencia exacta por huella
    exactos = bd.consultar_todos(
        "SELECT * FROM movimientos WHERE huella = ?",
        (huella,)
    )
    if exactos:
        return exactos

    # Coincidencia fuzzy: mismo importe, fecha ±1 día
    fuzzy = bd.consultar_todos(
        """SELECT * FROM movimientos
           WHERE importe = ?
           AND fecha BETWEEN date(?, '-1 day') AND date(?, '+1 day')""",
        (importe, fecha, fecha)
    )
    return fuzzy
