"""FiDo — Parser para extractos del Banco Santander.

Formatos soportados:
- Separadores: coma (,), punto y coma (;) o tabulador (\t)
- Columnas: Fecha operación, Fecha valor, Concepto/Operación, Importe [EUR], Saldo
- Fechas: DD/MM/YYYY
- Importes: punto como separador de miles, coma como decimal, sufijo EUR opcional
  Ejemplos: -13,00 EUR | 1.200,00 EUR | "-165,00" | "1.338,88"
- Los campos con comas internas van entrecomillados en el CSV de coma
- Tipos de operación:
  - Pago Movil En [comercio], [ciudad], Tarj. :*XXXXXX
  - Transaccion Contactless En [comercio], [ciudad], Tarj. :*XXXXXX
  - Compra Internet En [comercio], [ciudad], Tarj. :*XXXXXX
  - Recibo [empresa] Nº Recibo...
  - Transferencia A Favor De [destinatario] Concepto: [texto]
  - Transferencia De [remitente], Concepto [texto]
  - Bizum A Favor De / Bizum De
  - Retirada De Efectivo En Cajero...
  - Liquidacion Periodica Prestamo...
  - Devolucion Pago Movil En...
"""

import csv
import io
import re
from typing import Iterator
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase


class ParserSantander(ParserBase):
    """Parser para ficheros CSV/TSV exportados desde Santander."""

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido usando csv.reader para manejar campos entrecomillados."""
        # Detectar delimitador en la primera línea no vacía
        sep = self._detectar_separador(contenido)

        lector = csv.reader(io.StringIO(contenido), delimiter=sep)

        for campos in lector:
            if len(campos) < 4:
                continue
            # Saltar líneas de cabecera
            if any(cab in campos[0].lower() for cab in ["fecha", "date", "operación", "operacion"]):
                continue

            try:
                fecha_op = self._parsear_fecha(campos[0].strip())
                if len(campos) >= 5:
                    fecha_valor = self._parsear_fecha(campos[1].strip())
                    descripcion = campos[2].strip()
                    importe_raw = campos[3].strip()
                else:
                    fecha_valor = fecha_op
                    descripcion = campos[1].strip()
                    importe_raw = campos[2].strip()

                importe = self._parsear_importe(importe_raw)

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

    def _detectar_separador(self, contenido: str) -> str:
        """Detecta el separador de campos en la primera línea no vacía."""
        for linea in contenido.splitlines():
            if linea.strip():
                if "\t" in linea:
                    return "\t"
                if ";" in linea:
                    return ";"
                return ","
        return ","

    def _parsear_fecha(self, texto: str) -> str:
        """Convierte DD/MM/YYYY a YYYY-MM-DD."""
        texto = texto.strip().strip('"')
        partes = texto.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        # Intentar formato YYYY-MM-DD directamente
        if re.match(r"\d{4}-\d{2}-\d{2}", texto):
            return texto
        raise ValueError(f"Formato de fecha no reconocido: {texto}")

    def _parsear_importe(self, texto: str) -> float:
        """Convierte '1.234,56 EUR' o '-45,30 EUR' o '-45,30' a float."""
        limpio = texto.strip().strip('"')
        limpio = limpio.replace("EUR", "").replace("€", "").strip()
        # Quitar separador de miles (punto) y cambiar coma decimal a punto
        limpio = limpio.replace(".", "").replace(",", ".")
        return float(limpio)

    def _limpiar_descripcion(self, texto: str) -> str:
        """Limpia la descripción: quita espacios extra y normaliza."""
        texto = texto.strip().strip('"')
        # Quitar saltos de línea internos (a veces el CSV tiene campos multilínea)
        texto = " ".join(texto.split())
        return texto
