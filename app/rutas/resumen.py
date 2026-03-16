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


@ruta.get("")
def resumen():
    """
    Devuelve el resumen financiero del mes actual para el portal hogarOS.

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

    fila = bd.consultar_uno("""
        SELECT
            COALESCE(SUM(CASE WHEN importe > 0 THEN importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN importe < 0 THEN ABS(importe) ELSE 0 END), 0) as gastos,
            COALESCE(SUM(importe), 0) as balance
        FROM movimientos
        WHERE strftime('%Y-%m', fecha) = ?
    """, (mes_actual,))

    return {
        "mes": nombre_mes,
        "ingresos": round(fila["ingresos"], 2) if fila else 0.0,
        "gastos": round(fila["gastos"], 2) if fila else 0.0,
        "balance": round(fila["balance"], 2) if fila else 0.0,
    }
