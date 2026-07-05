"""
Pronosticos de demanda para el sistema de gestion de almacen.

Este modulo analiza salidas historicas de inventario para estimar demanda futura.
"""

import sqlite3
from typing import Optional

import pandas as pd

from database import obtener_conexion


TIPO_MOVIMIENTO_SALIDA = "salida"
COLUMNAS_SUGERENCIAS_COMPRA = [
    "id_producto",
    "nombre",
    "stock_actual",
    "demanda_pronosticada",
    "cantidad_a_comprar",
]


def pronostico_promedio_movil(id_producto: int, ventana_meses: int = 3) -> float:
    """
    Proyecta la demanda del proximo mes usando promedio movil de salidas mensuales.

    Args:
        id_producto: Identificador del producto a analizar.
        ventana_meses: Cantidad de meses recientes usados para el promedio movil.

    Returns:
        Demanda estimada para el proximo mes. Devuelve 0.0 si no hay historial valido.
    """
    conexion: Optional[sqlite3.Connection] = None

    if ventana_meses <= 0:
        raise ValueError("ventana_meses debe ser mayor que cero.")

    try:
        conexion = obtener_conexion()
        consulta = """
            SELECT
                cantidad,
                fecha_movimiento
            FROM movimientos
            WHERE id_producto = ?
              AND LOWER(tipo_movimiento) = ?
            ORDER BY fecha_movimiento ASC;
        """
        dataframe = pd.read_sql_query(
            consulta,
            conexion,
            params=(id_producto, TIPO_MOVIMIENTO_SALIDA),
        )

        if dataframe.empty:
            return 0.0

        dataframe["fecha_movimiento"] = pd.to_datetime(
            dataframe["fecha_movimiento"],
            errors="coerce",
        )
        dataframe["cantidad"] = pd.to_numeric(dataframe["cantidad"], errors="coerce")
        dataframe = dataframe.dropna(subset=["fecha_movimiento", "cantidad"])

        if dataframe.empty:
            return 0.0

        dataframe["mes"] = dataframe["fecha_movimiento"].dt.to_period("M")
        demanda_mensual = (
            dataframe.groupby("mes")["cantidad"]
            .sum()
            .sort_index()
        )

        if demanda_mensual.empty:
            return 0.0

        ultimos_meses = demanda_mensual.tail(ventana_meses)
        return float(ultimos_meses.mean())
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        print(f"Error al calcular pronostico de promedio movil: {error}")
        return 0.0
    finally:
        if conexion:
            conexion.close()


def sugerir_cantidades_compra() -> pd.DataFrame:
    """
    Sugiere cantidades de compra segun stock actual, stock minimo y demanda estimada.

    Returns:
        DataFrame con id_producto, nombre, stock_actual, demanda_pronosticada
        y cantidad_a_comprar. Si no hay productos o ocurre un error, devuelve
        un DataFrame vacio con esas columnas.
    """
    conexion: Optional[sqlite3.Connection] = None

    try:
        conexion = obtener_conexion()
        consulta = """
            SELECT
                id_producto,
                nombre,
                stock_actual,
                stock_minimo
            FROM productos
            ORDER BY nombre COLLATE NOCASE ASC;
        """
        productos = pd.read_sql_query(consulta, conexion)

        if productos.empty:
            return pd.DataFrame(columns=COLUMNAS_SUGERENCIAS_COMPRA)

        sugerencias = []
        for _, producto in productos.iterrows():
            id_producto = int(producto["id_producto"])
            nombre = producto["nombre"]
            stock_actual = float(producto["stock_actual"] or 0)
            stock_minimo = float(producto["stock_minimo"] or 0)
            demanda_proyectada = pronostico_promedio_movil(id_producto)

            punto_reabastecimiento = stock_minimo + demanda_proyectada
            if stock_actual < punto_reabastecimiento:
                cantidad_a_comprar = punto_reabastecimiento - stock_actual
            else:
                cantidad_a_comprar = 0.0

            sugerencias.append(
                {
                    "id_producto": id_producto,
                    "nombre": nombre,
                    "stock_actual": stock_actual,
                    "demanda_pronosticada": float(demanda_proyectada),
                    "cantidad_a_comprar": float(cantidad_a_comprar),
                }
            )

        return pd.DataFrame(sugerencias, columns=COLUMNAS_SUGERENCIAS_COMPRA)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        print(f"Error al sugerir cantidades de compra: {error}")
        return pd.DataFrame(columns=COLUMNAS_SUGERENCIAS_COMPRA)
    finally:
        if conexion:
            conexion.close()
