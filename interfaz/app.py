"""Interfaz web e integracion de modulos para Smart Warehouse.

Se implementa con la libreria estandar de Python para que pueda ejecutarse sin
instalar frameworks web adicionales. La interfaz solo reutiliza funciones ya
existentes de los modulos del repositorio.
"""

from __future__ import annotations

import html
import secrets
import sqlite3
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from database import inicializar_base_datos, obtener_conexion

COLORS = {
    "orange": "#F97316",
    "orange_hover": "#EA580C",
    "white": "#FFFFFF",
    "light": "#F3F4F6",
    "border": "#E5E7EB",
    "dark": "#374151",
    "muted": "#6B7280",
    "green": "#22C55E",
    "yellow": "#FACC15",
    "red": "#EF4444",
}

SESIONES = {}


def obtener_stock_general():
    from inventario import obtener_stock_general as funcion
    return funcion()


def registrar_entrada(*args, **kwargs):
    from inventario import registrar_entrada as funcion
    return funcion(*args, **kwargs)


def registrar_salida(*args, **kwargs):
    from inventario import registrar_salida as funcion
    return funcion(*args, **kwargs)


def exportar_a_pdf(*args, **kwargs):
    from pdf import exportar_a_pdf as funcion
    return funcion(*args, **kwargs)


def listar_productos():
    from productos import listar_productos as funcion
    return funcion()


def registrar_producto(*args, **kwargs):
    from productos import registrar_producto as funcion
    return funcion(*args, **kwargs)


def sugerir_cantidades_compra():
    from pronostico import sugerir_cantidades_compra as funcion
    return funcion()


def obtener_inventario_general():
    from reportes import obtener_inventario_general as funcion
    return funcion()


def productos_proximos_a_agotarse(*args, **kwargs):
    from reportes import productos_proximos_a_agotarse as funcion
    return funcion(*args, **kwargs)


def reporte_movimientos_filtrado(*args, **kwargs):
    from reportes import reporte_movimientos_filtrado as funcion
    return funcion(*args, **kwargs)

NAV_ITEMS = [
    ("/inicio", "Inicio"),
    ("/productos", "Productos"),
    ("/inventario", "Inventario"),
    ("/dashboard", "Dashboard"),
    ("/reportes", "Reportes"),
    ("/configuracion", "Configuración"),
]


class AuthService:
    """Valida empleados usando la tabla usuarios existente."""

    @staticmethod
    def autenticar(usuario: str, contrasena: str):
        conexion = None
        try:
            conexion = obtener_conexion()
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()
            cursor.execute(
                """
                SELECT id_usuario, nombres, apellidos, usuario, rol, estado
                FROM usuarios
                WHERE usuario = ? AND contrasena = ? AND LOWER(estado) = 'activo'
                """,
                (usuario.strip(), contrasena),
            )
            fila = cursor.fetchone()
            return dict(fila) if fila else None
        finally:
            if conexion:
                conexion.close()


def _escape(valor) -> str:
    return html.escape("" if valor is None else str(valor), quote=True)


def _tabla_html(dataframe) -> str:
    if dataframe is None or dataframe.empty:
        return '<div class="panel">No hay datos disponibles.</div>'
    return dataframe.to_html(index=False, classes="data-table", border=0, escape=True)


def _input(nombre: str, etiqueta: str, tipo: str = "text", requerido: bool = False) -> str:
    required = " required" if requerido else ""
    return f'<label>{_escape(etiqueta)}<input name="{_escape(nombre)}" type="{tipo}"{required}></label>'


