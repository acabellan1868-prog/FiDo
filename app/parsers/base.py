"""FiDo — Clase base abstracta para parsers de extractos bancarios."""

from abc import ABC, abstractmethod
from typing import Iterator
from app.modelos import MovimientoCrear


class ParserBase(ABC):
    """Cada banco implementa su propio parser heredando de esta clase."""

    @abstractmethod
    def parsear(self, contenido: str, cuenta_id: int) -> Iterator[MovimientoCrear]:
        """Parsea el contenido del fichero y genera movimientos."""
        ...
