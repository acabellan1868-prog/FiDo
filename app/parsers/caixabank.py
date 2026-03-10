"""FiDo — Parser para extractos de CaixaBank.

Formato detectado del extracto real (XLS → CSV convertido):
- Columnas: Fecha;Fecha valor;Descripción;Importe
- Fechas: DD/MM/YYYY
- Importes: formato español — punto separador de miles, coma decimal
  Ejemplos: -100,00 | 2.827,82 | -1.200,00
- Tipos de operación:
  - Recarga - Antonio .Rev.
  - NOMINA TRF - 20950844-DIPUTACION DE HUELVA
  - REINT.CAJERO
  - Amazon Prime - Fecha de operación: 08-02-2026
  - TRANSF. A SU FAVOR - 20803704-FRANCISCO JAVIER...
  - OCASO S.A.SEV. - Recibo entidad de previsión
  - PRES.25017399819
  - Seguro Coche - Lucia
"""

import re
from typing import Iterator
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase


class ParserCaixaBank(ParserBase):
    """Parser para ficheros CSV exportados/convertidos desde CaixaBank."""

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido línea a línea."""
        lineas = contenido.strip().split("\n")

        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue

            # Delimitador: punto y coma
            campos = linea.split(";")

            # Saltar cabeceras y líneas con pocos campos
            if len(campos) < 4:
                continue
            if any(cab in campos[0].lower() for cab in ["fecha", "date", "descripción"]):
                continue

            try:
                fecha_op = self._parsear_fecha(campos[0].strip())
                fecha_valor = self._parsear_fecha(campos[1].strip())
                descripcion = campos[2].strip()
                importe_raw = campos[3].strip()

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

    def _parsear_fecha(self, texto: str) -> str:
        """Convierte DD/MM/YYYY a YYYY-MM-DD."""
        texto = texto.strip().strip('"')
        partes = texto.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        if re.match(r"\d{4}-\d{2}-\d{2}", texto):
            return texto
        raise ValueError(f"Formato de fecha no reconocido: {texto}")

    def _parsear_importe(self, texto: str) -> float:
        """Convierte '1.234,56' o '-45,30' a float (formato español)."""
        limpio = texto.strip().strip('"')
        limpio = limpio.replace("EUR", "").replace("€", "").strip()
        limpio = limpio.replace(".", "").replace(",", ".")
        return float(limpio)

    def _limpiar_descripcion(self, texto: str) -> str:
        """Limpia la descripción: quita espacios extra."""
        texto = texto.strip().strip('"')
        texto = " ".join(texto.split())
        return texto
