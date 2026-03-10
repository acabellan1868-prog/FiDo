"""FiDo — Parser para extractos de Revolut.

Formato típico del CSV exportado desde Revolut:
- Delimitador: coma (,) — campos entrecomillados si contienen comas
- Columnas: Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
- Fechas: YYYY-MM-DD HH:MM:SS o similar
- Importes: punto decimal, sin separador de miles
  Ejemplos: -13.00 | 1200.50 | -4.95
- Solo se importan movimientos con State = Completed
- Tipos de operación:
  - CARD_PAYMENT — Pago con tarjeta
  - TOPUP — Recarga desde otra cuenta
  - TRANSFER — Transferencia entre cuentas/personas
  - EXCHANGE — Cambio de divisa
  - ATM — Retirada de cajero
"""

import csv
import io
import re
from typing import Iterator
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase


class ParserRevolut(ParserBase):
    """Parser para ficheros CSV exportados desde Revolut."""

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido CSV de Revolut."""
        lector = csv.DictReader(io.StringIO(contenido))

        for fila in lector:
            try:
                # Solo importar movimientos completados
                estado = fila.get("State", "").strip()
                if estado.lower() != "completed":
                    continue

                # Solo importar EUR (o la moneda principal)
                moneda = fila.get("Currency", "").strip()

                # Parsear fechas
                fecha_inicio = self._parsear_fecha(fila.get("Started Date", "").strip())
                fecha_completado = self._parsear_fecha(
                    fila.get("Completed Date", "").strip()
                ) or fecha_inicio

                # Parsear importe
                importe_raw = fila.get("Amount", "").strip()
                if not importe_raw:
                    continue
                importe = float(importe_raw)

                # Descripción: combinar tipo + descripción
                tipo = fila.get("Type", "").strip()
                descripcion = fila.get("Description", "").strip()
                desc_completa = f"{tipo}: {descripcion}" if tipo else descripcion

                # Añadir moneda si no es EUR
                if moneda and moneda.upper() != "EUR":
                    desc_completa += f" ({moneda})"

                yield MovimientoCrear(
                    fecha=fecha_inicio,
                    fecha_valor=fecha_completado,
                    importe=importe,
                    descripcion=self._limpiar_descripcion(desc_completa),
                    descripcion_original=desc_completa,
                    cuenta_id=cuenta_id,
                    origen="csv",
                )
            except (ValueError, KeyError):
                continue

    def _parsear_fecha(self, texto: str) -> str:
        """Convierte fecha Revolut a YYYY-MM-DD.

        Formatos aceptados:
        - YYYY-MM-DD HH:MM:SS
        - YYYY-MM-DD
        - DD/MM/YYYY
        """
        if not texto:
            return ""
        texto = texto.strip().strip('"')

        # YYYY-MM-DD (con o sin hora)
        match = re.match(r"(\d{4}-\d{2}-\d{2})", texto)
        if match:
            return match.group(1)

        # DD/MM/YYYY
        partes = texto.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"

        raise ValueError(f"Formato de fecha no reconocido: {texto}")

    def _limpiar_descripcion(self, texto: str) -> str:
        """Limpia la descripción."""
        texto = texto.strip().strip('"')
        texto = " ".join(texto.split())
        return texto
