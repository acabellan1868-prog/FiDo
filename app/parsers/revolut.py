"""FiDo — Parser para extractos de Revolut.

Formato del CSV exportado desde Revolut (app en español):
- Delimitador: coma (,) — campos entrecomillados si contienen comas
- Columnas (ES): Tipo,Producto,Fecha de inicio,Fecha de finalización,Descripción,Importe,Comisión,Divisa,State,Saldo
- Columnas (EN): Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
- Fechas: YYYY-MM-DD HH:MM:SS
- Importes: punto decimal, sin separador de miles
  Ejemplos: -13.00 | 1200.50 | -4.95
- Solo se importan movimientos con State = COMPLETADO / COMPLETED
- Tipos de operación:
  - Pago con tarjeta / CARD_PAYMENT
  - Recargas / TOPUP
  - Transferir / TRANSFER
  - Reembolso de tarjeta / CARD_REFUND
  - REVX_TRANSFER — transferencia a/desde Revolut X (ahorro)
"""

import csv
import io
import re
from typing import Iterator
from app.modelos import MovimientoCrear
from app.parsers.base import ParserBase

# Mapeo de cabeceras ES → EN para normalizar
_MAPEO_CABECERAS = {
    "Tipo": "Type",
    "Producto": "Product",
    "Fecha de inicio": "Started Date",
    "Fecha de finalización": "Completed Date",
    "Descripción": "Description",
    "Importe": "Amount",
    "Comisión": "Fee",
    "Divisa": "Currency",
    "Saldo": "Balance",
    # State ya viene en inglés en ambos formatos
}


class ParserRevolut(ParserBase):
    """Parser para ficheros CSV exportados desde Revolut (ES o EN)."""

    def _normalizar_fila(self, fila: dict) -> dict:
        """Normaliza las claves de una fila al formato EN."""
        normalizada = {}
        for clave, valor in fila.items():
            clave_limpia = clave.strip()
            clave_en = _MAPEO_CABECERAS.get(clave_limpia, clave_limpia)
            normalizada[clave_en] = valor
        return normalizada

    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido CSV de Revolut."""
        lector = csv.DictReader(io.StringIO(contenido))

        for fila_raw in lector:
            try:
                fila = self._normalizar_fila(fila_raw)

                # Solo importar movimientos completados
                estado = fila.get("State", "").strip().lower()
                if estado not in ("completed", "completado"):
                    continue

                # Moneda
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
