"""FiDo — Ruta de importación de extractos bancarios (CSV/TSV)."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.parsers.santander import ParserSantander
from app.parsers.caixabank import ParserCaixaBank
from app.parsers.revolut import ParserRevolut
from app.servicios.categorizador import categorizar
from app.servicios.deduplicador import calcular_huella, buscar_duplicados
from app.servicios.detector_transferencias import detectar_y_marcar
from app import bd

ruta = APIRouter()

PARSERS = {
    "santander": ParserSantander(),
    "caixabank": ParserCaixaBank(),
    "revolut": ParserRevolut(),
}


@ruta.post("/csv")
async def importar_csv(
    fichero: UploadFile = File(...),
    cuenta_id: int = Form(...),
    banco: str = Form("santander"),
):
    """Importa un fichero CSV/TSV de extracto bancario.
    Auto-categoriza y detecta duplicados.
    """
    parser = PARSERS.get(banco.lower())
    if not parser:
        raise HTTPException(400, f"Banco no soportado: {banco}. Disponibles: {list(PARSERS.keys())}")

    # Verificar que la cuenta existe
    cuenta = bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
    if not cuenta:
        raise HTTPException(404, f"Cuenta con id {cuenta_id} no encontrada")

    # Leer contenido del fichero
    contenido_bytes = await fichero.read()
    # Intentar UTF-8, fallback a ISO-8859-1 (común en bancos españoles)
    try:
        contenido = contenido_bytes.decode("utf-8")
    except UnicodeDecodeError:
        contenido = contenido_bytes.decode("iso-8859-1")

    importados = 0
    duplicados = 0
    errores = 0
    detalles = []

    # Contador de huellas dentro del lote actual:
    # si hay dos movimientos idénticos (mismo día, importe y descripción)
    # se distinguen añadiendo el índice de ocurrencia (_0, _1, ...)
    # para evitar que el segundo sea detectado como duplicado del primero.
    contador_huellas: dict[str, int] = {}

    for movimiento in parser.parsear(contenido, cuenta_id):
        try:
            # Auto-categorizar si no tiene categoría
            categoria_id = movimiento.categoria_id
            if not categoria_id:
                categoria_id = categorizar(movimiento.descripcion)

            # Calcular huella base y ajustar según ocurrencias en el lote
            huella_base = calcular_huella(movimiento.fecha, movimiento.importe, movimiento.descripcion)
            ocurrencia  = contador_huellas.get(huella_base, 0)
            huella      = huella_base if ocurrencia == 0 else f"{huella_base}_{ocurrencia}"
            contador_huellas[huella_base] = ocurrencia + 1

            # Buscar duplicados: primero por huella exacta, luego fuzzy
            existentes = bd.consultar_todos(
                "SELECT * FROM movimientos WHERE huella = ?", (huella,)
            )
            if not existentes:
                # Fallback: mismo importe, misma cuenta y fecha ±1 día
                existentes = bd.consultar_todos(
                    """SELECT * FROM movimientos
                       WHERE importe = ? AND cuenta_id = ?
                       AND fecha BETWEEN date(?, '-1 day') AND date(?, '+1 day')""",
                    (movimiento.importe, movimiento.cuenta_id,
                     movimiento.fecha, movimiento.fecha)
                )
            if existentes:
                duplicados += 1
                detalles.append({
                    "estado": "duplicado",
                    "descripcion": movimiento.descripcion,
                    "fecha": movimiento.fecha,
                    "importe": movimiento.importe,
                })
                continue

            # Insertar
            bd.ejecutar(
                """INSERT INTO movimientos
                   (fecha, fecha_valor, importe, descripcion, descripcion_original,
                    categoria_id, cuenta_id, origen, huella)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (movimiento.fecha, movimiento.fecha_valor, movimiento.importe,
                 movimiento.descripcion, movimiento.descripcion_original,
                 categoria_id, movimiento.cuenta_id, "csv", huella)
            )
            importados += 1
            detalles.append({
                "estado": "importado",
                "descripcion": movimiento.descripcion,
                "fecha": movimiento.fecha,
                "importe": movimiento.importe,
                "categoria_id": categoria_id,
            })

        except Exception as e:
            errores += 1
            detalles.append({
                "estado": "error",
                "descripcion": getattr(movimiento, "descripcion", ""),
                "error": str(e),
            })

    transferencias_marcadas = detectar_y_marcar()

    return {
        "importados": importados,
        "duplicados": duplicados,
        "errores": errores,
        "transferencias_marcadas": transferencias_marcadas,
        "detalles": detalles,
    }
