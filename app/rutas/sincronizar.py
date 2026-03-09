"""FiDo — Rutas de sincronización (para la app Android Wallet Listener)."""

from fastapi import APIRouter
from app.modelos import MovimientoCrear
from app.servicios.categorizador import categorizar
from app.servicios.deduplicador import calcular_huella, buscar_duplicados
from app import bd

ruta = APIRouter()


@ruta.get("/ping")
def ping():
    """Health check — la app Android llama aquí para saber si el servidor está disponible."""
    return {"estado": "ok", "app": "fido", "version": "1.0.0"}


@ruta.post("/movimientos")
def sincronizar_movimientos(lote: list[MovimientoCrear]):
    """Recibe un lote de movimientos desde la app Android.
    Auto-categoriza y detecta duplicados.
    """
    importados = 0
    duplicados = 0

    for mov in lote:
        # Auto-categorizar
        categoria_id = mov.categoria_id
        if not categoria_id:
            categoria_id = categorizar(mov.descripcion)

        # Huella y dedup
        huella = calcular_huella(mov.fecha, mov.importe, mov.descripcion)
        existentes = buscar_duplicados(mov.fecha, mov.importe, mov.descripcion)

        if existentes:
            duplicados += 1
            continue

        bd.ejecutar(
            """INSERT INTO movimientos
               (fecha, fecha_valor, importe, descripcion, descripcion_original,
                categoria_id, cuenta_id, origen, origen_ref, huella, notas)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mov.fecha, mov.fecha_valor, mov.importe, mov.descripcion,
             mov.descripcion_original, categoria_id, mov.cuenta_id,
             mov.origen, mov.origen_ref, huella, mov.notas)
        )
        importados += 1

    return {"importados": importados, "duplicados": duplicados}
