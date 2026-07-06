"""
Interfaz Streamlit para Smart Warehouse.

La app integra los modulos existentes de base de datos, productos, inventario,
pronostico y reportes sin modificar su logica de negocio.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile

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
    """Inicializa la base de datos y asegura un usuario operativo para movimientos."""
    inicializar_base_datos()
    with obtener_conexion() as conexion:
        conexion.execute(
            """
            INSERT OR IGNORE INTO usuarios (
                tipo_documento,
                numero_documento,
                nombres,
                apellidos,
                correo,
                usuario,
                contrasena,
                rol,
                estado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "DNI",
                "00000000",
                "Usuario",
                "Sistema",
                "sistema@smartwarehouse.local",
                "sistema",
                "sistema",
                "administrador",
                "activo",
            ),
        )
        conexion.commit()
    return True


def formatear_moneda(valor):
    return f"S/ {float(valor or 0):,.2f}"


def cargar_productos():
    return listar_productos()


def calcular_metricas_dashboard(productos):
    if productos.empty:
        return 0, 0, 0.0, 0.0

    stock_total = pd.to_numeric(productos["stock_actual"], errors="coerce").fillna(0).sum()
    precios = pd.to_numeric(productos["precio_compra"], errors="coerce").fillna(0)
    valor_inventario = (pd.to_numeric(productos["stock_actual"], errors="coerce").fillna(0) * precios).sum()
    sugerencias = sugerir_cantidades_compra()
    venta_estimada = 0.0
    if not sugerencias.empty:
        venta_estimada = pd.to_numeric(
            sugerencias["demanda_pronosticada"], errors="coerce"
        ).fillna(0).sum()
    return len(productos), int(stock_total), float(valor_inventario), float(venta_estimada)


def obtener_abc():
    with obtener_conexion() as conexion:
        consulta = """
            SELECT
                p.codigo_barras,
                p.nombre,
                p.categoria,
                COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'salida' THEN m.cantidad ELSE 0 END), 0) AS unidades_vendidas,
                COALESCE(SUM(CASE WHEN LOWER(m.tipo_movimiento) = 'salida' THEN m.cantidad * p.precio_venta ELSE 0 END), 0) AS valor_vendido
            FROM productos p
            LEFT JOIN movimientos m ON p.id_producto = m.id_producto
            GROUP BY p.id_producto, p.codigo_barras, p.nombre, p.categoria
            ORDER BY valor_vendido DESC, unidades_vendidas DESC, p.nombre ASC;
        """
        abc = pd.read_sql_query(consulta, conexion)

    if abc.empty:
        return abc

    total = float(pd.to_numeric(abc["valor_vendido"], errors="coerce").fillna(0).sum())
    if total <= 0:
        abc["porcentaje"] = 0.0
        abc["porcentaje_acumulado"] = 0.0
        abc["clasificacion_abc"] = "C"
        return abc

    abc["porcentaje"] = abc["valor_vendido"] / total * 100
    abc["porcentaje_acumulado"] = abc["porcentaje"].cumsum()
    abc["clasificacion_abc"] = abc["porcentaje_acumulado"].apply(
        lambda porcentaje: "A" if porcentaje <= 80 else ("B" if porcentaje <= 95 else "C")
    )
    return abc


def crear_pdf_descargable(titulo, dataframe):
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temporal:
        ruta = Path(temporal.name)
    ruta_generada = Path(exportar_a_pdf(str(ruta), titulo, dataframe))
    datos = ruta_generada.read_bytes()
    ruta_generada.unlink(missing_ok=True)
    return datos


def mostrar_dashboard():
    st.header("📊 Dashboard")
    productos = cargar_productos()
    cantidad_productos, stock_total, valor_inventario, venta_estimada = calcular_metricas_dashboard(productos)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Productos registrados", cantidad_productos)
    col2.metric("Stock total", stock_total)
    col3.metric("Valor de inventario", formatear_moneda(valor_inventario))
    col4.metric("Venta estimada", f"{venta_estimada:,.0f} unidades")

    st.divider()
    col_stock, col_alertas = st.columns(2)
    with col_stock:
        st.subheader("📦 Stock general")
        stock_general = obtener_stock_general()
        st.dataframe(stock_general, use_container_width=True, hide_index=True)
    with col_alertas:
        st.subheader("⚠️ Por agotarse")
        alertas = productos_proximos_a_agotarse()
        if alertas.empty:
            st.success("No hay productos por debajo del stock mínimo.")
        else:
            st.dataframe(alertas, use_container_width=True, hide_index=True)


