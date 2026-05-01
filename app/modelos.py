"""
FiDo — Modelos Pydantic (esquemas de request/response).
Todas las entidades tienen variantes Crear, Actualizar y Respuesta.
"""

from pydantic import BaseModel
from typing import Optional


# ============================================================
# Miembros
# ============================================================

class MiembroCrear(BaseModel):
    nombre: str
    telegram_chat_id: Optional[str] = None

class MiembroActualizar(BaseModel):
    nombre: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class MiembroRespuesta(BaseModel):
    id: int
    nombre: str
    telegram_chat_id: Optional[str] = None
    creado_en: Optional[str] = None


# ============================================================
# Cuentas
# ============================================================

class CuentaCrear(BaseModel):
    nombre: str
    banco: Optional[str] = None
    iban: Optional[str] = None
    miembro_id: Optional[int] = None
    es_compartida: bool = False

class CuentaActualizar(BaseModel):
    nombre: Optional[str] = None
    banco: Optional[str] = None
    iban: Optional[str] = None
    miembro_id: Optional[int] = None
    es_compartida: Optional[bool] = None

class CuentaRespuesta(BaseModel):
    id: int
    nombre: str
    banco: Optional[str] = None
    iban: Optional[str] = None
    miembro_id: Optional[int] = None
    es_compartida: int = 0
    creado_en: Optional[str] = None


# ============================================================
# Categorías
# ============================================================

class CategoriaCrear(BaseModel):
    nombre: str
    padre_id: Optional[int] = None
    icono: Optional[str] = None
    orden: int = 0

class CategoriaActualizar(BaseModel):
    nombre: Optional[str] = None
    padre_id: Optional[int] = None
    icono: Optional[str] = None
    orden: Optional[int] = None

class CategoriaRespuesta(BaseModel):
    id: int
    nombre: str
    padre_id: Optional[int] = None
    icono: Optional[str] = None
    orden: int = 0

class CategoriaArbol(BaseModel):
    """Categoría padre con sus hijas anidadas."""
    id: int
    nombre: str
    icono: Optional[str] = None
    orden: int = 0
    hijas: list["CategoriaRespuesta"] = []


# ============================================================
# Reglas
# ============================================================

class ReglaCrear(BaseModel):
    patron: str
    categoria_id: int
    prioridad: int = 0

class ReglaActualizar(BaseModel):
    patron: Optional[str] = None
    categoria_id: Optional[int] = None
    prioridad: Optional[int] = None

class ReglaRespuesta(BaseModel):
    id: int
    patron: str
    categoria_id: int
    prioridad: int = 0
    creado_en: Optional[str] = None


# ============================================================
# Movimientos
# ============================================================

class MovimientoCrear(BaseModel):
    fecha: str  # YYYY-MM-DD
    fecha_valor: Optional[str] = None
    importe: float
    descripcion: str
    descripcion_original: Optional[str] = None
    categoria_id: Optional[int] = None
    cuenta_id: int
    origen: str  # telegram, wallet, csv, web, ntfy
    origen_ref: Optional[str] = None
    notas: Optional[str] = None
    estado: str = 'ok'  # ok | revisar

class MovimientoActualizar(BaseModel):
    fecha: Optional[str] = None
    fecha_valor: Optional[str] = None
    importe: Optional[float] = None
    descripcion: Optional[str] = None
    categoria_id: Optional[int] = None
    cuenta_id: Optional[int] = None
    notas: Optional[str] = None
    estado: Optional[str] = None  # ok | revisar

class MovimientoRespuesta(BaseModel):
    id: int
    fecha: str
    fecha_valor: Optional[str] = None
    importe: float
    descripcion: str
    descripcion_original: Optional[str] = None
    categoria_id: Optional[int] = None
    cuenta_id: int
    origen: str
    origen_ref: Optional[str] = None
    huella: Optional[str] = None
    notas: Optional[str] = None
    estado: str = 'ok'
    es_transferencia_interna: int = 0
    creado_en: Optional[str] = None
    # Campos extra que se rellenan con JOINs
    nombre_categoria: Optional[str] = None
    nombre_cuenta: Optional[str] = None


# ============================================================
# Mapeo de tarjetas
# ============================================================

class MapeoTarjetaCrear(BaseModel):
    ultimos4: str
    cuenta_id: int
    etiqueta: Optional[str] = None

class MapeoTarjetaActualizar(BaseModel):
    ultimos4: Optional[str] = None
    cuenta_id: Optional[int] = None
    etiqueta: Optional[str] = None

class MapeoTarjetaRespuesta(BaseModel):
    id: int
    ultimos4: str
    cuenta_id: int
    etiqueta: Optional[str] = None


# ============================================================
# Respuestas de importación
# ============================================================

class ResultadoImportacion(BaseModel):
    importados: int = 0
    duplicados: int = 0
    errores: int = 0
    detalles: list[dict] = []
