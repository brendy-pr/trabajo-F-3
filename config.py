"""
Configuracion global del sistema de gestion de almacen.

Este modulo centraliza valores compartidos para que otros archivos del
proyecto puedan importarlos sin repetir rutas o nombres de recursos.
"""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE_NAME = "almacen.db"
DATABASE_PATH = BASE_DIR / DATABASE_NAME

