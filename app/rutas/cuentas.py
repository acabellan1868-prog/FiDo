"""FiDo — Rutas CRUD para cuentas bancarias."""

from fastapi import APIRouter, HTTPException
from app.modelos import CuentaCrear, CuentaActualizar, CuentaRespuesta
from app import bd

ruta = APIRouter()


@ruta.get("/", response_model=list[CuentaRespuesta])
def listar_cuentas():
    return bd.consultar_todos("SELECT * FROM cuentas ORDER BY nombre")


@ruta.get("/{cuenta_id}", response_model=CuentaRespuesta)
def obtener_cuenta(cuenta_id: int):
    fila = bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
    if not fila:
        raise HTTPException(404, "Cuenta no encontrada")
    return fila


@ruta.post("/", response_model=CuentaRespuesta, status_code=201)
def crear_cuenta(datos: CuentaCrear):
    nuevo_id = bd.ejecutar(
        """INSERT INTO cuentas (nombre, banco, iban, miembro_id, es_compartida)
           VALUES (?, ?, ?, ?, ?)""",
        (datos.nombre, datos.banco, datos.iban, datos.miembro_id, int(datos.es_compartida))
    )
    return bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (nuevo_id,))


@ruta.put("/{cuenta_id}", response_model=CuentaRespuesta)
def actualizar_cuenta(cuenta_id: int, datos: CuentaActualizar):
    existente = bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
    if not existente:
        raise HTTPException(404, "Cuenta no encontrada")

    campos = []
    valores = []
    for campo, valor in [
        ("nombre", datos.nombre), ("banco", datos.banco), ("iban", datos.iban),
        ("miembro_id", datos.miembro_id),
    ]:
        if valor is not None:
            campos.append(f"{campo} = ?")
            valores.append(valor)
    if datos.es_compartida is not None:
        campos.append("es_compartida = ?")
        valores.append(int(datos.es_compartida))

    if campos:
        valores.append(cuenta_id)
        bd.ejecutar(f"UPDATE cuentas SET {', '.join(campos)} WHERE id = ?", tuple(valores))

    return bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))


@ruta.delete("/{cuenta_id}", status_code=204)
def borrar_cuenta(cuenta_id: int):
    existente = bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
    if not existente:
        raise HTTPException(404, "Cuenta no encontrada")
    bd.ejecutar("DELETE FROM cuentas WHERE id = ?", (cuenta_id,))
