"""
FiDo — Datos iniciales (seed).
Inserta categorías, reglas, miembros y cuentas si la BD está vacía.
"""

from app import bd


def sembrar_si_vacio():
    """Inserta datos iniciales en cada tabla que esté vacía (independientemente)."""
    total_cat = bd.consultar_uno("SELECT COUNT(*) as total FROM categorias")
    if not total_cat or total_cat["total"] == 0:
        _sembrar_categorias()

    total_reglas = bd.consultar_uno("SELECT COUNT(*) as total FROM reglas")
    if not total_reglas or total_reglas["total"] == 0:
        _sembrar_reglas()

    total_miembros = bd.consultar_uno("SELECT COUNT(*) as total FROM miembros")
    if not total_miembros or total_miembros["total"] == 0:
        _sembrar_miembros()

    total_cuentas = bd.consultar_uno("SELECT COUNT(*) as total FROM cuentas")
    if not total_cuentas or total_cuentas["total"] == 0:
        _sembrar_cuentas()


def _sembrar_categorias():
    """Inserta las 13 categorías padre y sus subcategorías."""
    arbol = {
        ("🏠", "Hogar"): [
            "Hipoteca", "Luz", "Agua", "Gas", "Internet", "Comunidad",
            "Seguro hogar", "Mantenimiento", "Empleada hogar", "Impuestos"
        ],
        ("🛒", "Alimentación"): [
            "Supermercado", "Frutería", "Carnicería", "Panadería",
            "Pescadería", "Otros alimentación"
        ],
        ("🚗", "Transporte"): [
            "Combustible", "ITV", "Seguro coche", "Taller",
            "Transporte público", "Parking", "Peajes"
        ],
        ("🍽️", "Restauración"): [
            "Restaurantes", "Cafeterías", "Comida rápida", "Comida a domicilio"
        ],
        ("🏨", "Viajes"): [
            "Alojamiento", "Vuelos / Transporte", "Actividades", "Comidas en viaje"
        ],
        ("🎭", "Ocio"): [
            "Cine / Teatro", "Suscripciones", "Deporte", "Eventos"
        ],
        ("💊", "Salud"): [
            "Farmacia", "Médico", "Dentista", "Óptica", "Seguro médico"
        ],
        ("👕", "Ropa"): [
            "Adultos", "Niños", "Calzado"
        ],
        ("📚", "Educación"): [
            "Colegio", "Libros", "Extraescolares", "Academia"
        ],
        ("🛠️", "Tecnología"): [
            "Software", "Hardware", "Suscripciones tech"
        ],
        ("💰", "Ingresos"): [
            "Nómina", "Freelance", "Devoluciones", "Otros ingresos"
        ],
        ("🔄", "Transferencias"): [
            "Aporte cuenta común"
        ],
        ("💶", "Efectivo"): [
            "Retirada cajero"
        ],
    }

    orden_padre = 0
    for (icono, nombre_padre), hijas in arbol.items():
        padre_id = bd.ejecutar(
            "INSERT INTO categorias (nombre, padre_id, icono, orden) VALUES (?, NULL, ?, ?)",
            (nombre_padre, icono, orden_padre)
        )
        for orden_hija, nombre_hija in enumerate(hijas):
            bd.ejecutar(
                "INSERT INTO categorias (nombre, padre_id, icono, orden) VALUES (?, ?, NULL, ?)",
                (nombre_hija, padre_id, orden_hija)
            )
        orden_padre += 1


