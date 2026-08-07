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
    try:
        cursor = conexion.execute(sql, parametros)
        conexion.commit()
        return cursor.lastrowid
    finally:
        conexion.close()


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
      v1→v2: Añade 'ntfy' al CHECK de movimientos.origen.
      v3:    Añade columna 'estado' (ok|revisar).
      v4:    Añade columna 'es_transferencia_interna' y tabla cuentas_vinculadas.
      v5:    Añade 'drive' al CHECK de movimientos.origen. Necesaria porque la BD
             de producción puede tener 'ntfy' pero no 'drive' si la migración v1→v2
             se ejecutó antes de que se añadiera 'drive' al bloque inline.
      v6:    Convierte el índice de 'huella' en UNIQUE, para que la propia base
             de datos rechace duplicados aunque dos inserciones casi simultáneas
             (p.ej. durante un redeploy que solapa el listener NTFY viejo y el
             nuevo) pasen el chequeo previo de 'buscar_duplicados' a la vez.
             Antes de crear el índice, elimina huellas repetidas que ya existan
             (conserva la fila con el id más bajo de cada grupo); las filas sin
             huella (NULL) no se tocan, ya que SQLite no las considera iguales
             entre sí a efectos de un índice único.
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
                                     CHECK(origen IN ('telegram','wallet','csv','web','ntfy','drive')),
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

    # Migración v5: añadir 'drive' al CHECK de origen si no está.
    # La BD de producción puede tener 'ntfy' pero no 'drive' si la migración v1→v2
    # se ejecutó antes de añadir 'drive' al bloque inline de esa migración.
    fila_v5 = conexion.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='movimientos'"
    ).fetchone()
    if fila_v5 and "'drive'" not in fila_v5[0]:
        conexion.executescript("""
            ALTER TABLE movimientos RENAME TO movimientos_v5;

            CREATE TABLE movimientos (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha                    TEXT    NOT NULL,
                fecha_valor              TEXT,
                importe                  REAL    NOT NULL,
                descripcion              TEXT    NOT NULL,
                descripcion_original     TEXT,
                categoria_id             INTEGER REFERENCES categorias(id),
                cuenta_id                INTEGER NOT NULL REFERENCES cuentas(id),
                origen                   TEXT    NOT NULL
                                         CHECK(origen IN ('telegram','wallet','csv','web','ntfy','drive')),
                origen_ref               TEXT,
                huella                   TEXT,
                notas                    TEXT,
                creado_en                TEXT    NOT NULL DEFAULT (datetime('now')),
                estado                   TEXT    NOT NULL DEFAULT 'ok',
                es_transferencia_interna INTEGER NOT NULL DEFAULT 0
            );

            INSERT INTO movimientos
                SELECT id, fecha, fecha_valor, importe, descripcion, descripcion_original,
                       categoria_id, cuenta_id, origen, origen_ref, huella, notas,
                       creado_en, estado, es_transferencia_interna
                FROM movimientos_v5;

            DROP TABLE movimientos_v5;

            CREATE INDEX IF NOT EXISTS idx_movimientos_fecha     ON movimientos(fecha);
            CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta    ON movimientos(cuenta_id);
            CREATE INDEX IF NOT EXISTS idx_movimientos_categoria ON movimientos(categoria_id);
            CREATE INDEX IF NOT EXISTS idx_movimientos_huella    ON movimientos(huella);
        """)

    # Migración v6: índice único sobre 'huella'
    indice = conexion.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_movimientos_huella'"
    ).fetchone()
    if not indice or not indice[0] or "UNIQUE" not in indice[0]:
        conexion.execute("""
            DELETE FROM movimientos
            WHERE huella IS NOT NULL
            AND id NOT IN (
                SELECT MIN(id) FROM movimientos WHERE huella IS NOT NULL GROUP BY huella
            )
        """)
        conexion.execute("DROP INDEX IF EXISTS idx_movimientos_huella")
        conexion.execute("CREATE UNIQUE INDEX idx_movimientos_huella ON movimientos(huella)")
        conexion.commit()

    conexion.close()