def _base_html(contenido: str, usuario=None, activo: str = "") -> bytes:
    if usuario is None:
        cuerpo = f"""
        <main class="login-page">
            <section class="login-card">
                <h1 class="brand">Smart Warehouse</h1>
                <p class="subtitle">Inicio de sesión de empleados</p>
                {contenido}
            </section>
        </main>
        """
    else:
        enlaces = "".join(
            f'<a class="nav-link {"active" if ruta == activo else ""}" href="{ruta}">{label}</a>'
            for ruta, label in NAV_ITEMS
        )
        cuerpo = f"""
        <div class="layout">
            <aside class="sidebar">
                <div class="logo">SW</div>
                <div class="system-name">Smart Warehouse</div>
                {enlaces}
                <form method="post" action="/logout"><button class="logout-button" type="submit">Cerrar sesión</button></form>
            </aside>
            <main class="main">
                <header class="header">
                    <h1>Sistema inteligente de gestión de almacén</h1>
                    <div class="user">Usuario: {_escape(usuario['nombres'])} {_escape(usuario['apellidos'])} ({_escape(usuario['rol'])})</div>
                </header>
                <section class="content">{contenido}</section>
            </main>
        </div>
        """

    pagina = f"""
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Smart Warehouse</title>
        <style>
            :root {{ --orange:{COLORS['orange']}; --orange-hover:{COLORS['orange_hover']}; --white:{COLORS['white']}; --light:{COLORS['light']}; --border:{COLORS['border']}; --dark:{COLORS['dark']}; --muted:{COLORS['muted']}; --green:{COLORS['green']}; --yellow:{COLORS['yellow']}; --red:{COLORS['red']}; }}
            * {{ box-sizing: border-box; }}
            body {{ margin:0; min-height:100vh; background:var(--light); color:var(--dark); font-family:Inter, Segoe UI, Arial, sans-serif; }}
            a {{ color:inherit; text-decoration:none; }}
            .login-page {{ min-height:100vh; display:grid; place-items:center; padding:24px; background:linear-gradient(135deg,#fff7ed 0%,#f3f4f6 55%,#fff 100%); }}
            .login-card,.card,.panel {{ background:var(--white); border:1px solid var(--border); border-radius:22px; box-shadow:0 18px 45px rgba(17,24,39,.08); }}
            .login-card {{ width:min(430px,100%); padding:38px; text-align:center; }}
            .brand {{ color:var(--orange); font-size:32px; font-weight:800; margin:0 0 8px; }}
            .subtitle {{ color:var(--muted); margin:0 0 28px; }}
            .layout {{ display:grid; grid-template-columns:250px minmax(0,1fr); min-height:100vh; }}
            .sidebar {{ background:#111827; color:var(--white); padding:26px 18px; display:flex; flex-direction:column; gap:8px; }}
            .logo {{ color:var(--orange); font-size:34px; font-weight:900; text-align:center; }}
            .system-name {{ text-align:center; color:#e5e7eb; margin-bottom:22px; }}
            .nav-link,.logout-button,.button {{ border:0; border-radius:14px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center; font-weight:700; min-height:42px; padding:11px 16px; transition:.18s ease; }}
            .nav-link {{ justify-content:flex-start; color:var(--white); }}
            .nav-link:hover,.nav-link.active {{ background:#1f2937; }}
            .logout-button {{ margin-top:auto; background:var(--red); color:var(--white); width:100%; }}
            .button {{ background:var(--orange); color:var(--white); }}
            .button:hover {{ background:var(--orange-hover); transform:translateY(-1px); }}
            .button.success {{ background:var(--green); }}
            .header {{ min-height:76px; background:var(--white); border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; padding:18px 30px; gap:12px; }}
            .header h1 {{ font-size:22px; margin:0; }}
            .user {{ color:var(--muted); font-weight:600; }}
            .content {{ padding:28px; }}
            .page-title {{ font-size:28px; margin:0 0 18px; }}
            .cards {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin-bottom:18px; }}
            .card {{ padding:20px; }}
            .card-label {{ color:var(--muted); font-weight:700; margin-bottom:8px; }}
            .card-value {{ color:var(--orange); font-size:34px; font-weight:900; }}
            .panel {{ padding:18px; margin-bottom:18px; }}
            .form-grid {{ display:grid; grid-template-columns:repeat(5,minmax(140px,1fr)); gap:12px; align-items:end; }}
            input,select {{ width:100%; min-height:42px; border:1px solid var(--border); border-radius:12px; color:var(--dark); padding:0 12px; outline-color:var(--orange); }}
            label {{ color:var(--muted); display:grid; gap:6px; font-size:13px; font-weight:700; text-align:left; }}
            .table-wrap {{ overflow:auto; border-radius:16px; border:1px solid var(--border); background:var(--white); }}
            table {{ border-collapse:collapse; min-width:100%; }}
            th {{ background:var(--orange); color:var(--white); padding:12px; text-align:left; white-space:nowrap; }}
            td {{ border-top:1px solid var(--border); padding:11px 12px; white-space:nowrap; }}
            tr:nth-child(even) td {{ background:#fafafa; }}
            .flash {{ border-radius:14px; margin-bottom:14px; padding:12px 14px; font-weight:700; }}
            .flash.error {{ background:#fee2e2; color:#991b1b; }}
            .flash.success {{ background:#dcfce7; color:#166534; }}
            @media (max-width:900px) {{ .layout {{ grid-template-columns:1fr; }} .cards,.form-grid {{ grid-template-columns:1fr; }} .header {{ align-items:flex-start; flex-direction:column; }} }}
        </style>
    </head>
    <body>{cuerpo}</body>
    </html>
    """
    return pagina.encode("utf-8")


