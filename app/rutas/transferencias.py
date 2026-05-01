"""FiDo — Rutas de transferencias internas y cuentas vinculadas."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app import bd
from app.servicios.detector_transferencias import detectar_y_marcar

ruta = APIRouter()


class VinculacionCrear(BaseModel):
    cuenta_principal_id: int
    cuenta_vinculada_id: int
    patron_principal: str
    patron_vinculada: str
    tolerancia_dias: int = 1


# ── Vinculaciones ──────────────────────────────────────────────────────────────

@ruta.get("/vinculaciones")
def listar_vinculaciones():
    """Lista las vinculaciones configuradas entre cuentas."""
    return bd.consultar_todos("""
        SELECT cv.*,
               cp.nombre AS nombre_principal,
               cv2.nombre AS nombre_vinculada
        FROM cuentas_vinculadas cv
        JOIN cuentas cp  ON cp.id  = cv.cuenta_principal_id
        JOIN cuentas cv2 ON cv2.id = cv.cuenta_vinculada_id
        ORDER BY cv.id
    """)


@ruta.post("/vinculaciones", status_code=201)
def crear_vinculacion(datos: VinculacionCrear):
    """Crea una vinculación entre dos cuentas."""
    for cuenta_id in (datos.cuenta_principal_id, datos.cuenta_vinculada_id):
        if not bd.consultar_uno("SELECT id FROM cuentas WHERE id = ?", (cuenta_id,)):
            raise HTTPException(404, f"Cuenta {cuenta_id} no encontrada")

    nuevo_id = bd.ejecutar(
        """INSERT INTO cuentas_vinculadas
           (cuenta_principal_id, cuenta_vinculada_id, patron_principal, patron_vinculada, tolerancia_dias)
           VALUES (?, ?, ?, ?, ?)""",
        (datos.cuenta_principal_id, datos.cuenta_vinculada_id,
         datos.patron_principal, datos.patron_vinculada, datos.tolerancia_dias),
    )
    return bd.consultar_uno("SELECT * FROM cuentas_vinculadas WHERE id = ?", (nuevo_id,))


@ruta.delete("/vinculaciones/{id}", status_code=204)
def eliminar_vinculacion(id: int):
    """Elimina una vinculación. No desmarca los movimientos ya marcados."""
    if not bd.consultar_uno("SELECT id FROM cuentas_vinculadas WHERE id = ?", (id,)):
        raise HTTPException(404, "Vinculación no encontrada")
    bd.ejecutar("DELETE FROM cuentas_vinculadas WHERE id = ?", (id,))


# ── Transferencias detectadas ──────────────────────────────────────────────────

@ruta.get("")
def listar_transferencias():
    """Lista los pares de movimientos marcados como transferencias internas."""
    return bd.consultar_todos("""
        SELECT
            mp.id            AS id_principal,
            mp.fecha         AS fecha,
            mp.importe       AS importe,
            mp.descripcion   AS desc_principal,
            cp.nombre        AS cuenta_principal,
            mv.id            AS id_vinculada,
            mv.descripcion   AS desc_vinculada,
            cv.nombre        AS cuenta_vinculada
        FROM movimientos mp
        JOIN cuentas cp ON cp.id = mp.cuenta_id
        JOIN movimientos mv
            ON mv.es_transferencia_interna = 1
           AND mv.importe = ABS(mp.importe)
           AND ABS(julianday(mp.fecha) - julianday(mv.fecha)) <= 1
           AND mv.cuenta_id != mp.cuenta_id
        JOIN cuentas cv ON cv.id = mv.cuenta_id
        WHERE mp.es_transferencia_interna = 1
          AND mp.importe < 0
        ORDER BY mp.fecha DESC
    """)


@ruta.post("/detectar")
def ejecutar_deteccion():
    """Lanza la detección manual de transferencias internas."""
    pares = detectar_y_marcar()
    return {"pares_marcados": pares}


@ruta.post("/{id}/marcar")
def marcar_transferencia(id: int):
    """Marca manualmente un movimiento como transferencia interna."""
    mov = bd.consultar_uno("SELECT * FROM movimientos WHERE id = ?", (id,))
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    bd.ejecutar(
        "UPDATE movimientos SET es_transferencia_interna = 1 WHERE id = ?", (id,)
    )
    return {"ok": True, "id": id}


@ruta.post("/{id}/desmarcar")
def desmarcar_transferencia(id: int):
    """Desmarca un movimiento como transferencia interna (corrección de falso positivo)."""
    mov = bd.consultar_uno("SELECT * FROM movimientos WHERE id = ?", (id,))
    if not mov:
        raise HTTPException(404, "Movimiento no encontrado")
    if not mov["es_transferencia_interna"]:
        raise HTTPException(400, "El movimiento no está marcado como transferencia interna")
    bd.ejecutar(
        "UPDATE movimientos SET es_transferencia_interna = 0 WHERE id = ?", (id,)
    )
    return {"ok": True, "id": id}
