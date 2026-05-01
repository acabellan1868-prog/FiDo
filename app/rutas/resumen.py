"""FiDo — Ruta de resumen para el portal hogarOS."""

from datetime import date, timedelta
from fastapi import APIRouter

from app import bd

# Nombres de meses en español
_MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
_MESES_CORTO = [
    "", "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
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
def resumen(
    periodo: str = "mes",
    cuenta_id: int | None = None,
    cuenta_nombre: str | None = None,
    banco: str | None = None,
):
    """
    Devuelve el resumen financiero del mes o semana actual para el portal hogarOS.

    - `periodo=mes` (por defecto): mes en curso.
    - `periodo=semana`: desde el lunes de la semana actual hasta hoy.

    Puede filtrarse por cuenta con `cuenta_id` o con `cuenta_nombre` y `banco`.
    """
    hoy = date.today()
    filtro_cuenta, parametros_cuenta = _crear_filtro_cuenta(cuenta_id, cuenta_nombre, banco)

    if periodo == "semana":
        lunes = hoy - timedelta(days=hoy.weekday())
        fecha_ini = lunes.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")
        etiqueta = f"Semana del {lunes.day} al {hoy.day} {_MESES_CORTO[hoy.month]}"
        filtro_fecha = "date(m.fecha) BETWEEN ? AND ?"
        parametros = [fecha_ini, fecha_fin] + parametros_cuenta
    else:
        mes_actual = hoy.strftime("%Y-%m")
        etiqueta = f"{_MESES[hoy.month]} {hoy.year}"
        filtro_fecha = "strftime('%Y-%m', m.fecha) = ?"
        parametros = [mes_actual] + parametros_cuenta

    fila = bd.consultar_uno(f"""
        SELECT
            COALESCE(SUM(CASE WHEN m.importe > 0 THEN m.importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN m.importe < 0 THEN ABS(m.importe) ELSE 0 END), 0) as gastos,
            COALESCE(SUM(m.importe), 0) as balance
        FROM movimientos m
        JOIN cuentas c ON c.id = m.cuenta_id
        WHERE {filtro_fecha}
          AND m.es_transferencia_interna = 0
          {filtro_cuenta}
    """, tuple(parametros))

    clave_periodo = "semana" if periodo == "semana" else "mes"
    return {
        clave_periodo: etiqueta,
        "ingresos": round(fila["ingresos"], 2) if fila else 0.0,
        "gastos": round(fila["gastos"], 2) if fila else 0.0,
        "balance": round(fila["balance"], 2) if fila else 0.0,
        "cuenta": cuenta_nombre if cuenta_nombre else None,
        "banco": banco if banco else None,
    }
