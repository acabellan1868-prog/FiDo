"""FiDo — Parser para extractos de CaixaBank.

Formato del extracto CSV exportado desde CaixaBank:
- Delimitador: coma
- Columnas: Fecha,Fecha valor,Movimiento,Más datos,Importe,Saldo
- Fechas: DD/MM/YYYY
- Importes: formato español con comillas — "-70,00" | "2.827,82"
- Encoding: UTF-8 o ISO-8859-1 (gestionado en importar.py)
"""

import csv
import io
import re
from typing import Iterator
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase


class ParserCaixaBank(ParserBase):
    """Parser para ficheros CSV exportados desde CaixaBank."""

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido usando el módulo csv para manejar campos entrecomillados."""
        lector = csv.reader(io.StringIO(contenido.strip()))

        for campos in lector:
            if len(campos) < 5:
                continue

            # Saltar cabecera
            if any(cab in campos[0].lower() for cab in ["fecha", "date"]):
                continue

            try:
                fecha_op    = self._parsear_fecha(campos[0].strip())
                fecha_valor = self._parsear_fecha(campos[1].strip())

                # Descripción = Movimiento + Más datos (si existe y no está vacío)
                descripcion = campos[2].strip()
                mas_datos   = campos[3].strip() if len(campos) > 3 else ""
                if mas_datos:
                    descripcion = f"{descripcion} - {mas_datos}"

                importe = self._parsear_importe(campos[4].strip())

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
        """Convierte '1.234,56' o '-70,00' a float (formato español)."""
        limpio = texto.strip().strip('"')
        limpio = limpio.replace("EUR", "").replace("€", "").strip()
        limpio = limpio.replace(".", "").replace(",", ".")
        return float(limpio)

    def _limpiar_descripcion(self, texto: str) -> str:
        """Limpia la descripción: quita espacios extra y comillas."""
        texto = texto.strip().strip('"')
        texto = " ".join(texto.split())
        return texto
