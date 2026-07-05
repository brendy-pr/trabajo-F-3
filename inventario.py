from datetime import date, datetime

import pandas as pd

from database import obtener_conexion


TIPO_ENTRADA = "entrada"
TIPO_SALIDA = "salida"
FORMATO_FECHA = "%Y-%m-%d %H:%M:%S"

COLUMNAS_MOVIMIENTOS = [
    "id_movimiento",
    "id_producto",
    "codigo_barras",
    "nombre",
    "tipo_movimiento",
    "cantidad",
    "fecha_movimiento",
    "motivo",
    "observacion",
    "id_usuario",
]

COLUMNAS_STOCK_GENERAL = [
    "codigo_barras",
    "nombre",
    "categoria",
    "entradas",
    "salidas",
    "stock_actual",
    "stock_minimo",
    "estado_stock",
]


def _fecha_actual():
    return datetime.now().strftime(FORMATO_FECHA)


def _normalizar_codigo(codigo_producto):
    if codigo_producto is None:
        return ""
    return str(codigo_producto).strip()


def _normalizar_texto(texto):
    if texto is None:
        return ""
    return str(texto).strip()


def _validar_cantidad(cantidad):
    try:
        if isinstance(cantidad, bool):
            return False, None, "La cantidad debe ser un numero mayor a cero."

        cantidad_validada = float(cantidad)

        if cantidad_validada <= 0:
            return False, None, "La cantidad debe ser mayor a cero."

        if not cantidad_validada.is_integer():
            return False, None, "La cantidad debe ser un numero entero."

        return True, int(cantidad_validada), ""
    except (TypeError, ValueError):
        return False, None, "La cantidad debe ser un numero valido."


def _activar_llaves_foraneas(conexion):
    conexion.execute("PRAGMA foreign_keys = ON")


def _obtener_producto_por_codigo(cursor, codigo_producto):
    cursor.execute(
        """
        SELECT
            id_producto,
            codigo_barras,
            nombre,
            categoria,
            stock_actual,
            stock_minimo
        FROM productos
        WHERE codigo_barras = ?
        """,
        (codigo_producto,),
    )
    return cursor.fetchone()


def _obtener_id_usuario(cursor, id_usuario=None):
    # id_usuario es obligatorio en movimientos, por eso se valida antes de insertar.
    if id_usuario not in (None, ""):
        cursor.execute(
            """
            SELECT id_usuario
            FROM usuarios
            WHERE id_usuario = ?
            """,
            (id_usuario,),
        )
        usuario = cursor.fetchone()

        if usuario:
            return usuario[0]

        raise ValueError("El usuario indicado no existe.")

    cursor.execute(
        """
        SELECT id_usuario
        FROM usuarios
        ORDER BY id_usuario ASC
        LIMIT 1
        """
    )
    usuario = cursor.fetchone()

    if not usuario:
        raise ValueError("No hay usuarios registrados para asociar el movimiento.")

    return usuario[0]


def _obtener_stock_producto(producto):
    stock_actual = producto[4]

    if stock_actual is None:
        return 0

    return int(stock_actual)


def _actualizar_stock(cursor, id_producto, nuevo_stock):
    cursor.execute(
        """
        UPDATE productos
        SET stock_actual = ?
        WHERE id_producto = ?
        """,
        (nuevo_stock, id_producto),
    )


