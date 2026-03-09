"""FiDo — Rutas CRUD para movimientos (gastos e ingresos)."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.modelos import MovimientoCrear, MovimientoActualizar, MovimientoRespuesta
from app import bd

ruta = APIRouter()


@ruta.get("/", response_model=list[MovimientoRespuesta])
def listar_movimientos(
    mes: Optional[str] = Query(None, description="Filtrar por mes: YYYY-MM"),
    cuenta_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    origen: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None, description="Buscar en descripción"),
    offset: int = Query(0, ge=0),
    limite: int = Query(50, ge=1, le=500),
):
    """Lista movimientos con filtros opcionales y paginación."""
    condiciones = []
    parametros = []

    if mes:
        condiciones.append("strftime('%Y-%m', m.fecha) = ?")
        parametros.append(mes)
    if cuenta_id:
        condiciones.append("m.cuenta_id = ?")
        parametros.append(cuenta_id)
    if categoria_id:
        condiciones.append("m.categoria_id = ?")
        parametros.append(categoria_id)
    if origen:
        condiciones.append("m.origen = ?")
        parametros.append(origen)
    if buscar:
        condiciones.append("m.descripcion LIKE ?")
        parametros.append(f"%{buscar}%")

    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    parametros.extend([limite, offset])

    filas = bd.consultar_todos(f"""
        SELECT m.*,
               COALESCE(h.nombre, '') as nombre_categoria,
               c.nombre as nombre_cuenta
        FROM movimientos m
        LEFT JOIN categorias h ON m.categoria_id = h.id
        LEFT JOIN cuentas c ON m.cuenta_id = c.id
        {where}
        ORDER BY m.fecha DESC, m.id DESC
        LIMIT ? OFFSET ?
    """, tuple(parametros))
    return filas


@ruta.get("/total")
def contar_movimientos(
    mes: Optional[str] = Query(None),
    cuenta_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    origen: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None),
):
    """Devuelve el total de movimientos (para paginación)."""
    condiciones = []
    parametros = []

    if mes:
        condiciones.append("strftime('%Y-%m', fecha) = ?")
        parametros.append(mes)
    if cuenta_id:
        condiciones.append("cuenta_id = ?")
        parametros.append(cuenta_id)
    if categoria_id:
        condiciones.append("categoria_id = ?")
        parametros.append(categoria_id)
    if origen:
        condiciones.append("origen = ?")
        parametros.append(origen)
    if buscar:
        condiciones.append("descripcion LIKE ?")
        parametros.append(f"%{buscar}%")

    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    resultado = bd.consultar_uno(f"SELECT COUNT(*) as total FROM movimientos {where}", tuple(parametros))
    return {"total": resultado["total"] if resultado else 0}


@ruta.get("/{movimiento_id}", response_model=MovimientoRespuesta)
def obtener_movimiento(movimiento_id: int):
    fila = bd.consultar_uno("""
        SELECT m.*,
               COALESCE(h.nombre, '') as nombre_categoria,
               c.nombre as nombre_cuenta
        FROM movimientos m
        LEFT JOIN categorias h ON m.categoria_id = h.id
        LEFT JOIN cuentas c ON m.cuenta_id = c.id
        WHERE m.id = ?
    """, (movimiento_id,))
    if not fila:
        raise HTTPException(404, "Movimiento no encontrado")
    return fila


@ruta.post("/", response_model=MovimientoRespuesta, status_code=201)
def crear_movimiento(datos: MovimientoCrear):
    # Auto-categorizar si no viene categoría
    categoria_id = datos.categoria_id
    if not categoria_id:
        from app.servicios.categorizador import categorizar
        categoria_id = categorizar(datos.descripcion)

    # Calcular huella para deduplicación
    from app.servicios.deduplicador import calcular_huella
    huella = calcular_huella(datos.fecha, datos.importe, datos.descripcion)

    nuevo_id = bd.ejecutar(
        """INSERT INTO movimientos
           (fecha, fecha_valor, importe, descripcion, descripcion_original,
            categoria_id, cuenta_id, origen, origen_ref, huella, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datos.fecha, datos.fecha_valor, datos.importe, datos.descripcion,
         datos.descripcion_original, categoria_id, datos.cuenta_id,
         datos.origen, datos.origen_ref, huella, datos.notas)
    )
    return obtener_movimiento(nuevo_id)


@ruta.put("/{movimiento_id}", response_model=MovimientoRespuesta)
def actualizar_movimiento(movimiento_id: int, datos: MovimientoActualizar):
    existente = bd.consultar_uno("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,))
    if not existente:
        raise HTTPException(404, "Movimiento no encontrado")

    campos = []
    valores = []
    for campo, valor in [
        ("fecha", datos.fecha), ("fecha_valor", datos.fecha_valor),
        ("importe", datos.importe), ("descripcion", datos.descripcion),
        ("categoria_id", datos.categoria_id), ("cuenta_id", datos.cuenta_id),
        ("notas", datos.notas),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if campos:
        valores.append(movimiento_id)
        bd.ejecutar(f"UPDATE movimientos SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return obtener_movimiento(movimiento_id)


@ruta.delete("/{movimiento_id}", status_code=204)
def borrar_movimiento(movimiento_id: int):
    existente = bd.consultar_uno("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,))
    if not existente:
        raise HTTPException(404, "Movimiento no encontrado")
    bd.ejecutar("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
