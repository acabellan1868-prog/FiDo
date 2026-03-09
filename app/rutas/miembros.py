"""FiDo — Rutas CRUD para miembros de la familia."""

from fastapi import APIRouter, HTTPException
from app.modelos import MiembroCrear, MiembroActualizar, MiembroRespuesta
from app import bd

ruta = APIRouter()


@ruta.get("/", response_model=list[MiembroRespuesta])
def listar_miembros():
    return bd.consultar_todos("SELECT * FROM miembros ORDER BY nombre")


@ruta.get("/{miembro_id}", response_model=MiembroRespuesta)
def obtener_miembro(miembro_id: int):
    fila = bd.consultar_uno("SELECT * FROM miembros WHERE id = ?", (miembro_id,))
    if not fila:
        raise HTTPException(404, "Miembro no encontrado")
    return fila


@ruta.post("/", response_model=MiembroRespuesta, status_code=201)
def crear_miembro(datos: MiembroCrear):
    try:
        nuevo_id = bd.ejecutar(
            "INSERT INTO miembros (nombre, telegram_chat_id) VALUES (?, ?)",
            (datos.nombre, datos.telegram_chat_id)
        )
    except Exception:
        raise HTTPException(409, f"Ya existe un miembro con nombre '{datos.nombre}'")
    return bd.consultar_uno("SELECT * FROM miembros WHERE id = ?", (nuevo_id,))


@ruta.put("/{miembro_id}", response_model=MiembroRespuesta)
def actualizar_miembro(miembro_id: int, datos: MiembroActualizar):
    existente = bd.consultar_uno("SELECT * FROM miembros WHERE id = ?", (miembro_id,))
    if not existente:
        raise HTTPException(404, "Miembro no encontrado")

    campos = []
    valores = []
    if datos.nombre is not None:
        campos.append("nombre = ?")
        valores.append(datos.nombre)
    if datos.telegram_chat_id is not None:
        campos.append("telegram_chat_id = ?")
        valores.append(datos.telegram_chat_id)

    if campos:
        valores.append(miembro_id)
        bd.ejecutar(f"UPDATE miembros SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return bd.consultar_uno("SELECT * FROM miembros WHERE id = ?", (miembro_id,))


@ruta.delete("/{miembro_id}", status_code=204)
def borrar_miembro(miembro_id: int):
    existente = bd.consultar_uno("SELECT * FROM miembros WHERE id = ?", (miembro_id,))
    if not existente:
        raise HTTPException(404, "Miembro no encontrado")
    bd.ejecutar("DELETE FROM miembros WHERE id = ?", (miembro_id,))
