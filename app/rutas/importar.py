"""FiDo — Ruta de importación de extractos bancarios (CSV/TSV/XLS/XLSX)."""

import csv
import io
import sqlite3
from datetime import date, datetime

import openpyxl
import xlrd
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

# Revolut exige importes con punto decimal (float() directo);
# Santander y CaixaBank esperan formato español (coma decimal).
_BANCOS_DECIMAL_PUNTO = {"revolut"}


def _formatear_numero(valor: float, decimal_punto: bool) -> str:
    texto = f"{valor:.2f}"
    return texto if decimal_punto else texto.replace(".", ",")


def _celda_a_texto(valor, decimal_punto: bool) -> str:
    """Convierte el valor de una celda de openpyxl (.xlsx) al texto que espera un parser CSV."""
    if valor is None:
        return ""
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    if isinstance(valor, float):
        return _formatear_numero(valor, decimal_punto)
    return str(valor).strip()


def _xlsx_a_csv(contenido_bytes: bytes, banco: str) -> str:
    """Convierte la primera hoja de un Excel (.xlsx) a texto CSV separado por comas."""
    libro = openpyxl.load_workbook(io.BytesIO(contenido_bytes), data_only=True, read_only=True)
    hoja = libro.active
    decimal_punto = banco in _BANCOS_DECIMAL_PUNTO

    salida = io.StringIO()
    escritor = csv.writer(salida)
    for fila in hoja.iter_rows(values_only=True):
        if fila is None or all(c is None for c in fila):
            continue
        escritor.writerow([_celda_a_texto(c, decimal_punto) for c in fila])
    return salida.getvalue()


def _xls_a_csv(contenido_bytes: bytes, banco: str) -> str:
    """Convierte la primera hoja de un Excel antiguo (.xls) a texto CSV separado por comas."""
    libro = xlrd.open_workbook(file_contents=contenido_bytes)
    hoja = libro.sheet_by_index(0)
    decimal_punto = banco in _BANCOS_DECIMAL_PUNTO

    salida = io.StringIO()
    escritor = csv.writer(salida)
    for i in range(hoja.nrows):
        fila = hoja.row(i)
        if all(c.ctype == xlrd.XL_CELL_EMPTY for c in fila):
            continue

        valores = []
        for c in fila:
            if c.ctype == xlrd.XL_CELL_EMPTY:
                valores.append("")
            elif c.ctype == xlrd.XL_CELL_DATE:
                dt = xlrd.xldate_as_datetime(c.value, libro.datemode)
                valores.append(dt.strftime("%Y-%m-%d"))
            elif c.ctype == xlrd.XL_CELL_NUMBER:
                valores.append(_formatear_numero(c.value, decimal_punto))
            else:
                valores.append(str(c.value).strip())
        escritor.writerow(valores)
    return salida.getvalue()


@ruta.post("/csv")
async def importar_csv(
    fichero: UploadFile = File(...),
    cuenta_id: int = Form(...),
    banco: str = Form("santander"),
):
    """Importa un fichero CSV/TSV o Excel (.xls/.xlsx) de extracto bancario.
    Auto-categoriza y detecta duplicados.
    """
    banco = banco.lower()
    parser = PARSERS.get(banco)
    if not parser:
        raise HTTPException(400, f"Banco no soportado: {banco}. Disponibles: {list(PARSERS.keys())}")

    # Verificar que la cuenta existe
    cuenta = bd.consultar_uno("SELECT * FROM cuentas WHERE id = ?", (cuenta_id,))
    if not cuenta:
        raise HTTPException(404, f"Cuenta con id {cuenta_id} no encontrada")

    # Leer contenido del fichero
    contenido_bytes = await fichero.read()
    nombre = (fichero.filename or "").lower()

    if nombre.endswith(".xlsx"):
        try:
            contenido = _xlsx_a_csv(contenido_bytes, banco)
        except Exception as e:
            raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    elif nombre.endswith(".xls"):
        try:
            contenido = _xls_a_csv(contenido_bytes, banco)
        except Exception as e:
            raise HTTPException(400, f"No se pudo leer el Excel: {e}")
    else:
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

        except sqlite3.IntegrityError:
            # El chequeo de huella exacta de arriba puede perder una carrera
            # (o la huella con sufijo _N puede coincidir con una ya existente
            # de una importación anterior del mismo fichero). El índice único
            # es quien lo bloquea aquí.
            duplicados += 1
            detalles.append({
                "estado": "duplicado",
                "descripcion": movimiento.descripcion,
                "fecha": movimiento.fecha,
                "importe": movimiento.importe,
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
