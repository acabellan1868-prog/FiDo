"""
FiDo — Punto de entrada de la aplicación FastAPI.
Inicializa la BD, siembra datos iniciales y registra todas las rutas.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.bd import inicializar_bd, RUTA_BD
from app.datos_iniciales import sembrar_si_vacio
from app.rutas import (
    miembros, cuentas, categorias, reglas,
    movimientos, mapeo_tarjetas, importar, sincronizar, panel, resumen
)


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    """Se ejecuta al arrancar la app: crea BD y siembra datos."""
    # Asegurar que el directorio de datos existe
    directorio_bd = os.path.dirname(RUTA_BD)
    if directorio_bd:
        os.makedirs(directorio_bd, exist_ok=True)

    inicializar_bd()
    sembrar_si_vacio()
    yield


app = FastAPI(
    title="FiDo — Finanzas Domésticas",
    description="API para gestionar las finanzas familiares",
    version="1.0.0",
    lifespan=ciclo_vida,
)

# ---- Registrar rutas API ----
app.include_router(miembros.ruta, prefix="/api/miembros", tags=["Miembros"])
app.include_router(cuentas.ruta, prefix="/api/cuentas", tags=["Cuentas"])
app.include_router(categorias.ruta, prefix="/api/categorias", tags=["Categorías"])
app.include_router(reglas.ruta, prefix="/api/reglas", tags=["Reglas"])
app.include_router(movimientos.ruta, prefix="/api/movimientos", tags=["Movimientos"])
app.include_router(mapeo_tarjetas.ruta, prefix="/api/mapeo-tarjetas", tags=["Mapeo Tarjetas"])
app.include_router(importar.ruta, prefix="/api/importar", tags=["Importar"])
app.include_router(sincronizar.ruta, prefix="/api/sincronizar", tags=["Sincronizar"])
app.include_router(panel.ruta, prefix="/api/panel", tags=["Panel"])
app.include_router(resumen.ruta, prefix="/api/resumen", tags=["Resumen"])

# ---- Servir frontend estático (DEBE ir al final, es catch-all) ----
app.mount("/", StaticFiles(directory="static", html=True), name="static")