def mostrar_productos():
    st.header("🧾 Productos")
    with st.form("form_producto", clear_on_submit=True):
        st.subheader("➕ Agregar producto")
        col1, col2 = st.columns(2)
        codigo = col1.text_input("Código de barras *")
        nombre = col2.text_input("Nombre *")
        descripcion = st.text_area("Descripción")
        col3, col4, col5 = st.columns(3)
        categoria = col3.text_input("Categoría")
        unidad = col4.text_input("Unidad de medida *", value="unidad")
        stock_actual = col5.number_input("Stock actual", min_value=0, step=1)
        col6, col7, col8 = st.columns(3)
        stock_minimo = col6.number_input("Stock mínimo", min_value=0, step=1)
        precio_compra = col7.number_input("Precio compra", min_value=0.0, step=0.1, format="%.2f")
        precio_venta = col8.number_input("Precio venta", min_value=0.0, step=0.1, format="%.2f")
        enviado = st.form_submit_button("Guardar producto", type="primary")

    if enviado:
        if not codigo.strip() or not nombre.strip() or not unidad.strip():
            st.error("Completa los campos obligatorios: código, nombre y unidad de medida.")
        else:
            exito, mensaje = registrar_producto(
                codigo.strip(), nombre.strip(), descripcion.strip(), categoria.strip(), unidad.strip(),
                int(stock_actual), int(stock_minimo), float(precio_compra), float(precio_venta)
            )
            st.success(mensaje) if exito else st.error(mensaje)

    st.subheader("📋 Productos registrados")
    st.dataframe(cargar_productos(), use_container_width=True, hide_index=True)


def mostrar_movimientos():
    st.header("🔄 Movimientos")
    productos = cargar_productos()
    if productos.empty:
        st.info("Registra productos antes de crear movimientos.")
        return

    opciones = {f"{fila.nombre} ({fila.codigo_barras})": fila.codigo_barras for fila in productos.itertuples()}
    with st.form("form_movimiento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        producto_label = col1.selectbox("Producto", list(opciones.keys()))
        tipo = col2.radio("Tipo de movimiento", ["Entrada", "Salida"], horizontal=True)
        col3, col4 = st.columns([1, 2])
        cantidad = col3.number_input("Cantidad", min_value=1, step=1)
        motivo = col4.text_input("Motivo / observación")
        enviado = st.form_submit_button("Registrar movimiento", type="primary")

    if enviado:
        codigo = opciones[producto_label]
        mensaje = registrar_entrada(codigo, int(cantidad), motivo) if tipo == "Entrada" else registrar_salida(codigo, int(cantidad), motivo)
        st.success(mensaje) if mensaje.startswith("Exito") else st.error(mensaje)

    st.subheader("🧮 Stock actualizado")
    st.dataframe(obtener_stock_general(), use_container_width=True, hide_index=True)


def mostrar_abc():
    st.header("🏷️ Análisis ABC")
    abc = obtener_abc()
    if abc.empty:
        st.info("No hay productos para clasificar.")
        return
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(abc, use_container_width=True, hide_index=True)
    with col2:
        resumen = abc.groupby("clasificacion_abc", as_index=False)["valor_vendido"].sum()
        st.bar_chart(resumen, x="clasificacion_abc", y="valor_vendido")


def mostrar_reportes():
    st.header("📄 Reportes")
    inventario = obtener_inventario_general()
    sugerencias = sugerir_cantidades_compra()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📦 Inventario general")
        st.dataframe(inventario, use_container_width=True, hide_index=True)
        st.download_button("Descargar inventario PDF", crear_pdf_descargable("Inventario general", inventario), "inventario_general.pdf", "application/pdf")
    with col2:
        st.subheader("🛒 Sugerencias de compra")
        st.dataframe(sugerencias, use_container_width=True, hide_index=True)
        st.download_button("Descargar sugerencias PDF", crear_pdf_descargable("Sugerencias de compra", sugerencias), "sugerencias_compra.pdf", "application/pdf")


preparar_sistema()
st.sidebar.title("🏭 Smart Warehouse")
st.sidebar.caption("Sistema inteligente de gestión de almacén")
opcion = st.sidebar.radio(
    "Menú",
    ["Dashboard", "Productos", "Movimientos", "Análisis ABC", "Reportes"],
)

if opcion == "Dashboard":
    mostrar_dashboard()
elif opcion == "Productos":
    mostrar_productos()
elif opcion == "Movimientos":
    mostrar_movimientos()
elif opcion == "Análisis ABC":
    mostrar_abc()
else:
    mostrar_reportes()