class SmartWarehouseHandler(BaseHTTPRequestHandler):
    """Controlador HTTP de la interfaz web."""

    def do_GET(self):
        ruta = urlparse(self.path).path
        usuario = self._usuario_actual()
        if ruta in ("/", "/login"):
            if usuario:
                self._redirect("/inicio")
            else:
                self._send(_base_html(self._login_form(), None))
            return
        if not usuario:
            self._redirect("/login")
            return
        rutas = {
            "/inicio": self._vista_inicio,
            "/productos": self._vista_productos,
            "/inventario": self._vista_inventario,
            "/dashboard": self._vista_dashboard,
            "/reportes": self._vista_reportes,
            "/configuracion": self._vista_configuracion,
        }
        vista = rutas.get(ruta)
        if vista is None:
            self._redirect("/inicio")
            return
        self._send(_base_html(vista(), usuario, ruta))

    def do_POST(self):
        ruta = urlparse(self.path).path
        datos = self._leer_formulario()
        if ruta == "/login":
            empleado = AuthService.autenticar(datos.get("usuario", ""), datos.get("contrasena", ""))
            if not empleado:
                self._send(_base_html(self._login_form("Credenciales inválidas o usuario inactivo."), None))
                return
            token = secrets.token_urlsafe(32)
            SESIONES[token] = empleado
            self._redirect("/inicio", token)
            return
        if ruta == "/logout":
            token = self._token_sesion()
            if token:
                SESIONES.pop(token, None)
            self._redirect("/login", limpiar_cookie=True)
            return
        usuario = self._usuario_actual()
        if not usuario:
            self._redirect("/login")
            return
        if ruta == "/productos":
            self._registrar_producto(datos)
            return
        if ruta == "/inventario":
            self._registrar_movimiento(datos, usuario)
            return
        if ruta == "/reportes":
            datos_reporte = obtener_inventario_general()
            ruta_pdf = exportar_a_pdf("reporte_inventario.pdf", "Reporte de inventario general", datos_reporte)
            self._send(_base_html(self._alerta(f"Archivo generado: {ruta_pdf}", "success") + self._vista_reportes(), usuario, "/reportes"))
            return
        self._redirect("/inicio")

    def _login_form(self, mensaje: str = "") -> str:
        alerta = self._alerta(mensaje, "error") if mensaje else ""
        return f"""
            {alerta}
            <form method="post" action="/login">
                <label>Usuario<input name="usuario" autocomplete="username" required></label><br>
                <label>Contraseña<input name="contrasena" type="password" autocomplete="current-password" required></label><br>
                <button class="button" type="submit" style="width:100%">Ingresar</button>
            </form>
        """

    def _vista_inicio(self) -> str:
        inventario_df = obtener_inventario_general()
        alertas_df = productos_proximos_a_agotarse()
        movimientos_df = reporte_movimientos_filtrado()
        return f"""
            <h2 class="page-title">Inicio</h2>
            <div class="cards">
                <article class="card"><div class="card-label">Productos</div><div class="card-value">{len(inventario_df)}</div></article>
                <article class="card"><div class="card-label">Alertas de stock</div><div class="card-value">{len(alertas_df)}</div></article>
                <article class="card"><div class="card-label">Movimientos</div><div class="card-value">{len(movimientos_df)}</div></article>
            </div>
            <div class="table-wrap">{_tabla_html(alertas_df.head(8))}</div>
        """

    def _vista_productos(self, mensaje: str = "", tipo: str = "success") -> str:
        campos = [
            "codigo_barras", "nombre", "descripcion", "categoria", "unidad_medida",
            "stock_actual", "stock_minimo", "precio_compra", "precio_venta", "id_proveedor",
        ]
        inputs = "".join(_input(campo, campo.replace("_", " ").title()) for campo in campos)
        return f"""
            <h2 class="page-title">Productos</h2>
            {self._alerta(mensaje, tipo) if mensaje else ""}
            <form class="panel form-grid" method="post" action="/productos">
                {inputs}
                <button class="button success" type="submit">Registrar producto</button>
            </form>
            <div class="table-wrap">{_tabla_html(listar_productos())}</div>
        """

    def _vista_inventario(self, mensaje: str = "", tipo: str = "success") -> str:
        return f"""
            <h2 class="page-title">Inventario</h2>
            {self._alerta(mensaje, tipo) if mensaje else ""}
            <form class="panel form-grid" method="post" action="/inventario">
                {_input("codigo_producto", "Código de barras", requerido=True)}
                {_input("cantidad", "Cantidad", "number", True)}
                {_input("descripcion", "Descripción")}
                <label>Movimiento<select name="tipo_movimiento"><option value="entrada">Entrada</option><option value="salida">Salida</option></select></label>
                <button class="button" type="submit">Registrar movimiento</button>
            </form>
            <div class="table-wrap">{_tabla_html(obtener_stock_general())}</div>
        """

    def _vista_dashboard(self) -> str:
        sugerencias_df = sugerir_cantidades_compra()
        alertas_df = productos_proximos_a_agotarse(2)
        return f"""
            <h2 class="page-title">Dashboard</h2>
            <div class="cards">
                <article class="card"><div class="card-label">Sugerencias de compra</div><div class="card-value">{len(sugerencias_df)}</div></article>
                <article class="card"><div class="card-label">Productos en alerta</div><div class="card-value">{len(alertas_df)}</div></article>
            </div>
            <div class="table-wrap">{_tabla_html(sugerencias_df)}</div>
        """

    def _vista_reportes(self) -> str:
        datos = obtener_inventario_general()
        return f"""
            <h2 class="page-title">Reportes</h2>
            <form class="panel" method="post" action="/reportes"><button class="button" type="submit">Exportar inventario a PDF</button></form>
            <div class="table-wrap">{_tabla_html(datos)}</div>
        """

    def _vista_configuracion(self) -> str:
        return '<h2 class="page-title">Configuración</h2><div class="panel">Módulo reservado para futuras preferencias del sistema.</div>'

    def _registrar_producto(self, datos):
        usuario = self._usuario_actual()
        try:
            id_proveedor = datos.get("id_proveedor", "").strip()
            exito, mensaje = registrar_producto(
                datos.get("codigo_barras", "").strip(),
                datos.get("nombre", "").strip(),
                datos.get("descripcion", "").strip(),
                datos.get("categoria", "").strip(),
                datos.get("unidad_medida", "").strip(),
                int(datos.get("stock_actual") or 0),
                int(datos.get("stock_minimo") or 0),
                float(datos.get("precio_compra") or 0),
                float(datos.get("precio_venta") or 0),
                int(id_proveedor) if id_proveedor else None,
            )
            tipo = "success" if exito else "error"
        except ValueError:
            mensaje = "Revise los campos numéricos del producto."
            tipo = "error"
        self._send(_base_html(self._vista_productos(mensaje, tipo), usuario, "/productos"))

    def _registrar_movimiento(self, datos, usuario):
        funcion = registrar_entrada if datos.get("tipo_movimiento") == "entrada" else registrar_salida
        mensaje = funcion(
            datos.get("codigo_producto", ""),
            datos.get("cantidad", ""),
            datos.get("descripcion", ""),
            usuario["id_usuario"],
        )
        tipo = "success" if mensaje.lower().startswith("exito") else "error"
        self._send(_base_html(self._vista_inventario(mensaje, tipo), usuario, "/inventario"))

    def _leer_formulario(self):
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo = self.rfile.read(longitud).decode("utf-8")
        return {clave: valores[0] for clave, valores in parse_qs(cuerpo).items()}

    def _token_sesion(self):
        header = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(header)
        if "sw_session" not in jar:
            return None
        return jar["sw_session"].value

    def _usuario_actual(self):
        token = self._token_sesion()
        return SESIONES.get(token) if token else None

    def _alerta(self, mensaje: str, tipo: str) -> str:
        return f'<div class="flash {_escape(tipo)}">{_escape(mensaje)}</div>'

    def _send(self, contenido: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def _redirect(self, ruta: str, token: str | None = None, limpiar_cookie: bool = False):
        self.send_response(303)
        self.send_header("Location", ruta)
        if token:
            self.send_header("Set-Cookie", f"sw_session={token}; HttpOnly; Path=/; SameSite=Lax")
        if limpiar_cookie:
            self.send_header("Set-Cookie", "sw_session=; Max-Age=0; Path=/; SameSite=Lax")
        self.end_headers()


def crear_servidor(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    """Crea el servidor web local de Smart Warehouse."""
    inicializar_base_datos()
    return ThreadingHTTPServer((host, port), SmartWarehouseHandler)


def ejecutar_app(host: str = "127.0.0.1", port: int = 8000):
    """Ejecuta la interfaz web local en http://127.0.0.1:8000."""
    servidor = crear_servidor(host, port)
    print(f"Interfaz web disponible en http://{host}:{port}")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
