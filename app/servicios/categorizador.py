"""FiDo — Servicio de categorización automática."""

from app import bd


def categorizar(descripcion: str) -> int | None:
    """Busca en las reglas un patrón que coincida con la descripción.
    Devuelve el categoria_id de la regla con mayor prioridad, o None.
    """
    reglas = bd.consultar_todos(
        "SELECT patron, categoria_id FROM reglas ORDER BY prioridad DESC"
    )
    descripcion_lower = descripcion.lower()

    for regla in reglas:
        if regla["patron"].lower() in descripcion_lower:
            return regla["categoria_id"]

    return None