def _insertar_movimiento(
    cursor,
    id_producto,
    tipo_movimiento,
    cantidad,
    motivo,
    observacion,
    id_usuario,
):
    cursor.execute(
        """
        INSERT INTO movimientos (
            id_producto,
            tipo_movimiento,
            cantidad,
            fecha_movimiento,
            motivo,
            observacion,
            id_usuario
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id_producto,
            tipo_movimiento,
            cantidad,
            _fecha_actual(),
            motivo,
            observacion,
            id_usuario,
        ),
    )


def _registrar_movimiento(codigo_producto, cantidad, descripcion, tipo_movimiento, id_usuario=None):
    conexion = None

    try:
        codigo_producto = _normalizar_codigo(codigo_producto)
        descripcion = _normalizar_texto(descripcion)

        if not codigo_producto:
            return "Error: Debe ingresar el codigo de barras del producto."

        cantidad_valida, cantidad_validada, mensaje = _validar_cantidad(cantidad)

        if not cantidad_valida:
            return f"Error: {mensaje}"

        conexion = obtener_conexion()
        _activar_llaves_foraneas(conexion)
        cursor = conexion.cursor()

        producto = _obtener_producto_por_codigo(cursor, codigo_producto)

        if not producto:
            return "Error: El producto no existe."

        usuario = _obtener_id_usuario(cursor, id_usuario)
        id_producto = producto[0]
        stock_actual = _obtener_stock_producto(producto)

        if tipo_movimiento == TIPO_ENTRADA:
            nuevo_stock = stock_actual + cantidad_validada
            motivo = "Entrada de mercaderia"
            mensaje_exito = "Exito: Entrada registrada correctamente."
        elif tipo_movimiento == TIPO_SALIDA:
            if stock_actual < cantidad_validada:
                return "Error: Stock insuficiente."

            nuevo_stock = stock_actual - cantidad_validada
            motivo = "Salida de producto"
            mensaje_exito = "Exito: Salida registrada correctamente."
        else:
            return "Error: Tipo de movimiento no valido."

        _insertar_movimiento(
            cursor,
            id_producto,
            tipo_movimiento,
            cantidad_validada,
            motivo,
            descripcion,
            usuario,
        )
        _actualizar_stock(cursor, id_producto, nuevo_stock)

        conexion.commit()
        return mensaje_exito
    except Exception as error:
        if conexion:
            conexion.rollback()
        return f"Error al registrar movimiento: {error}"
    finally:
        if conexion:
            conexion.close()


def _normalizar_fecha(fecha, es_inicio):
    if isinstance(fecha, datetime):
        return fecha.strftime(FORMATO_FECHA)

    if isinstance(fecha, date):
        hora = "00:00:00" if es_inicio else "23:59:59"
        return f"{fecha.strftime('%Y-%m-%d')} {hora}"

    texto_fecha = str(fecha).strip()

    if len(texto_fecha) == 10:
        datetime.strptime(texto_fecha, "%Y-%m-%d")
        hora = "00:00:00" if es_inicio else "23:59:59"
        return f"{texto_fecha} {hora}"

    datetime.strptime(texto_fecha, FORMATO_FECHA)
    return texto_fecha


def verificar_producto_existe(codigo_producto):
    conexion = None

    try:
        codigo_producto = _normalizar_codigo(codigo_producto)

        if not codigo_producto:
            print("Error: Debe ingresar el codigo de barras del producto.")
            return False

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        return _obtener_producto_por_codigo(cursor, codigo_producto) is not None
    except Exception as error:
        print(f"Error al verificar producto: {error}")
        return False
    finally:
        if conexion:
            conexion.close()


def registrar_entrada(codigo_producto, cantidad, descripcion="", id_usuario=None):
    return _registrar_movimiento(
        codigo_producto,
        cantidad,
        descripcion,
        TIPO_ENTRADA,
        id_usuario,
    )


def registrar_salida(codigo_producto, cantidad, descripcion="", id_usuario=None):
    return _registrar_movimiento(
        codigo_producto,
        cantidad,
        descripcion,
        TIPO_SALIDA,
        id_usuario,
    )


def calcular_stock_actual(codigo_producto):
    conexion = None

    try:
        codigo_producto = _normalizar_codigo(codigo_producto)

        if not codigo_producto:
            print("Error: Debe ingresar el codigo de barras del producto.")
            return 0

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        producto = _obtener_producto_por_codigo(cursor, codigo_producto)

        if not producto:
            print("Error: El producto no existe.")
            return 0

        return _obtener_stock_producto(producto)
    except Exception as error:
        print(f"Error al calcular stock actual: {error}")
        return 0
    finally:
        if conexion:
            conexion.close()


def validar_stock_disponible(codigo_producto, cantidad):
    try:
        cantidad_valida, cantidad_validada, mensaje = _validar_cantidad(cantidad)

        if not cantidad_valida:
            print(f"Error: {mensaje}")
            return False

        stock_actual = calcular_stock_actual(codigo_producto)

        if stock_actual < cantidad_validada:
            print("Error: Stock insuficiente.")
            return False

        return True
    except Exception as error:
        print(f"Error al validar stock disponible: {error}")
        return False


def listar_movimientos():
    conexion = None

    try:
        conexion = obtener_conexion()

        consulta = """
        SELECT
            m.id_movimiento,
            m.id_producto,
            p.codigo_barras,
            p.nombre,
            m.tipo_movimiento,
            m.cantidad,
            m.fecha_movimiento,
            m.motivo,
            m.observacion,
            m.id_usuario
        FROM movimientos m
        INNER JOIN productos p ON m.id_producto = p.id_producto
        ORDER BY m.fecha_movimiento DESC, m.id_movimiento DESC
        """

        return pd.read_sql_query(consulta, conexion)
    except Exception as error:
        print(f"Error al listar movimientos: {error}")
        return pd.DataFrame(columns=COLUMNAS_MOVIMIENTOS)
    finally:
        if conexion:
            conexion.close()


def buscar_movimientos_por_fecha(fecha_inicio, fecha_fin):
    conexion = None

    try:
        fecha_inicio = _normalizar_fecha(fecha_inicio, es_inicio=True)
        fecha_fin = _normalizar_fecha(fecha_fin, es_inicio=False)

        if fecha_inicio > fecha_fin:
            print("Error: La fecha de inicio no puede ser mayor que la fecha final.")
            return pd.DataFrame(columns=COLUMNAS_MOVIMIENTOS)

        conexion = obtener_conexion()

        consulta = """
        SELECT
            m.id_movimiento,
            m.id_producto,
            p.codigo_barras,
            p.nombre,
            m.tipo_movimiento,
            m.cantidad,
            m.fecha_movimiento,
            m.motivo,
            m.observacion,
            m.id_usuario
        FROM movimientos m
        INNER JOIN productos p ON m.id_producto = p.id_producto
        WHERE m.fecha_movimiento BETWEEN ? AND ?
        ORDER BY m.fecha_movimiento DESC, m.id_movimiento DESC
        """

        return pd.read_sql_query(consulta, conexion, params=(fecha_inicio, fecha_fin))
    except Exception as error:
        print(f"Error al buscar movimientos por fecha: {error}")
        return pd.DataFrame(columns=COLUMNAS_MOVIMIENTOS)
    finally:
        if conexion:
            conexion.close()


def obtener_stock_general():
    conexion = None

    try:
        conexion = obtener_conexion()

        consulta = """
        WITH resumen AS (
            SELECT
                id_producto,
                COALESCE(SUM(CASE WHEN LOWER(tipo_movimiento) = 'entrada' THEN cantidad ELSE 0 END), 0) AS entradas,
                COALESCE(SUM(CASE WHEN LOWER(tipo_movimiento) = 'salida' THEN cantidad ELSE 0 END), 0) AS salidas
            FROM movimientos
            GROUP BY id_producto
        )
        SELECT
            p.codigo_barras,
            p.nombre,
            p.categoria,
            COALESCE(r.entradas, 0) AS entradas,
            COALESCE(r.salidas, 0) AS salidas,
            COALESCE(p.stock_actual, 0) AS stock_actual,
            p.stock_minimo,
            CASE
                WHEN COALESCE(p.stock_actual, 0) = 0 THEN 'Sin stock'
                WHEN COALESCE(p.stock_actual, 0) > 0
                     AND COALESCE(p.stock_actual, 0) <= COALESCE(p.stock_minimo, 0)
                    THEN 'Bajo stock'
                ELSE 'Normal'
            END AS estado_stock
        FROM productos p
        LEFT JOIN resumen r ON p.id_producto = r.id_producto
        ORDER BY p.nombre ASC
        """

        return pd.read_sql_query(consulta, conexion)
    except Exception as error:
        print(f"Error al obtener stock general: {error}")
        return pd.DataFrame(columns=COLUMNAS_STOCK_GENERAL)
    finally:
        if conexion:
            conexion.close()


if __name__ == "__main__":
    print("Modulo de inventario listo para integrarse con Smart Warehouse.")
