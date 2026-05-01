"""FiDo — Detector de transferencias internas entre cuentas vinculadas.

Busca pares de movimientos (gasto en cuenta principal + ingreso en cuenta
vinculada) que coincidan con los patrones configurados, mismo importe y
fechas dentro de la tolerancia. Los marca como es_transferencia_interna = 1
para excluirlos de los informes.
"""

from app import bd


def detectar_y_marcar() -> int:
    """Detecta pares de transferencias internas no marcados y los marca.

    Devuelve el número de pares marcados en esta ejecución.
    """
    vinculaciones = bd.consultar_todos("SELECT * FROM cuentas_vinculadas")
    pares_marcados = 0

    for vin in vinculaciones:
        pares = bd.consultar_todos(
            """
            SELECT mp.id AS id_principal, mv.id AS id_vinculada
            FROM movimientos mp
            JOIN movimientos mv
                ON ABS(mp.importe) = mv.importe
               AND ABS(julianday(mp.fecha) - julianday(mv.fecha)) <= ?
            WHERE mp.cuenta_id = ?
              AND mv.cuenta_id = ?
              AND mp.importe < 0
              AND mv.importe > 0
              AND mp.descripcion LIKE ?
              AND mv.descripcion LIKE ?
              AND mp.es_transferencia_interna = 0
              AND mv.es_transferencia_interna = 0
            """,
            (
                vin["tolerancia_dias"],
                vin["cuenta_principal_id"],
                vin["cuenta_vinculada_id"],
                vin["patron_principal"],
                vin["patron_vinculada"],
            ),
        )

        for par in pares:
            bd.ejecutar(
                "UPDATE movimientos SET es_transferencia_interna = 1 WHERE id = ?",
                (par["id_principal"],),
            )
            bd.ejecutar(
                "UPDATE movimientos SET es_transferencia_interna = 1 WHERE id = ?",
                (par["id_vinculada"],),
            )
            pares_marcados += 1

    return pares_marcados