def _sembrar_reglas():
    """Inserta las reglas de categorización extraídas del extracto bancario real."""
    # Mapeo: (patrón, categoría_padre, subcategoría, prioridad)
    reglas = [
        # Alimentación > Supermercado
        ("mercadona", "Alimentación", "Supermercado", 10),
        ("el jamon", "Alimentación", "Supermercado", 10),
        ("coviran", "Alimentación", "Supermercado", 10),
        ("dia retail", "Alimentación", "Supermercado", 10),
        ("cash huelva", "Alimentación", "Supermercado", 10),
        # Alimentación > Pescadería
        ("pescados", "Alimentación", "Pescadería", 10),
        # Alimentación > Otros alimentación
        ("atun y mojamas", "Alimentación", "Otros alimentación", 10),
        # Alimentación > Panadería
        ("panaderia", "Alimentación", "Panadería", 10),
        # Salud
        ("farmacia", "Salud", "Farmacia", 10),
        ("clinica enrile", "Salud", "Médico", 10),
        # Restauración
        ("fuente de hispa", "Restauración", "Cafeterías", 10),
        ("costa luz", "Restauración", "Restaurantes", 10),
        ("correlimos", "Restauración", "Restaurantes", 10),
        ("bodegas del pin", "Restauración", "Restaurantes", 10),
        # Hogar
        ("digi spain", "Hogar", "Internet", 10),
        ("jazztel", "Hogar", "Internet", 10),
        ("naturgy", "Hogar", "Luz", 10),
        ("comunidad avda italia", "Hogar", "Comunidad", 10),
        ("liquidacion periodica prestamo", "Hogar", "Hipoteca", 20),
        ("entidad conservacion", "Hogar", "Comunidad", 10),
        ("adeli", "Hogar", "Empleada hogar", 10),
        ("agencia provincial tributaria", "Hogar", "Impuestos", 10),
        # Ropa
        ("sfera", "Ropa", "Adultos", 10),
        # Hogar > Mantenimiento
        ("colchoness", "Hogar", "Mantenimiento", 10),
        # Educación
        ("kedaro", "Educación", "Academia", 10),
        # Efectivo
        ("retirada de efectivo", "Efectivo", "Retirada cajero", 20),
        # Transferencias
        ("aporte cuenta comun", "Transferencias", "Aporte cuenta común", 15),
    ]

    for patron, nombre_padre, nombre_hija, prioridad in reglas:
        # Buscar la categoría hija por nombre y nombre del padre
        categoria = bd.consultar_uno(
            """SELECT h.id FROM categorias h
               JOIN categorias p ON h.padre_id = p.id
               WHERE h.nombre = ? AND p.nombre = ?""",
            (nombre_hija, nombre_padre)
        )
        if categoria:
            bd.ejecutar(
                "INSERT INTO reglas (patron, categoria_id, prioridad) VALUES (?, ?, ?)",
                (patron, categoria["id"], prioridad)
            )


def _sembrar_miembros():
    """Inserta los miembros iniciales de la familia."""
    bd.ejecutar(
        "INSERT INTO miembros (nombre) VALUES (?)",
        ("Antonio",)
    )
    bd.ejecutar(
        "INSERT INTO miembros (nombre) VALUES (?)",
        ("Lucía",)
    )


def _sembrar_cuentas():
    """Inserta las cuentas bancarias iniciales."""
    antonio = bd.consultar_uno("SELECT id FROM miembros WHERE nombre = 'Antonio'")
    lucia = bd.consultar_uno("SELECT id FROM miembros WHERE nombre = 'Lucía'")

    if not antonio or not lucia:
        return

    # Cuenta Antonio (Santander)
    bd.ejecutar(
        """INSERT INTO cuentas (nombre, banco, iban, miembro_id, es_compartida)
           VALUES (?, ?, ?, ?, ?)""",
        ("Cuenta Antonio", "santander", "ES7000304130120002342271", antonio["id"], 0)
    )

    # Cuenta Lucía
    bd.ejecutar(
        """INSERT INTO cuentas (nombre, banco, miembro_id, es_compartida)
           VALUES (?, ?, ?, ?)""",
        ("Cuenta Lucía", None, lucia["id"], 0)
    )

    # Cuenta Común
    bd.ejecutar(
        """INSERT INTO cuentas (nombre, banco, miembro_id, es_compartida)
           VALUES (?, ?, ?, ?)""",
        ("Cuenta Común", "santander", antonio["id"], 1)
    )

    # Tarjeta Hijo (Revolut)
    bd.ejecutar(
        """INSERT INTO cuentas (nombre, banco, miembro_id, es_compartida)
           VALUES (?, ?, ?, ?)""",
        ("Tarjeta Hijo", "revolut", antonio["id"], 0)
    )
