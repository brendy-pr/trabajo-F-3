"""
Archivo principal del sistema de gestion de almacen.
"""

from database import inicializar_base_datos
from productos_ui import mostrar_menu_productos


def main():
    inicializar_base_datos()

    while True:
        print(
            """
=== Sistema inteligente de gestion de almacen ===
1. Gestion de productos
0. Salir
"""
        )
        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "1":
            mostrar_menu_productos()
        elif opcion == "0":
            print("Gracias por usar el sistema.")
            break
        else:
            print("Opcion no valida. Intente nuevamente.")


if __name__ == "__main__":
    main()

