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

    # Siempre intentar añadir reglas nuevas (idempotente)
    _añadir_reglas_faltantes()

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


def _añadir_reglas_faltantes():
    """Añade reglas nuevas si no existen (idempotente). Se ejecuta en cada arranque."""
    reglas_extra = [
        # === CaixaBank ===
        # Ingresos
        ("nomina trf", "Ingresos", "Nómina", 20),
        ("nomina", "Ingresos", "Nómina", 15),
        ("transf. a su favor", "Ingresos", "Otros ingresos", 10),
        # Efectivo
        ("reint.cajero", "Efectivo", "Retirada cajero", 20),
        # Hogar
        ("ocaso", "Hogar", "Seguro hogar", 10),
        ("pres.250", "Hogar", "Hipoteca", 15),
        ("seguro coche", "Transporte", "Seguro coche", 15),
        # Transferencias / Recargas
        ("recarga", "Transferencias", "Aporte cuenta común", 5),
        ("aporte cuenta com", "Transferencias", "Aporte cuenta común", 15),

        # === Revolut — Restauración ===
        ("bk hue", "Restauración", "Comida rápida", 10),
        ("burger king", "Restauración", "Comida rápida", 10),
        ("pizza hut", "Restauración", "Comida rápida", 10),
        ("domino", "Restauración", "Comida a domicilio", 10),
        ("el rinconcito", "Restauración", "Cafeterías", 10),
        ("el tercer tiempo", "Restauración", "Restaurantes", 10),
        ("sonambulo", "Restauración", "Restaurantes", 10),
        ("la mafia", "Restauración", "Restaurantes", 10),
        ("la clandestina", "Restauración", "Restaurantes", 10),
        ("la fonda", "Restauración", "Restaurantes", 10),
        ("taberna la sorpresa", "Restauración", "Restaurantes", 10),
        ("pura huelva", "Restauración", "Restaurantes", 10),
        ("cafeteria piranchelo", "Restauración", "Cafeterías", 10),
        ("zebra coffe", "Restauración", "Cafeterías", 10),
        ("manolo bakes", "Restauración", "Cafeterías", 10),
        ("granvia uno", "Restauración", "Cafeterías", 10),
        ("bar la teja", "Restauración", "Restaurantes", 10),
        ("heladeria taco roll", "Restauración", "Cafeterías", 10),
        ("hermanos novalio", "Alimentación", "Panadería", 10),

        # === Revolut — Alimentación ===
        ("granier", "Alimentación", "Panadería", 10),
        ("ambrosio", "Alimentación", "Supermercado", 10),
        ("cash lepe", "Alimentación", "Supermercado", 10),
        ("bazar asia", "Alimentación", "Supermercado", 10),
        ("dulceria novaruiz", "Alimentación", "Panadería", 10),
        ("carrefour", "Alimentación", "Supermercado", 10),
        ("coviran", "Alimentación", "Supermercado", 10),
        ("el rey del pollo", "Alimentación", "Otros alimentación", 10),
        ("alimentacion ye", "Alimentación", "Supermercado", 10),
        ("espacio rubens", "Alimentación", "Supermercado", 10),
        ("jamones miguel romero", "Alimentación", "Otros alimentación", 10),
        ("burguer hnos rodriguez", "Restauración", "Comida rápida", 10),

        # === Revolut — Salud ===
        ("fcia", "Salud", "Farmacia", 10),
        ("farmacia garcia", "Salud", "Farmacia", 10),

        # === Revolut — Transporte ===
        ("parkinglibre", "Transporte", "Parking", 10),
        ("ipark", "Transporte", "Parking", 10),
        ("bolt", "Transporte", "Transporte público", 10),

        # === Revolut — Ocio / Suscripciones ===
        ("claude.ai", "Tecnología", "Suscripciones tech", 10),
        ("amazon prime", "Ocio", "Suscripciones", 15),
        ("fever", "Ocio", "Eventos", 10),
        ("steam", "Ocio", "Suscripciones", 10),
        ("google play", "Tecnología", "Software", 10),
        ("gamsgo", "Tecnología", "Suscripciones tech", 10),

        # === Revolut — Compras online ===
        ("amazon", "Tecnología", "Hardware", 5),
        ("aliexpress", "Tecnología", "Hardware", 5),

        # === Revolut — Educación ===
        ("factoria raton perez", "Ocio", "Eventos", 10),

        # === Revolut — Otros ===
        ("catedral de cadiz", "Ocio", "Eventos", 10),
        ("nulomi", "Alimentación", "Otros alimentación", 10),

        # === Revolut — Transferencias internas ===
        ("transferencia a antonio", "Transferencias", "Aporte cuenta común", 10),
        ("transferencia de antonio", "Ingresos", "Otros ingresos", 10),
        ("revolut x", "Transferencias", "Aporte cuenta común", 10),
        ("pago de antonio", "Ingresos", "Otros ingresos", 10),
    ]

    for patron, nombre_padre, nombre_hija, prioridad in reglas_extra:
        # Comprobar si el patrón ya existe
        existente = bd.consultar_uno(
            "SELECT id FROM reglas WHERE patron = ?", (patron,)
        )
        if existente:
            continue

        # Buscar la categoría hija
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
