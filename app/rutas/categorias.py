"""FiDo — Rutas CRUD para categorías (árbol de 2 niveles)."""

from fastapi import APIRouter, HTTPException
from app.modelos import CategoriaCrear, CategoriaActualizar, CategoriaRespuesta, CategoriaArbol
from app import bd

ruta = APIRouter()


@ruta.get("/", response_model=list[CategoriaArbol])
def listar_categorias():
    """Devuelve el árbol completo: padres con sus hijas anidadas."""
    todas = bd.consultar_todos("SELECT * FROM categorias ORDER BY orden, nombre")

    padres = [c for c in todas if c["padre_id"] is None]
    hijas_por_padre = {}
    for c in todas:
        if c["padre_id"] is not None:
            hijas_por_padre.setdefault(c["padre_id"], []).append(c)

    resultado = []
    for padre in padres:
        resultado.append(CategoriaArbol(
            id=padre["id"],
            nombre=padre["nombre"],
            icono=padre["icono"],
            orden=padre["orden"],
            hijas=[CategoriaRespuesta(**h) for h in hijas_por_padre.get(padre["id"], [])]
        ))
    return resultado


@ruta.get("/planas", response_model=list[CategoriaRespuesta])
def listar_categorias_planas():
    """Devuelve todas las categorías sin anidar (útil para selects)."""
    return bd.consultar_todos("SELECT * FROM categorias ORDER BY orden, nombre")


@ruta.get("/{categoria_id}", response_model=CategoriaRespuesta)
def obtener_categoria(categoria_id: int):
    fila = bd.consultar_uno("SELECT * FROM categorias WHERE id = ?", (categoria_id,))
    if not fila:
        raise HTTPException(404, "Categoría no encontrada")
    return fila


@ruta.post("/", response_model=CategoriaRespuesta, status_code=201)
def crear_categoria(datos: CategoriaCrear):
    try:
        nuevo_id = bd.ejecutar(
            "INSERT INTO categorias (nombre, padre_id, icono, orden) VALUES (?, ?, ?, ?)",
            (datos.nombre, datos.padre_id, datos.icono, datos.orden)
        )
    except Exception:
        raise HTTPException(409, f"Ya existe la categoría '{datos.nombre}' en ese nivel")
    return bd.consultar_uno("SELECT * FROM categorias WHERE id = ?", (nuevo_id,))


@ruta.put("/{categoria_id}", response_model=CategoriaRespuesta)
def actualizar_categoria(categoria_id: int, datos: CategoriaActualizar):
    existente = bd.consultar_uno("SELECT * FROM categorias WHERE id = ?", (categoria_id,))
    if not existente:
        raise HTTPException(404, "Categoría no encontrada")

    campos = []
    valores = []
    for campo, valor in [
        ("nombre", datos.nombre), ("padre_id", datos.padre_id),
        ("icono", datos.icono), ("orden", datos.orden),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)

    if campos:
        valores.append(categoria_id)
        bd.ejecutar(f"UPDATE categorias SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return bd.consultar_uno("SELECT * FROM categorias WHERE id = ?", (categoria_id,))


@ruta.delete("/{categoria_id}", status_code=204)
def borrar_categoria(categoria_id: int):
    existente = bd.consultar_uno("SELECT * FROM categorias WHERE id = ?", (categoria_id,))
    if not existente:
        raise HTTPException(404, "Categoría no encontrada")
    # Borrar hijas primero si es padre
    bd.ejecutar("DELETE FROM categorias WHERE padre_id = ?", (categoria_id,))
    bd.ejecutar("DELETE FROM categorias WHERE id = ?", (categoria_id,))
