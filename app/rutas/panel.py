"""FiDo — Rutas del panel (dashboard): resúmenes y datos para gráficas."""

from fastapi import APIRouter, Query
from typing import Optional
from app import bd

ruta = APIRouter()


@ruta.get("/resumen")
def resumen(
    mes: Optional[str] = Query(None, description="YYYY-MM"),
    cuenta_id: Optional[int] = Query(None),
):
    """Tarjetas resumen: ingresos, gastos, balance, nº movimientos."""
    condiciones = []
    parametros = []

    if mes:
        condiciones.append("strftime('%Y-%m', fecha) = ?")
        parametros.append(mes)
    if cuenta_id:
        condiciones.append("cuenta_id = ?")
        parametros.append(cuenta_id)

    condiciones.append("es_transferencia_interna = 0")
    where = "WHERE " + " AND ".join(condiciones)

    fila = bd.consultar_uno(f"""
        SELECT
            COALESCE(SUM(CASE WHEN importe > 0 THEN importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN importe < 0 THEN importe ELSE 0 END), 0) as gastos,
            COALESCE(SUM(importe), 0) as balance,
            COUNT(*) as total_movimientos
        FROM movimientos {where}
    """, tuple(parametros))
    return fila


@ruta.get("/por-categoria")
def por_categoria(
    mes: Optional[str] = Query(None),
    cuenta_id: Optional[int] = Query(None),
):
    """Gastos agrupados por categoría padre, con desglose por subcategoría."""
    condiciones = ["m.importe < 0", "m.es_transferencia_interna = 0"]
    parametros = []

    if mes:
        condiciones.append("strftime('%Y-%m', m.fecha) = ?")
        parametros.append(mes)
    if cuenta_id:
        condiciones.append("m.cuenta_id = ?")
        parametros.append(cuenta_id)

    where = "WHERE " + " AND ".join(condiciones)

    filas = bd.consultar_todos(f"""
        SELECT
            COALESCE(p.nombre, 'Sin categoría') as categoria_padre,
            COALESCE(p.icono, '❓') as icono,
            COALESCE(h.nombre, 'Sin categoría') as subcategoria,
            SUM(ABS(m.importe)) as total
        FROM movimientos m
        LEFT JOIN categorias h ON m.categoria_id = h.id
        LEFT JOIN categorias p ON h.padre_id = p.id
        {where}
        GROUP BY p.id, h.id
        ORDER BY total DESC
    """, tuple(parametros))

    # Agrupar por padre
    resultado = {}
    for fila in filas:
        padre = fila["categoria_padre"]
        if padre not in resultado:
            resultado[padre] = {
                "nombre": padre,
                "icono": fila["icono"],
                "total": 0,
                "subcategorias": [],
            }
        resultado[padre]["total"] += fila["total"]
        resultado[padre]["subcategorias"].append({
            "nombre": fila["subcategoria"],
            "total": fila["total"],
        })

    return list(resultado.values())


@ruta.get("/por-mes")
def por_mes(
    cuenta_id: Optional[int] = Query(None),
    meses: int = Query(12, description="Número de meses hacia atrás"),
):
    """Evolución mensual: ingresos y gastos por mes."""
    condiciones = ["es_transferencia_interna = 0"]
    parametros = []

    if cuenta_id:
        condiciones.append("cuenta_id = ?")
        parametros.append(cuenta_id)

    # Filtrar últimos N meses
    condiciones.append("fecha >= date('now', ?)")
    parametros.append(f"-{meses} months")

    where = "WHERE " + " AND ".join(condiciones)

    filas = bd.consultar_todos(f"""
        SELECT
            strftime('%Y-%m', fecha) as mes,
            COALESCE(SUM(CASE WHEN importe > 0 THEN importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN importe < 0 THEN ABS(importe) ELSE 0 END), 0) as gastos
        FROM movimientos
        {where}
        GROUP BY strftime('%Y-%m', fecha)
        ORDER BY mes
    """, tuple(parametros))
    return filas


@ruta.get("/por-cuenta")
def por_cuenta(mes: Optional[str] = Query(None)):
    """Totales por cuenta bancaria."""
    condiciones = ["m.es_transferencia_interna = 0"]
    parametros = []

    if mes:
        condiciones.append("strftime('%Y-%m', m.fecha) = ?")
        parametros.append(mes)

    filtro_join = " AND " + " AND ".join(condiciones)

    filas = bd.consultar_todos(f"""
        SELECT
            c.id as cuenta_id,
            c.nombre as nombre_cuenta,
            COALESCE(SUM(CASE WHEN m.importe > 0 THEN m.importe ELSE 0 END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN m.importe < 0 THEN m.importe ELSE 0 END), 0) as gastos,
            COALESCE(SUM(m.importe), 0) as balance,
            COUNT(m.id) as total_movimientos
        FROM cuentas c
        LEFT JOIN movimientos m ON c.id = m.cuenta_id {filtro_join}
        GROUP BY c.id
        ORDER BY c.nombre
    """, tuple(parametros))
    return filas
