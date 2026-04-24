"""FiDo — Parser para extractos de CaixaBank.

Diseño flexible basado en cabeceras:
- Detecta el delimitador automáticamente (coma, punto y coma, tabulador)
- Localiza las columnas por nombre, no por posición
- Funciona con cualquier número de columnas y orden arbitrario
- Compatible con exportaciones directas del banco o convertidas desde Excel

Columnas que reconoce (insensible a mayúsculas/acentos):
  fecha        → "Fecha", "Fecha operación", "Date"...
  fecha_valor  → "Fecha valor", "Valor"...
  descripcion  → "Movimiento", "Descripción", "Concepto"...
  mas_datos    → "Más datos", "Observaciones"... (opcional, se añade a descripción)
  importe      → "Importe", "Amount"...
"""

import csv
import io
import re
from typing import Iterator, Optional
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase


# Palabras clave para identificar cada columna (minúsculas, sin acentos)
_CLAVES_FECHA        = ["fecha", "date", "f.operacion", "f.valor"]
_CLAVES_FECHA_VALOR  = ["fecha valor", "valor", "value"]
_CLAVES_DESCRIPCION  = ["movimiento", "descripcion", "concepto", "description", "detalle"]
_CLAVES_MAS_DATOS    = ["mas datos", "observaciones", "info", "detalles"]
_CLAVES_IMPORTE      = ["importe", "amount", "cantidad", "importe eur"]


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos para comparación flexible."""
    return (texto.lower()
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ü", "u")
            .strip())


def _detectar_delimitador(primera_linea: str) -> str:
    """Detecta el delimitador más probable."""
    for sep in [";", ",", "\t"]:
        if primera_linea.count(sep) >= 2:
            return sep
    return ","


def _buscar_columna(cabeceras: list[str], claves: list[str]) -> Optional[int]:
    """Devuelve el índice de la primera cabecera que coincide con alguna clave."""
    for i, cab in enumerate(cabeceras):
        cab_norm = _normalizar(cab)
        for clave in claves:
            if clave in cab_norm:
                return i
    return None


class ParserCaixaBank(ParserBase):
    """Parser flexible para ficheros CSV de CaixaBank."""

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        lineas = contenido.strip().splitlines()
        if not lineas:
            return

        # Detectar delimitador a partir de la primera línea no vacía
        primera = next((l for l in lineas if l.strip()), "")
        sep = _detectar_delimitador(primera)

        lector = csv.reader(io.StringIO(contenido.strip()), delimiter=sep)
        filas = list(lector)
        if not filas:
            return

        # Buscar la fila de cabeceras (primera con suficientes columnas)
        idx_cab = None
        cabeceras = []
        for i, fila in enumerate(filas):
            if len(fila) >= 3:
                norm = [_normalizar(c) for c in fila]
                if any("fecha" in n or "date" in n for n in norm):
                    idx_cab = i
                    cabeceras = fila
                    break

        if idx_cab is None:
            return

        # Mapear columnas por nombre
        col_fecha       = _buscar_columna(cabeceras, _CLAVES_FECHA)
        col_fecha_valor = _buscar_columna(cabeceras, _CLAVES_FECHA_VALOR)
        col_desc        = _buscar_columna(cabeceras, _CLAVES_DESCRIPCION)
        col_mas_datos   = _buscar_columna(cabeceras, _CLAVES_MAS_DATOS)
        col_importe     = _buscar_columna(cabeceras, _CLAVES_IMPORTE)

        # Fecha y importe son imprescindibles
        if col_fecha is None or col_importe is None:
            return

        # Si no hay columna de descripción, usar la primera columna que no sea fecha
        if col_desc is None:
            col_desc = next(
                (i for i in range(len(cabeceras))
                 if i not in [col_fecha, col_fecha_valor, col_importe]),
                None
            )

        # Procesar filas de datos
        for fila in filas[idx_cab + 1:]:
            if not fila or all(c.strip() == "" for c in fila):
                continue

            try:
                fecha_op = self._parsear_fecha(fila[col_fecha])

                fecha_valor = (self._parsear_fecha(fila[col_fecha_valor])
                               if col_fecha_valor is not None and col_fecha_valor < len(fila)
                               else fecha_op)

                descripcion = fila[col_desc].strip() if col_desc is not None and col_desc < len(fila) else ""
                if col_mas_datos is not None and col_mas_datos < len(fila):
                    extra = fila[col_mas_datos].strip()
                    if extra:
                        descripcion = f"{descripcion} - {extra}"

                importe = self._parsear_importe(fila[col_importe])

                yield MovimientoCrear(
                    fecha=fecha_op,
                    fecha_valor=fecha_valor,
                    importe=importe,
                    descripcion=self._limpiar_descripcion(descripcion),
                    descripcion_original=descripcion,
                    cuenta_id=cuenta_id,
                    origen="csv",
                )
            except (ValueError, IndexError):
                continue

    def _parsear_fecha(self, texto: str) -> str:
        texto = texto.strip().strip('"')
        partes = texto.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        if re.match(r"\d{4}-\d{2}-\d{2}", texto):
            return texto
        raise ValueError(f"Formato de fecha no reconocido: {texto}")

    def _parsear_importe(self, texto: str) -> float:
        limpio = texto.strip().strip('"').replace("EUR", "").replace("€", "").strip()
        if "," in limpio:
            # Formato español: punto = miles, coma = decimal (ej. -1.200,50)
            limpio = limpio.replace(".", "").replace(",", ".")
        # Sin coma: punto ya es el separador decimal (ej. -173.68)
        return float(limpio)

    def _limpiar_descripcion(self, texto: str) -> str:
        return " ".join(texto.strip().strip('"').split())
