-- ============================================================
-- FiDo — Esquema de base de datos v1
-- ============================================================

-- Miembros de la familia
CREATE TABLE IF NOT EXISTS miembros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    telegram_chat_id TEXT,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Cuentas bancarias
CREATE TABLE IF NOT EXISTS cuentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    banco TEXT,
    iban TEXT,
    miembro_id INTEGER REFERENCES miembros(id),
    es_compartida INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Categorías en dos niveles (padre_id NULL = nivel 1)
CREATE TABLE IF NOT EXISTS categorias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    padre_id INTEGER REFERENCES categorias(id),
    icono TEXT,
    orden INTEGER NOT NULL DEFAULT 0,
    UNIQUE(nombre, padre_id)
);

-- Reglas de categorización automática
CREATE TABLE IF NOT EXISTS reglas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patron TEXT NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    prioridad INTEGER NOT NULL DEFAULT 0,
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Movimientos (gastos e ingresos)
CREATE TABLE IF NOT EXISTS movimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    fecha_valor TEXT,
    importe REAL NOT NULL,
    descripcion TEXT NOT NULL,
    descripcion_original TEXT,
    categoria_id INTEGER REFERENCES categorias(id),
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    origen TEXT NOT NULL CHECK(origen IN ('telegram', 'wallet', 'csv', 'web', 'ntfy')),
    origen_ref TEXT,
    huella TEXT,
    notas TEXT,
    estado TEXT NOT NULL DEFAULT 'ok' CHECK(estado IN ('ok', 'revisar')),
    creado_en TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Mapeo de últimos 4 dígitos de tarjeta a cuenta
CREATE TABLE IF NOT EXISTS mapeo_tarjetas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ultimos4 TEXT NOT NULL UNIQUE,
    cuenta_id INTEGER NOT NULL REFERENCES cuentas(id),
    etiqueta TEXT
);

-- Vinculaciones entre cuentas (ej: Caixa → Revolut)
-- Los movimientos que coincidan con los patrones de ambos lados
-- y tengan el mismo importe en fechas próximas se marcan automáticamente
-- como transferencias internas y se excluyen de los informes.
CREATE TABLE IF NOT EXISTS cuentas_vinculadas (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    cuenta_principal_id  INTEGER NOT NULL REFERENCES cuentas(id),
    cuenta_vinculada_id  INTEGER NOT NULL REFERENCES cuentas(id),
    patron_principal     TEXT    NOT NULL,  -- patrón LIKE para el gasto en la cuenta principal
    patron_vinculada     TEXT    NOT NULL,  -- patrón LIKE para el ingreso en la cuenta vinculada
    tolerancia_dias      INTEGER NOT NULL DEFAULT 1,
    UNIQUE(cuenta_principal_id, cuenta_vinculada_id)
);

-- Índices para rendimiento
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos(fecha);
CREATE INDEX IF NOT EXISTS idx_movimientos_cuenta ON movimientos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_categoria ON movimientos(categoria_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_huella ON movimientos(huella);
CREATE INDEX IF NOT EXISTS idx_reglas_patron ON reglas(patron);
