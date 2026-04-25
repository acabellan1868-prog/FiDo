"""FiDo — Ruta de resumen para el portal hogarOS."""

from datetime import date
from fastapi import APIRouter

from app import bd

# Nombres de meses en español
_MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

ruta = APIRouter()


def _crear_filtro_cuenta(cuenta_id: int | None, cuenta_nombre: str | None, banco: str | None) -> tuple[str, list]:
    """Crea el JOIN y filtros SQL opcionales para limitar el resumen a una cuenta."""
    filtros = []
    parametros = []

    if cuenta_id is not None:
        filtros.append("m.cuenta_id = ?")
        parametros.append(cuenta_id)
    else:
        if cuenta_nombre:
            filtros.append("LOWER(c.nombre) LIKE LOWER(?)")
            parametros.append(f"%{cuenta_nombre}%")
        if banco:
            filtros.append("LOWER(COALESCE(c.banco, '')) LIKE LOWER(?)")
            parametros.append(f"%{banco}%")

    if not filtros:
        return "", []

    return " AND " + " AND ".join(filtros), parametros


@ruta.get("")
def resumen(cuenta_id: int | None = None, cuenta_nombre: str | None = None, banco: str | None = None):
    """
    Devuelve el resumen financiero del mes actual para el portal hogarOS.

    Puede filtrarse por cuenta con `cuenta_id` o con `cuenta_nombre` y `banco`.

    Formato esperado por el portal:
    {
        "mes": "Marzo 2026",
        "ingresos": 2100.00,
        "gastos": 1258.50,
        "balance": 841.50
    }
    """
    hoy = date.today()
    mes_actual = hoy.strftime("%Y-%m")
    nombre_mes = f"{_MESES[hoy.month]} {hoy.year}"

    filtro_cuenta, parametros_cuenta = _crear_filtro_cuenta(cuenta_id, cuenta_nombre, banco)
    parametros = [mes_actual] + parametros_cuenta

    fila = bd.consultar_uno(f"""
        SELECT
            COALESCE(SUM(CASE WHEN m.importe > 0 THEN m.importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN m.importe < 0 THEN ABS(m.importe) ELSE 0 END), 0) as gastos,
            COALESCE(SUM(m.importe), 0) as balance
        FROM movimientos m
        JOIN cuentas c ON c.id = m.cuenta_id
        WHERE strftime('%Y-%m', m.fecha) = ?{filtro_cuenta}
    """, tuple(parametros))

    return {
        "mes": nombre_mes,
        "ingresos": round(fila["ingresos"], 2) if fila else 0.0,
        "gastos": round(fila["gastos"], 2) if fila else 0.0,
        "balance": round(fila["balance"], 2) if fila else 0.0,
        "cuenta": cuenta_nombre if cuenta_nombre else None,
        "banco": banco if banco else None,
    }
