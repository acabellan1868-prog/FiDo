"""
FiDo — Módulo de base de datos SQLite.
Gestión de conexión, helpers y inicialización del esquema.
"""

import sqlite3
import os
from pathlib import Path

RUTA_BD = os.environ.get("FIDO_DB_PATH", "data/fido.db")


def obtener_conexion() -> sqlite3.Connection:
    """Abre una conexión a la BD con WAL y foreign keys activados."""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA journal_mode=WAL")
    conexion.execute("PRAGMA foreign_keys=ON")
    return conexion


def inicializar_bd():
    """Crea las tablas si no existen ejecutando esquema.sql."""
    ruta_esquema = Path(__file__).parent / "esquema.sql"
    conexion = obtener_conexion()
    conexion.executescript(ruta_esquema.read_text(encoding="utf-8"))
    conexion.close()


def consultar_todos(sql: str, parametros: tuple = ()) -> list[dict]:
    """Ejecuta una consulta SELECT y devuelve todas las filas como lista de dicts."""
    conexion = obtener_conexion()
    filas = conexion.execute(sql, parametros).fetchall()
    conexion.close()
    return [dict(fila) for fila in filas]


def consultar_uno(sql: str, parametros: tuple = ()) -> dict | None:
    """Ejecuta una consulta SELECT y devuelve una fila como dict, o None."""
    conexion = obtener_conexion()
    fila = conexion.execute(sql, parametros).fetchone()
    conexion.close()
    return dict(fila) if fila else None


def ejecutar(sql: str, parametros: tuple = ()) -> int:
    """Ejecuta INSERT/UPDATE/DELETE y devuelve el lastrowid."""
    conexion = obtener_conexion()
    cursor = conexion.execute(sql, parametros)
    conexion.commit()
    ultimo_id = cursor.lastrowid
    conexion.close()
    return ultimo_id


def ejecutar_varios(sql: str, lista_parametros: list[tuple]) -> None:
    """Ejecuta la misma sentencia con múltiples conjuntos de parámetros."""
    conexion = obtener_conexion()
    conexion.executemany(sql, lista_parametros)
    conexion.commit()
    conexion.close()


def migrar_bd():
    """Aplica migraciones de esquema sobre BDs existentes.

    Se ejecuta en cada arranque y es idempotente (seguro de llamar varias veces).

    Migraciones incluidas:
      v1→v2: Añade 'ntfy' al CHECK de movimientos.origen para soportar
              movimientos recibidos desde NTFY (intermediario de transporte).
    """
    conexion = obtener_conexion()

    fila = conexion.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='movimientos'"
    ).fetchone()

    if fila and "'ntfy'" not in fila[0]:
        # La BD tiene el esquema antiguo sin 'ntfy' — migrar recreando la tabla.
        # SQLite no permite ALTER COLUMN, así que se renombra, se crea la nueva
        # y se copian los datos.
        conexion.executescript("""
            ALTER TABLE movimientos RENAME TO movimientos_v1;

            CREATE TABLE movimientos (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha                TEXT    NOT NULL,
                fecha_valor          TEXT,
                importe              REAL    NOT NULL,
                descripcion          TEXT    NOT NULL,
                descripcion_original TEXT,
                categoria_id         INTEGER REFERENCES categorias(id),
                cuenta_id            INTEGER NOT NULL REFERENCES cuentas(id),
                origen               TEXT    NOT NULL
                                     CHECK(origen IN ('telegram','wallet','csv','web','ntfy')),
                origen_ref           TEXT,
                huella               TEXT,
                notas                TEXT,
                creado_en            TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            INSERT INTO movimientos SELECT * FROM movimientos_v1;
            DROP TABLE movimientos_v1;

            CREATE INDEX IF NOT EXISTS idx_movimientos_fecha     ON movimientos(fecha);
            CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta    ON movimientos(cuenta_id);
            CREATE INDEX IF NOT EXISTS idx_movimientos_categoria ON movimientos(categoria_id);
            CREATE INDEX IF NOT EXISTS idx_movimientos_huella    ON movimientos(huella);
        """)

    # Migración v3: añadir columna 'estado' si no existe
    # SQLite soporta ALTER TABLE ADD COLUMN — no hace falta recrear la tabla.
    columnas = [fila[1] for fila in conexion.execute("PRAGMA table_info(movimientos)").fetchall()]
    if "estado" not in columnas:
        conexion.execute("ALTER TABLE movimientos ADD COLUMN estado TEXT NOT NULL DEFAULT 'ok'")
        conexion.commit()

    # Migración v4: añadir columna 'es_transferencia_interna' si no existe
    columnas = [fila[1] for fila in conexion.execute("PRAGMA table_info(movimientos)").fetchall()]
    if "es_transferencia_interna" not in columnas:
        conexion.execute(
            "ALTER TABLE movimientos ADD COLUMN es_transferencia_interna INTEGER NOT NULL DEFAULT 0"
        )
        conexion.commit()

    # Migración v4: crear tabla cuentas_vinculadas si no existe
    tablas = [fila[0] for fila in conexion.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if "cuentas_vinculadas" not in tablas:
        conexion.executescript("""
            CREATE TABLE cuentas_vinculadas (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                cuenta_principal_id  INTEGER NOT NULL REFERENCES cuentas(id),
                cuenta_vinculada_id  INTEGER NOT NULL REFERENCES cuentas(id),
                patron_principal     TEXT    NOT NULL,
                patron_vinculada     TEXT    NOT NULL,
                tolerancia_dias      INTEGER NOT NULL DEFAULT 1,
                UNIQUE(cuenta_principal_id, cuenta_vinculada_id)
            );
        """)

    conexion.close()
