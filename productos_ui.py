"""
Interfaz de consola para el modulo de productos.
"""

from productos import (
    buscar_producto,
    editar_producto,
    eliminar_producto,
    listar_productos,
    registrar_producto,
)


def _leer_texto(mensaje, obligatorio=True):
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("Este campo es obligatorio.")


def _leer_entero(mensaje, minimo=None, obligatorio=True):
    while True:
        valor = input(mensaje).strip()

        if not valor and not obligatorio:
            return None

        try:
            numero = int(valor)
            if minimo is not None and numero < minimo:
                print(f"Ingrese un numero mayor o igual a {minimo}.")
                continue
            return numero
        except ValueError:
            print("Ingrese un numero entero valido.")


def _leer_decimal(mensaje, minimo=None, obligatorio=True):
    while True:
        valor = input(mensaje).strip().replace(",", ".")

        if not valor and not obligatorio:
            return None

        try:
            numero = float(valor)
            if minimo is not None and numero < minimo:
                print(f"Ingrese un numero mayor o igual a {minimo}.")
                continue
            return numero
        except ValueError:
            print("Ingrese un numero decimal valido.")


def _leer_id_proveedor():
    return _leer_entero(
        "ID del proveedor (Enter si no aplica): ",
        minimo=1,
        obligatorio=False,
    )


def _mostrar_resultado(exito, mensaje):
    estado = "OK" if exito else "AVISO"
    print(f"\n[{estado}] {mensaje}")


def _mostrar_productos_encontrados(productos):
    if not productos:
        print("\nNo se encontraron productos.")
        return

    print("\nProductos encontrados:")
    for producto in productos:
        proveedor = producto["proveedor"] or "Sin proveedor"
        print(
            f"{producto['id_producto']} | {producto['codigo_barras']} | "
            f"{producto['nombre']} | Stock: {producto['stock_actual']} | "
            f"Proveedor: {proveedor}"
        )


def opcion_registrar_producto():
    print("\n=== Registrar producto ===")
    codigo_barras = _leer_texto("Codigo de barras: ")
    nombre = _leer_texto("Nombre: ")
    descripcion = _leer_texto("Descripcion (Enter para omitir): ", obligatorio=False)
    categoria = _leer_texto("Categoria (Enter para omitir): ", obligatorio=False)
    unidad_medida = _leer_texto("Unidad de medida: ")
    stock_actual = _leer_entero("Stock actual: ", minimo=0)
    stock_minimo = _leer_entero("Stock minimo: ", minimo=0)
    precio_compra = _leer_decimal("Precio de compra: ", minimo=0)
    precio_venta = _leer_decimal("Precio de venta: ", minimo=0)
    id_proveedor = _leer_id_proveedor()

    exito, mensaje = registrar_producto(
        codigo_barras=codigo_barras,
        nombre=nombre,
        descripcion=descripcion,
        categoria=categoria,
        unidad_medida=unidad_medida,
        stock_actual=stock_actual,
        stock_minimo=stock_minimo,
        precio_compra=precio_compra,
        precio_venta=precio_venta,
        id_proveedor=id_proveedor,
    )
    _mostrar_resultado(exito, mensaje)


def opcion_editar_producto():
    print("\n=== Editar producto ===")
    id_producto = _leer_entero("ID del producto a editar: ", minimo=1)

    print("Deje en blanco los campos que no desea modificar.")
    datos = {
        "codigo_barras": _leer_texto("Nuevo codigo de barras: ", obligatorio=False),
        "nombre": _leer_texto("Nuevo nombre: ", obligatorio=False),
        "descripcion": _leer_texto("Nueva descripcion: ", obligatorio=False),
        "categoria": _leer_texto("Nueva categoria: ", obligatorio=False),
        "unidad_medida": _leer_texto("Nueva unidad de medida: ", obligatorio=False),
        "stock_actual": _leer_entero(
            "Nuevo stock actual: ", minimo=0, obligatorio=False
        ),
        "stock_minimo": _leer_entero(
            "Nuevo stock minimo: ", minimo=0, obligatorio=False
        ),
        "precio_compra": _leer_decimal(
            "Nuevo precio de compra: ", minimo=0, obligatorio=False
        ),
        "precio_venta": _leer_decimal(
            "Nuevo precio de venta: ", minimo=0, obligatorio=False
        ),
        "id_proveedor": _leer_id_proveedor(),
        "estado": _leer_texto("Nuevo estado: ", obligatorio=False),
    }

    datos = {campo: valor for campo, valor in datos.items() if valor not in ("", None)}
    exito, mensaje = editar_producto(id_producto, **datos)
    _mostrar_resultado(exito, mensaje)


def opcion_eliminar_producto():
    print("\n=== Eliminar producto ===")
    id_producto = _leer_entero("ID del producto a eliminar: ", minimo=1)
    confirmacion = input("Confirme la eliminacion escribiendo SI: ").strip().upper()

    if confirmacion != "SI":
        print("Eliminacion cancelada.")
        return

    exito, mensaje = eliminar_producto(id_producto)
    _mostrar_resultado(exito, mensaje)


def opcion_buscar_producto():
    print("\n=== Buscar producto ===")
    termino = _leer_texto("Ingrese nombre o codigo de barras: ")
    productos = buscar_producto(termino)
    _mostrar_productos_encontrados(productos)


def opcion_listar_productos():
    print("\n=== Listar productos ===")
    dataframe = listar_productos()

    if dataframe.empty:
        print("No hay productos registrados.")
        return

    print(dataframe.to_string(index=False))


def mostrar_menu_productos():
    while True:
        print(
            """
=== Modulo de productos ===
1. Registrar producto
2. Editar producto
3. Eliminar producto
4. Buscar producto
5. Listar productos
0. Volver / salir
"""
        )
        opcion = input("Seleccione una opcion: ").strip()

        if opcion == "1":
            opcion_registrar_producto()
        elif opcion == "2":
            opcion_editar_producto()
        elif opcion == "3":
            opcion_eliminar_producto()
        elif opcion == "4":
            opcion_buscar_producto()
        elif opcion == "5":
            opcion_listar_productos()
        elif opcion == "0":
            print("Saliendo del modulo de productos.")
            break
        else:
            print("Opcion no valida. Intente nuevamente.")

