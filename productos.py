"""
Logica de negocio para el modulo de productos.
"""

import sqlite3

import pandas as pd

from database import obtener_conexion


CAMPOS_EDITABLES = {
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
}


def _fila_a_diccionario(fila):
    return dict(fila) if fila else None


def validar_codigo_duplicado(codigo_barras, id_producto_excluir=None):
    """
    Verifica si ya existe un producto con el mismo codigo de barras.
    """
    conexion = None

    try:
        conexion = obtener_conexion()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()

        consulta = "SELECT id_producto FROM productos WHERE codigo_barras = ?"
        parametros = [codigo_barras]

        if id_producto_excluir is not None:
            consulta += " AND id_producto <> ?"
            parametros.append(id_producto_excluir)

        cursor.execute(consulta, parametros)
        return cursor.fetchone() is not None
    except sqlite3.Error as error:
        print(f"Error al validar codigo duplicado: {error}")
        return True
    finally:
        if conexion:
            conexion.close()


def registrar_producto(
    codigo_barras,
    nombre,
    descripcion,
    categoria,
    unidad_medida,
    stock_actual,
    stock_minimo,
    precio_compra,
    precio_venta,
    id_proveedor=None,
):
    """
    Registra un nuevo producto despues de validar que el codigo no exista.
    """
    if validar_codigo_duplicado(codigo_barras):
        return False, "Ya existe un producto con ese codigo de barras."

    conexion = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO productos (
                codigo_barras,
                nombre,
                descripcion,
                categoria,
                unidad_medida,
                stock_actual,
                stock_minimo,
                precio_compra,
                precio_venta,
                id_proveedor
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
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
            ),
        )
        conexion.commit()
        return True, "Producto registrado correctamente."
    except sqlite3.IntegrityError as error:
        if conexion:
            conexion.rollback()
        return False, f"No se pudo registrar el producto: {error}"
    except sqlite3.Error as error:
        if conexion:
            conexion.rollback()
        return False, f"Error de SQLite al registrar producto: {error}"
    finally:
        if conexion:
            conexion.close()


def editar_producto(id_producto, **kwargs):
    """
    Edita un producto usando campos dinamicos recibidos como argumentos.
    """
    datos = {
        campo: valor
        for campo, valor in kwargs.items()
        if campo in CAMPOS_EDITABLES and valor is not None
    }

    if not datos:
        return False, "No se recibieron campos validos para actualizar."

    if "codigo_barras" in datos and validar_codigo_duplicado(
        datos["codigo_barras"], id_producto_excluir=id_producto
    ):
        return False, "Ya existe otro producto con ese codigo de barras."

    conexion = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        asignaciones = ", ".join(f"{campo} = ?" for campo in datos)
        valores = list(datos.values())
        valores.append(id_producto)

        cursor.execute(
            f"UPDATE productos SET {asignaciones} WHERE id_producto = ?;",
            valores,
        )
        conexion.commit()

        if cursor.rowcount == 0:
            return False, "No se encontro un producto con ese ID."

        return True, "Producto actualizado correctamente."
    except sqlite3.IntegrityError as error:
        if conexion:
            conexion.rollback()
        return False, f"No se pudo actualizar el producto: {error}"
    except sqlite3.Error as error:
        if conexion:
            conexion.rollback()
        return False, f"Error de SQLite al actualizar producto: {error}"
    finally:
        if conexion:
            conexion.close()


def eliminar_producto(id_producto):
    """
    Elimina un producto. Si tiene movimientos asociados, SQLite lo impedira.
    """
    conexion = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM productos WHERE id_producto = ?;", (id_producto,))
        conexion.commit()

        if cursor.rowcount == 0:
            return False, "No se encontro un producto con ese ID."

        return True, "Producto eliminado correctamente."
    except sqlite3.IntegrityError:
        if conexion:
            conexion.rollback()
        return (
            False,
            "No se puede eliminar el producto porque tiene movimientos asociados.",
        )
    except sqlite3.Error as error:
        if conexion:
            conexion.rollback()
        return False, f"Error de SQLite al eliminar producto: {error}"
    finally:
        if conexion:
            conexion.close()


def buscar_producto(termino):
    """
    Busca productos por nombre o codigo de barras.
    """
    conexion = None

    try:
        conexion = obtener_conexion()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute(
            """
            SELECT
                p.id_producto,
                p.codigo_barras,
                p.nombre,
                p.descripcion,
                p.categoria,
                p.unidad_medida,
                p.stock_actual,
                p.stock_minimo,
                p.precio_compra,
                p.precio_venta,
                p.id_proveedor,
                pr.razon_social AS proveedor,
                p.estado,
                p.fecha_registro
            FROM productos p
            LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor
            WHERE p.nombre LIKE ? OR p.codigo_barras LIKE ?
            ORDER BY p.nombre;
            """,
            (f"%{termino}%", f"%{termino}%"),
        )
        return [_fila_a_diccionario(fila) for fila in cursor.fetchall()]
    except sqlite3.Error as error:
        print(f"Error al buscar productos: {error}")
        return []
    finally:
        if conexion:
            conexion.close()


def listar_productos():
    """
    Devuelve los productos en un DataFrame de Pandas.
    """
    conexion = None

    try:
        conexion = obtener_conexion()
        consulta = """
            SELECT
                p.id_producto,
                p.codigo_barras,
                p.nombre,
                p.descripcion,
                p.categoria,
                p.unidad_medida,
                p.stock_actual,
                p.stock_minimo,
                p.precio_compra,
                p.precio_venta,
                p.id_proveedor,
                pr.razon_social AS proveedor,
                p.estado,
                p.fecha_registro
            FROM productos p
            LEFT JOIN proveedores pr ON p.id_proveedor = pr.id_proveedor
            ORDER BY p.nombre;
        """
        return pd.read_sql_query(consulta, conexion)
    except sqlite3.Error as error:
        print(f"Error al listar productos: {error}")
        return pd.DataFrame()
    finally:
        if conexion:
            conexion.close()

