"""
Interfaz web con Streamlit para Smart Warehouse.

La app reutiliza la logica existente de base de datos, productos, inventario,
pronosticos y reportes PDF sin modificar sus reglas de negocio.
"""

from pathlib import Path
import sqlite3
import tempfile

import pandas as pd
import streamlit as st

from database import inicializar_base_datos, obtener_conexion
from inventario import obtener_stock_general, registrar_entrada, registrar_salida
from pdf import exportar_a_pdf
from productos import listar_productos, registrar_producto
from pronostico import sugerir_cantidades_compra
from reportes import obtener_inventario_general, productos_proximos_a_agotarse


st.set_page_config(
    page_title="Smart Warehouse",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def preparar_sistema():
    """Inicializa la base y asegura un usuario operativo para movimientos."""
    inicializar_base_datos()
    conexion = obtener_conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id_usuario FROM usuarios ORDER BY id_usuario ASC LIMIT 1;")
        usuario = cursor.fetchone()
        if usuario:
            return usuario[0]

        cursor.execute(
            """
            INSERT INTO usuarios (
                tipo_documento,
                numero_documento,
                nombres,
                apellidos,
                correo,
                usuario,
                contrasena,
                rol
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "DNI",
                "00000000",
                "Usuario",
                "Sistema",
                "sistema@smartwarehouse.local",
                "sistema",
                "smartwarehouse",
                "administrador",
            ),
        )
        conexion.commit()
        return cursor.lastrowid
    except sqlite3.Error:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def mostrar_dataframe(df: pd.DataFrame, mensaje_vacio: str, **kwargs):
    if df.empty:
        st.info(mensaje_vacio)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def columna_numerica(df: pd.DataFrame, columna: str) -> pd.Series:
    """Devuelve una columna numerica segura aunque el DataFrame venga vacio."""
    if df.empty or columna not in df.columns:
        return pd.Series(dtype="float64")

    return pd.to_numeric(df[columna], errors="coerce").fillna(0)


def formatear_moneda(valor: float) -> str:
    return f"S/ {valor:,.2f}"


def obtener_pdf_descarga(nombre_archivo: str, titulo: str, dataframe: pd.DataFrame) -> bytes:
    with tempfile.TemporaryDirectory() as carpeta_temporal:
        ruta = Path(carpeta_temporal) / nombre_archivo
        ruta_pdf = exportar_a_pdf(str(ruta), titulo, dataframe)
        return Path(ruta_pdf).read_bytes()


def calcular_abc(productos: pd.DataFrame, stock: pd.DataFrame) -> pd.DataFrame:
    columnas_abc = [
        "codigo_barras",
        "nombre",
        "categoria",
        "unidades_vendidas",
        "precio_venta",
        "valor_ventas",
        "porcentaje",
        "porcentaje_acumulado",
        "clase_abc",
    ]

    if productos.empty:
        return pd.DataFrame(columns=columnas_abc)

    abc = productos.copy()

    if not stock.empty and {"codigo_barras", "salidas"}.issubset(stock.columns):
        ventas = stock[["codigo_barras", "salidas"]]
        abc = abc.merge(ventas, on="codigo_barras", how="left")
    else:
        abc["salidas"] = 0

    abc["unidades_vendidas"] = columna_numerica(abc, "salidas")
    abc["precio_venta"] = columna_numerica(abc, "precio_venta")
    abc["valor_ventas"] = abc["unidades_vendidas"] * abc["precio_venta"]
    abc = abc.sort_values("valor_ventas", ascending=False)
    total = abc["valor_ventas"].sum()
    abc["porcentaje"] = 0 if total == 0 else abc["valor_ventas"] / total * 100
    abc["porcentaje_acumulado"] = abc["porcentaje"].cumsum()
    abc["clase_abc"] = abc["porcentaje_acumulado"].apply(
        lambda valor: "A" if valor <= 80 else "B" if valor <= 95 else "C"
    )
    if total == 0:
        abc["clase_abc"] = "Sin ventas"
    return abc[columnas_abc]


def pagina_dashboard():
    st.title("📊 Dashboard")
    productos = listar_productos()
    stock = obtener_stock_general()
    sugerencias = sugerir_cantidades_compra()
    alertas = productos_proximos_a_agotarse()

    total_productos = len(productos)
    stock_actual = columna_numerica(productos, "stock_actual")
    precio_compra = columna_numerica(productos, "precio_compra")
    demanda_pronosticada = columna_numerica(sugerencias, "demanda_pronosticada")
    stock_total = int(stock_actual.sum())
    valor_inventario = (stock_actual * precio_compra).sum()
    venta_estimada = demanda_pronosticada.sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Productos", total_productos)
    col2.metric("🏷️ Stock total", stock_total)
    col3.metric("💰 Valor inventario", formatear_moneda(valor_inventario))
    col4.metric("📈 Venta estimada", f"{venta_estimada:,.0f} uds")

    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("📋 Stock general")
        mostrar_dataframe(stock, "Todavia no hay productos para mostrar.")
    with derecha:
        st.subheader("⚠️ Por agotarse")
        mostrar_dataframe(alertas, "No hay productos con alerta de stock.")


def pagina_productos():
    st.title("🧾 Productos")
    with st.form("form_producto", clear_on_submit=True):
        st.subheader("➕ Agregar producto")
        col1, col2 = st.columns(2)
        codigo = col1.text_input("Codigo de barras *")
        nombre = col2.text_input("Nombre *")
        descripcion = st.text_area("Descripcion")
        col3, col4, col5 = st.columns(3)
        categoria = col3.text_input("Categoria")
        unidad = col4.text_input("Unidad de medida *", value="unidad")
        proveedor = col5.number_input("ID proveedor (opcional)", min_value=0, step=1)
        col6, col7, col8, col9 = st.columns(4)
        stock_actual = col6.number_input("Stock actual", min_value=0, step=1)
        stock_minimo = col7.number_input("Stock minimo", min_value=0, step=1)
        precio_compra = col8.number_input("Precio compra", min_value=0.0, step=0.1, format="%.2f")
        precio_venta = col9.number_input("Precio venta", min_value=0.0, step=0.1, format="%.2f")
        enviar = st.form_submit_button("Guardar producto")

    if enviar:
        if not codigo.strip() or not nombre.strip() or not unidad.strip():
            st.error("Completa codigo, nombre y unidad de medida.")
        else:
            exito, mensaje = registrar_producto(
                codigo.strip(), nombre.strip(), descripcion.strip(), categoria.strip(), unidad.strip(),
                int(stock_actual), int(stock_minimo), float(precio_compra), float(precio_venta),
                int(proveedor) if proveedor else None,
            )
            st.success(mensaje) if exito else st.error(mensaje)

    st.subheader("📚 Productos registrados")
    mostrar_dataframe(listar_productos(), "No hay productos registrados.")


def pagina_movimientos(id_usuario):
    st.title("🔄 Movimientos")
    productos = listar_productos()
    if productos.empty:
        st.warning("Registra al menos un producto antes de crear movimientos.")
        return

    opciones = {f"{fila.nombre} ({fila.codigo_barras})": fila.codigo_barras for fila in productos.itertuples()}
    with st.form("form_movimiento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        producto = col1.selectbox("Producto", list(opciones.keys()))
        tipo = col2.radio("Tipo", ["Entrada", "Salida"], horizontal=True)
        col3, col4 = st.columns([1, 2])
        cantidad = col3.number_input("Cantidad", min_value=1, step=1)
        motivo = col4.text_input("Motivo / observacion")
        enviar = st.form_submit_button("Registrar movimiento")

    if enviar:
        funcion = registrar_entrada if tipo == "Entrada" else registrar_salida
        mensaje = funcion(opciones[producto], int(cantidad), motivo, id_usuario=id_usuario)
        st.success(mensaje) if mensaje.lower().startswith("exito") else st.error(mensaje)

    st.subheader("📋 Stock actualizado")
    mostrar_dataframe(obtener_stock_general(), "No hay stock para mostrar.")


def pagina_abc():
    st.title("🏆 Análisis ABC")
    abc = calcular_abc(listar_productos(), obtener_stock_general())
    mostrar_dataframe(abc, "No hay productos para clasificar.")
    if not abc.empty:
        st.subheader("📊 Ventas por producto")
        st.bar_chart(abc.set_index("nombre")["valor_ventas"])


def pagina_reportes():
    st.title("📄 Reportes")
    inventario = obtener_inventario_general()
    sugerencias = sugerir_cantidades_compra()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Inventario general")
        mostrar_dataframe(inventario, "No hay inventario disponible.")
        st.download_button(
            "Descargar inventario PDF",
            data=obtener_pdf_descarga("inventario_general.pdf", "Inventario general", inventario),
            file_name="inventario_general.pdf",
            mime="application/pdf",
        )
    with col2:
        st.subheader("🛒 Sugerencias de compra")
        mostrar_dataframe(sugerencias, "No hay sugerencias disponibles.")
        st.download_button(
            "Descargar sugerencias PDF",
            data=obtener_pdf_descarga("sugerencias_compra.pdf", "Sugerencias de compra", sugerencias),
            file_name="sugerencias_compra.pdf",
            mime="application/pdf",
        )


def main():
    id_usuario = preparar_sistema()
    st.sidebar.title("🏬 Smart Warehouse")
    pagina = st.sidebar.radio(
        "Menu",
        ["Dashboard", "Productos", "Movimientos", "Análisis ABC", "Reportes"],
    )
    st.sidebar.caption("Sistema listo para usarse. La base de datos se crea automaticamente si no existe.")

    if pagina == "Dashboard":
        pagina_dashboard()
    elif pagina == "Productos":
        pagina_productos()
    elif pagina == "Movimientos":
        pagina_movimientos(id_usuario)
    elif pagina == "Análisis ABC":
        pagina_abc()
    else:
        pagina_reportes()


if __name__ == "__main__":
    main()
