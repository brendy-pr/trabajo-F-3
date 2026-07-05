"""
Modulo de conexion e inicializacion de la base de datos SQLite.
"""

import sqlite3

from config import DATABASE_PATH


SCRIPT_CREACION_TABLAS = """
CREATE TABLE IF NOT EXISTS proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    ruc TEXT NOT NULL UNIQUE,
    razon_social TEXT NOT NULL,
    nombre_contacto TEXT,
    telefono TEXT,
    correo TEXT UNIQUE,
    direccion TEXT,
    estado TEXT NOT NULL DEFAULT 'activo',
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_documento TEXT NOT NULL,
    numero_documento TEXT NOT NULL UNIQUE,
    nombres TEXT NOT NULL,
    apellidos TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    usuario TEXT NOT NULL UNIQUE,
    contrasena TEXT NOT NULL,
    rol TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'activo',
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_barras TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria TEXT,
    unidad_medida TEXT NOT NULL,
    stock_actual INTEGER NOT NULL DEFAULT 0,
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    precio_compra REAL NOT NULL DEFAULT 0,
    precio_venta REAL NOT NULL DEFAULT 0,
    id_proveedor INTEGER,
    estado TEXT NOT NULL DEFAULT 'activo',
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_proveedor)
        REFERENCES proveedores(id_proveedor)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,
    tipo_movimiento TEXT NOT NULL,
    cantidad INTEGER NOT NULL,
    fecha_movimiento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    motivo TEXT,
    observacion TEXT,

    FOREIGN KEY (id_producto)
        REFERENCES productos(id_producto)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id_usuario)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
"""


def obtener_conexion():
    """
    Abre una conexion a SQLite y activa el soporte de llaves foraneas.
    """
    conexion = sqlite3.connect(DATABASE_PATH)
    conexion.execute("PRAGMA foreign_keys = ON;")
    return conexion


def inicializar_base_datos():
    """
    Crea las tablas principales del sistema si aun no existen.
    """
    conexion = None

    try:
        conexion = obtener_conexion()
        conexion.executescript(SCRIPT_CREACION_TABLAS)
        conexion.commit()
        print("Base de datos inicializada correctamente.")
    except sqlite3.Error as error:
        if conexion:
            conexion.rollback()
        print(f"Error al inicializar la base de datos: {error}")
    finally:
        if conexion:
            conexion.close()

