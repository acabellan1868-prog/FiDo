"""FiDo — Rutas CRUD para movimientos (gastos e ingresos)."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.modelos import MovimientoCrear, MovimientoActualizar, MovimientoRespuesta
from app import bd

ruta = APIRouter()


def _construir_filtros(
    mes: Optional[str],
    cuenta_id: Optional[int],
    categoria_id: Optional[int],
    origen: Optional[str],
    buscar: Optional[str],
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    prefijo: str = "m.",
):
    """Construye condiciones WHERE y parámetros a partir de los filtros comunes."""
    condiciones = []
    parametros = []

    if mes:
        condiciones.append(f"strftime('%Y-%m', {prefijo}fecha) = ?")
        parametros.append(mes)
    if cuenta_id:
        condiciones.append(f"{prefijo}cuenta_id = ?")
        parametros.append(cuenta_id)
    if categoria_id:
        # Si es categoría padre, incluir todas sus subcategorías
        condiciones.append(f"""({prefijo}categoria_id = ? OR {prefijo}categoria_id IN
            (SELECT id FROM categorias WHERE padre_id = ?))""")
        parametros.extend([categoria_id, categoria_id])
    if origen:
        condiciones.append(f"{prefijo}origen = ?")
        parametros.append(origen)
    if buscar:
        condiciones.append(f"{prefijo}descripcion LIKE ?")
        parametros.append(f"%{buscar}%")
    if tipo == "gasto":
        condiciones.append(f"{prefijo}importe < 0")
    elif tipo == "ingreso":
        condiciones.append(f"{prefijo}importe > 0")
    if estado:
        condiciones.append(f"{prefijo}estado = ?")
        parametros.append(estado)

    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""
    return where, parametros


@ruta.get("", response_model=list[MovimientoRespuesta])
def listar_movimientos(
    mes: Optional[str] = Query(None, description="Filtrar por mes: YYYY-MM"),
    cuenta_id: Optional[int] = Query(None),
    categoria_id: Optional[int] = Query(None),
    origen: Optional[str] = Query(None),
    buscar: Optional[str] = Query(None, description="Buscar en descripción"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: gasto | ingreso"),
    estado: Optional[str] = Query(None, description="Filtrar por estado: ok | revisar"),
    offset: int = Query(0, ge=0),
    limite: int = Query(50, ge=1, le=500),
):
    """Lista movimientos con filtros opcionales y paginación."""
    where, parametros = _construir_filtros(mes, cuenta_id, categoria_id, origen, buscar, tipo, estado, "m.")
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
    tipo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
):
    """Devuelve el total de movimientos y la suma de importes (para paginación y resumen)."""
    where, parametros = _construir_filtros(mes, cuenta_id, categoria_id, origen, buscar, tipo, estado, "")

    resultado = bd.consultar_uno(f"""
        SELECT COUNT(*) as total,
               COALESCE(SUM(importe), 0) as suma
        FROM movimientos {where}
    """, tuple(parametros))
    return {
        "total": resultado["total"] if resultado else 0,
        "suma": round(resultado["suma"], 2) if resultado else 0,
    }


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


@ruta.post("", response_model=MovimientoRespuesta, status_code=201)
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
            categoria_id, cuenta_id, origen, origen_ref, huella, notas, estado)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datos.fecha, datos.fecha_valor, datos.importe, datos.descripcion,
         datos.descripcion_original, categoria_id, datos.cuenta_id,
         datos.origen, datos.origen_ref, huella, datos.notas, datos.estado)
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
        ("notas", datos.notas), ("estado", datos.estado),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if campos:
        valores.append(movimiento_id)
        bd.ejecutar(f"UPDATE movimientos SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return obtener_movimiento(movimiento_id)


@ruta.put("/{movimiento_id}/estado")
def cambiar_estado(movimiento_id: int, nuevo_estado: str):
    """Cambia el estado de un movimiento: ok | revisar."""
    if nuevo_estado not in ("ok", "revisar"):
        raise HTTPException(400, "Estado no válido. Usa 'ok' o 'revisar'.")
    existente = bd.consultar_uno("SELECT id FROM movimientos WHERE id = ?", (movimiento_id,))
    if not existente:
        raise HTTPException(404, "Movimiento no encontrado")
    bd.ejecutar("UPDATE movimientos SET estado = ? WHERE id = ?", (nuevo_estado, movimiento_id))
    return {"id": movimiento_id, "estado": nuevo_estado}


@ruta.post("/recategorizar")
def recategorizar_sin_categoria():
    """Recategoriza todos los movimientos que no tienen categoría asignada."""
    from app.servicios.categorizador import categorizar

    sin_cat = bd.consultar_todos(
        "SELECT id, descripcion FROM movimientos WHERE categoria_id IS NULL"
    )
    actualizados = 0
    for mov in sin_cat:
        cat_id = categorizar(mov["descripcion"])
        if cat_id:
            bd.ejecutar(
                "UPDATE movimientos SET categoria_id = ? WHERE id = ?",
                (cat_id, mov["id"])
            )
            actualizados += 1

    return {"total_sin_categoria": len(sin_cat), "recategorizados": actualizados}


@ruta.delete("/{movimiento_id}", status_code=204)
def borrar_movimiento(movimiento_id: int):
    existente = bd.consultar_uno("SELECT * FROM movimientos WHERE id = ?", (movimiento_id,))
    if not existente:
        raise HTTPException(404, "Movimiento no encontrado")
    bd.ejecutar("DELETE FROM movimientos WHERE id = ?", (movimiento_id,))
