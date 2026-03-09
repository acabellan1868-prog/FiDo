"""FiDo — Rutas CRUD para mapeo de tarjetas (últimos 4 dígitos → cuenta)."""

from fastapi import APIRouter, HTTPException
from app.modelos import MapeoTarjetaCrear, MapeoTarjetaActualizar, MapeoTarjetaRespuesta
from app import bd

ruta = APIRouter()


@ruta.get("", response_model=list[dict])
def listar_mapeos():
    """Lista todos los mapeos con nombre de cuenta."""
    return bd.consultar_todos("""
        SELECT mt.*, c.nombre as nombre_cuenta
        FROM mapeo_tarjetas mt
        JOIN cuentas c ON mt.cuenta_id = c.id
        ORDER BY mt.ultimos4
    """)


@ruta.get("/{mapeo_id}", response_model=MapeoTarjetaRespuesta)
def obtener_mapeo(mapeo_id: int):
    fila = bd.consultar_uno("SELECT * FROM mapeo_tarjetas WHERE id = ?", (mapeo_id,))
    if not fila:
        raise HTTPException(404, "Mapeo no encontrado")
    return fila


@ruta.post("", response_model=MapeoTarjetaRespuesta, status_code=201)
def crear_mapeo(datos: MapeoTarjetaCrear):
    try:
        nuevo_id = bd.ejecutar(
            "INSERT INTO mapeo_tarjetas (ultimos4, cuenta_id, etiqueta) VALUES (?, ?, ?)",
            (datos.ultimos4, datos.cuenta_id, datos.etiqueta)
        )
    except Exception:
        raise HTTPException(409, f"Ya existe un mapeo para la tarjeta *{datos.ultimos4}")
    return bd.consultar_uno("SELECT * FROM mapeo_tarjetas WHERE id = ?", (nuevo_id,))


@ruta.put("/{mapeo_id}", response_model=MapeoTarjetaRespuesta)
def actualizar_mapeo(mapeo_id: int, datos: MapeoTarjetaActualizar):
    existente = bd.consultar_uno("SELECT * FROM mapeo_tarjetas WHERE id = ?", (mapeo_id,))
    if not existente:
        raise HTTPException(404, "Mapeo no encontrado")

    campos = []
    valores = []
    for campo, valor in [
        ("ultimos4", datos.ultimos4), ("cuenta_id", datos.cuenta_id),
        ("etiqueta", datos.etiqueta),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if campos:
        valores.append(mapeo_id)
        bd.ejecutar(f"UPDATE mapeo_tarjetas SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return bd.consultar_uno("SELECT * FROM mapeo_tarjetas WHERE id = ?", (mapeo_id,))


@ruta.delete("/{mapeo_id}", status_code=204)
def borrar_mapeo(mapeo_id: int):
    existente = bd.consultar_uno("SELECT * FROM mapeo_tarjetas WHERE id = ?", (mapeo_id,))
    if not existente:
        raise HTTPException(404, "Mapeo no encontrado")
    bd.ejecutar("DELETE FROM mapeo_tarjetas WHERE id = ?", (mapeo_id,))
