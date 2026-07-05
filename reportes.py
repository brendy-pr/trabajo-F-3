"""
Consultas y reportes para el modulo de analisis de datos.
"""

import sqlite3
from typing import Any, List, Optional

import pandas as pd

from database import obtener_conexion


COLUMNAS_INVENTARIO = [
    "id_producto",
    "codigo_barras",
    "nombre",
    "descripcion",
    "categoria",
    "unidad_medida",
    "stock_actual",
    "stock_minimo",
    "precio_compra",
    "precio_venta",
    "id_proveedor",
    "estado",
    "fecha_registro",
]

COLUMNAS_MOVIMIENTOS = [
    "id_movimiento",
    "id_producto",
    "codigo_barras",
    "producto",
    "tipo_movimiento",
    "cantidad",
    "fecha_movimiento",
    "motivo",
    "observacion",
]

COLUMNAS_ALERTAS = [
    "id_producto",
    "codigo_barras",
    "nombre",
    "categoria",
    "unidad_medida",
    "stock_actual",
    "stock_minimo",
    "margen",
    "stock_alerta",
    "cantidad_faltante",
    "estado",
]


def _dataframe_vacio(columnas: List[str]) -> pd.DataFrame:
    """
    Crea un DataFrame vacio con una estructura definida.
    """
    return pd.DataFrame(columns=columnas)


def obtener_inventario_general() -> pd.DataFrame:
    """
    Consulta la tabla productos y devuelve el inventario ordenado por nombre.
    """
    conexion: Optional[sqlite3.Connection] = None

    try:
        conexion = obtener_conexion()
        consulta = """
            SELECT
                id_producto,
                codigo_barras,
                nombre,
                descripcion,
                categoria,
                unidad_medida,
                stock_actual,
                stock_minimo,
                precio_compra,
                precio_venta,
                id_proveedor,
                estado,
                fecha_registro
            FROM productos
            ORDER BY nombre COLLATE NOCASE ASC;
        """
        dataframe = pd.read_sql_query(consulta, conexion)
        return dataframe if not dataframe.empty else _dataframe_vacio(COLUMNAS_INVENTARIO)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        print(f"Error al obtener inventario general: {error}")
        return _dataframe_vacio(COLUMNAS_INVENTARIO)
    finally:
        if conexion:
            conexion.close()


def reporte_movimientos_filtrado(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    tipo_movimiento: Optional[str] = None,
) -> pd.DataFrame:
    """
    Consulta movimientos con datos del producto y filtros opcionales.
    """
    conexion: Optional[sqlite3.Connection] = None
    condiciones: List[str] = []
    parametros: List[Any] = []

    if fecha_inicio is not None:
        condiciones.append("m.fecha_movimiento >= ?")
        parametros.append(fecha_inicio)

    if fecha_fin is not None:
        condiciones.append("m.fecha_movimiento <= ?")
        parametros.append(fecha_fin)

    if tipo_movimiento is not None:
        condiciones.append("m.tipo_movimiento = ?")
        parametros.append(tipo_movimiento)

    filtro_where = ""
    if condiciones:
        filtro_where = "WHERE " + " AND ".join(condiciones)

    consulta = f"""
        SELECT
            m.id_movimiento,
            m.id_producto,
            p.codigo_barras,
            p.nombre AS producto,
            m.tipo_movimiento,
            m.cantidad,
            m.fecha_movimiento,
            m.motivo,
            m.observacion
        FROM movimientos m
        LEFT JOIN productos p ON m.id_producto = p.id_producto
        {filtro_where}
        ORDER BY m.fecha_movimiento DESC, m.id_movimiento DESC;
    """

    try:
        conexion = obtener_conexion()
        dataframe = pd.read_sql_query(consulta, conexion, params=parametros)
        return dataframe if not dataframe.empty else _dataframe_vacio(COLUMNAS_MOVIMIENTOS)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        print(f"Error al generar reporte de movimientos: {error}")
        return _dataframe_vacio(COLUMNAS_MOVIMIENTOS)
    finally:
        if conexion:
            conexion.close()


def productos_proximos_a_agotarse(margen: int = 0) -> pd.DataFrame:
    """
    Devuelve productos cuyo stock actual esta dentro del umbral de alerta.
    """
    conexion: Optional[sqlite3.Connection] = None
    margen_alerta = max(0, margen)

    try:
        conexion = obtener_conexion()
        consulta = """
            SELECT
                id_producto,
                codigo_barras,
                nombre,
                categoria,
                unidad_medida,
                stock_actual,
                stock_minimo,
                ? AS margen,
                stock_minimo + ? AS stock_alerta,
                (stock_minimo + ?) - stock_actual AS cantidad_faltante,
                estado
            FROM productos
            WHERE stock_actual <= stock_minimo + ?
            ORDER BY cantidad_faltante DESC, nombre COLLATE NOCASE ASC;
        """
        parametros = (
            margen_alerta,
            margen_alerta,
            margen_alerta,
            margen_alerta,
        )
        dataframe = pd.read_sql_query(consulta, conexion, params=parametros)
        return dataframe if not dataframe.empty else _dataframe_vacio(COLUMNAS_ALERTAS)
    except (sqlite3.Error, pd.errors.DatabaseError) as error:
        print(f"Error al obtener productos proximos a agotarse: {error}")
        return _dataframe_vacio(COLUMNAS_ALERTAS)
    finally:
        if conexion:
            conexion.close()
