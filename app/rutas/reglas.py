"""FiDo — Rutas CRUD para reglas de categorización automática."""

from fastapi import APIRouter, HTTPException
from app.modelos import ReglaCrear, ReglaActualizar, ReglaRespuesta
from app import bd

ruta = APIRouter()


@ruta.get("/", response_model=list[dict])
def listar_reglas():
    """Lista todas las reglas con nombre de categoría padre > hija."""
    return bd.consultar_todos("""
        SELECT r.id, r.patron, r.categoria_id, r.prioridad, r.creado_en,
               h.nombre as nombre_subcategoria,
               p.nombre as nombre_categoria
        FROM reglas r
        JOIN categorias h ON r.categoria_id = h.id
        LEFT JOIN categorias p ON h.padre_id = p.id
        ORDER BY r.prioridad DESC, r.patron
    """)


@ruta.get("/{regla_id}", response_model=ReglaRespuesta)
def obtener_regla(regla_id: int):
    fila = bd.consultar_uno("SELECT * FROM reglas WHERE id = ?", (regla_id,))
    if not fila:
        raise HTTPException(404, "Regla no encontrada")
    return fila


@ruta.post("/", response_model=ReglaRespuesta, status_code=201)
def crear_regla(datos: ReglaCrear):
    nuevo_id = bd.ejecutar(
        "INSERT INTO reglas (patron, categoria_id, prioridad) VALUES (?, ?, ?)",
        (datos.patron, datos.categoria_id, datos.prioridad)
    )
    return bd.consultar_uno("SELECT * FROM reglas WHERE id = ?", (nuevo_id,))


@ruta.put("/{regla_id}", response_model=ReglaRespuesta)
def actualizar_regla(regla_id: int, datos: ReglaActualizar):
    existente = bd.consultar_uno("SELECT * FROM reglas WHERE id = ?", (regla_id,))
    if not existente:
        raise HTTPException(404, "Regla no encontrada")

    campos = []
    valores = []
    for campo, valor in [
        ("patron", datos.patron), ("categoria_id", datos.categoria_id),
        ("prioridad", datos.prioridad),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if campos:
        valores.append(regla_id)
        bd.ejecutar(f"UPDATE reglas SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return bd.consultar_uno("SELECT * FROM reglas WHERE id = ?", (regla_id,))


@ruta.delete("/{regla_id}", status_code=204)
def borrar_regla(regla_id: int):
    existente = bd.consultar_uno("SELECT * FROM reglas WHERE id = ?", (regla_id,))
    if not existente:
        raise HTTPException(404, "Regla no encontrada")
    bd.ejecutar("DELETE FROM reglas WHERE id = ?", (regla_id,))
