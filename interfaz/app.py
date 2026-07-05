"""Interfaz grafica moderna e integracion de modulos para Smart Warehouse."""

from __future__ import annotations

import sqlite3
from tkinter import messagebox, ttk

import customtkinter as ctk

from database import inicializar_base_datos, obtener_conexion
from inventario import obtener_stock_general, registrar_entrada, registrar_salida
from pdf import exportar_a_pdf
from productos import listar_productos, registrar_producto
from pronostico import sugerir_cantidades_compra
from reportes import obtener_inventario_general, productos_proximos_a_agotarse, reporte_movimientos_filtrado


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
    "red_hover": "#DC2626",
}


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


class SmartWarehouseApp(ctk.CTk):
    """Ventana principal unica con navegacion lateral y area de contenido dinamica."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("Smart Warehouse")
        self.geometry("1180x720")
        self.minsize(1024, 650)
        self.usuario_actual = None
        self._mostrar_login()

    def _limpiar_ventana(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _mostrar_login(self):
        self._limpiar_ventana()
        self.configure(fg_color=COLORS["light"])

        contenedor = ctk.CTkFrame(self, fg_color=COLORS["white"], corner_radius=24)
        contenedor.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            contenedor,
            text="Smart Warehouse",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=COLORS["orange"],
        ).pack(padx=70, pady=(42, 8))
        ctk.CTkLabel(
            contenedor,
            text="Inicio de sesion de empleados",
            font=ctk.CTkFont(size=15),
            text_color=COLORS["muted"],
        ).pack(pady=(0, 28))

        usuario_entry = ctk.CTkEntry(contenedor, width=330, height=42, placeholder_text="Usuario")
        usuario_entry.pack(padx=42, pady=8)
        contrasena_entry = ctk.CTkEntry(
            contenedor, width=330, height=42, placeholder_text="Contrasena", show="*"
        )
        contrasena_entry.pack(padx=42, pady=8)

        mensaje = ctk.CTkLabel(contenedor, text="", text_color=COLORS["red"])
        mensaje.pack(pady=(8, 0))

        def iniciar_sesion():
            empleado = AuthService.autenticar(usuario_entry.get(), contrasena_entry.get())
            if not empleado:
                mensaje.configure(text="Credenciales invalidas o usuario inactivo.")
                return
            self.usuario_actual = empleado
            self._mostrar_principal()

        ctk.CTkButton(
            contenedor,
            text="Ingresar",
            width=330,
            height=44,
            corner_radius=14,
            fg_color=COLORS["orange"],
            hover_color=COLORS["orange_hover"],
            command=iniciar_sesion,
        ).pack(padx=42, pady=(18, 42))
        self.bind("<Return>", lambda _event: iniciar_sesion())

    def _mostrar_principal(self):
        self._limpiar_ventana()
        self.configure(fg_color=COLORS["white"])
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#111827")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="SW",
            font=ctk.CTkFont(size=34, weight="bold"),
            text_color=COLORS["orange"],
        ).pack(pady=(28, 4))
        ctk.CTkLabel(sidebar, text="Smart Warehouse", text_color=COLORS["white"]).pack(pady=(0, 25))

        opciones = [
            ("Inicio", self._vista_inicio),
            ("Productos", self._vista_productos),
            ("Inventario", self._vista_inventario),
            ("Dashboard", self._vista_dashboard),
            ("Reportes", self._vista_reportes),
            ("Configuracion", self._vista_configuracion),
        ]
        for texto, comando in opciones:
            ctk.CTkButton(
                sidebar,
                text=texto,
                height=42,
                corner_radius=12,
                anchor="w",
                fg_color="transparent",
                hover_color="#1F2937",
                text_color=COLORS["white"],
                command=comando,
            ).pack(fill="x", padx=18, pady=5)

        ctk.CTkButton(
            sidebar,
            text="Cerrar sesion",
            height=42,
            corner_radius=12,
            fg_color=COLORS["red"],
            hover_color=COLORS["red_hover"],
            command=self._mostrar_login,
        ).pack(side="bottom", fill="x", padx=18, pady=24)

        self.header = ctk.CTkFrame(self, height=74, corner_radius=0, fg_color=COLORS["white"])
        self.header.grid(row=0, column=1, sticky="ew")
        nombre = f"{self.usuario_actual['nombres']} {self.usuario_actual['apellidos']}"
        ctk.CTkLabel(
            self.header,
            text="Sistema inteligente de gestion de almacen",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["dark"],
        ).pack(side="left", padx=28)
        ctk.CTkLabel(
            self.header,
            text=f"Usuario: {nombre} ({self.usuario_actual['rol']})",
            text_color=COLORS["muted"],
        ).pack(side="right", padx=28)

        self.main_area = ctk.CTkScrollableFrame(self, fg_color=COLORS["light"], corner_radius=0)
        self.main_area.grid(row=1, column=1, sticky="nsew")
        self._vista_inicio()

    def _clear_main(self, titulo: str):
        for widget in self.main_area.winfo_children():
            widget.destroy()
        ctk.CTkLabel(
            self.main_area,
            text=titulo,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLORS["dark"],
        ).pack(anchor="w", padx=28, pady=(24, 12))

    def _card(self, parent, titulo, valor, color=COLORS["orange"]):
        card = ctk.CTkFrame(parent, fg_color=COLORS["white"], corner_radius=18)
        card.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(card, text=titulo, text_color=COLORS["muted"]).pack(anchor="w", padx=18, pady=(16, 4))
        ctk.CTkLabel(card, text=str(valor), font=ctk.CTkFont(size=28, weight="bold"), text_color=color).pack(anchor="w", padx=18, pady=(0, 16))
        return card

    def _tabla(self, parent, dataframe, alto=12):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["white"], corner_radius=14)
        frame.pack(fill="both", expand=True, padx=28, pady=12)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["white"], fieldbackground=COLORS["white"], foreground=COLORS["dark"], rowheight=28)
        style.configure("Treeview.Heading", background=COLORS["orange"], foreground=COLORS["white"], font=("Arial", 10, "bold"))
        columnas = list(dataframe.columns) if dataframe is not None and not dataframe.empty else ["mensaje"]
        tabla = ttk.Treeview(frame, columns=columnas, show="headings", height=alto)
        for columna in columnas:
            tabla.heading(columna, text=columna)
            tabla.column(columna, width=130, anchor="w")
        if dataframe is None or dataframe.empty:
            tabla.insert("", "end", values=("No hay datos disponibles",))
        else:
            for _, fila in dataframe.iterrows():
                tabla.insert("", "end", values=[fila[col] for col in columnas])
        tabla.pack(fill="both", expand=True, padx=14, pady=14)
        return tabla

    def _vista_inicio(self):
        self._clear_main("Inicio")
        inventario = obtener_inventario_general()
        alertas = productos_proximos_a_agotarse()
        movimientos = reporte_movimientos_filtrado()
        fila = ctk.CTkFrame(self.main_area, fg_color="transparent")
        fila.pack(fill="x", padx=20)
        self._card(fila, "Productos", len(inventario), COLORS["orange"])
        self._card(fila, "Alertas de stock", len(alertas), COLORS["yellow"])
        self._card(fila, "Movimientos", len(movimientos), COLORS["green"])
        self._tabla(self.main_area, alertas.head(8), alto=8)

    def _vista_productos(self):
        self._clear_main("Productos")
        formulario = ctk.CTkFrame(self.main_area, fg_color=COLORS["white"], corner_radius=18)
        formulario.pack(fill="x", padx=28, pady=10)
        campos = ["codigo_barras", "nombre", "descripcion", "categoria", "unidad_medida", "stock_actual", "stock_minimo", "precio_compra", "precio_venta", "id_proveedor"]
        entradas = {}
        for i, campo in enumerate(campos):
            entrada = ctk.CTkEntry(formulario, placeholder_text=campo.replace("_", " "), width=180)
            entrada.grid(row=i // 5, column=i % 5, padx=10, pady=10, sticky="ew")
            entradas[campo] = entrada

        def guardar():
            try:
                datos = {campo: entradas[campo].get().strip() for campo in campos}
                exito, msg = registrar_producto(
                    datos["codigo_barras"], datos["nombre"], datos["descripcion"], datos["categoria"], datos["unidad_medida"],
                    int(datos["stock_actual"] or 0), int(datos["stock_minimo"] or 0), float(datos["precio_compra"] or 0), float(datos["precio_venta"] or 0),
                    int(datos["id_proveedor"]) if datos["id_proveedor"] else None,
                )
                messagebox.showinfo("Productos" if exito else "Aviso", msg)
                self._vista_productos()
            except ValueError:
                messagebox.showerror("Error", "Revise los campos numericos del producto.")

        ctk.CTkButton(formulario, text="Registrar producto", fg_color=COLORS["green"], hover_color="#16A34A", command=guardar).grid(row=2, column=0, padx=10, pady=12)
        self._tabla(self.main_area, listar_productos())

    def _vista_inventario(self):
        self._clear_main("Inventario")
        panel = ctk.CTkFrame(self.main_area, fg_color=COLORS["white"], corner_radius=18)
        panel.pack(fill="x", padx=28, pady=10)
        codigo = ctk.CTkEntry(panel, placeholder_text="Codigo de barras")
        cantidad = ctk.CTkEntry(panel, placeholder_text="Cantidad")
        descripcion = ctk.CTkEntry(panel, placeholder_text="Descripcion")
        codigo.pack(side="left", padx=10, pady=16)
        cantidad.pack(side="left", padx=10, pady=16)
        descripcion.pack(side="left", padx=10, pady=16)

        def mover(tipo):
            funcion = registrar_entrada if tipo == "entrada" else registrar_salida
            mensaje = funcion(codigo.get(), cantidad.get(), descripcion.get(), self.usuario_actual["id_usuario"])
            messagebox.showinfo("Inventario", mensaje)
            self._vista_inventario()

        ctk.CTkButton(panel, text="Entrada", fg_color=COLORS["green"], command=lambda: mover("entrada")).pack(side="left", padx=8)
        ctk.CTkButton(panel, text="Salida", fg_color=COLORS["orange"], command=lambda: mover("salida")).pack(side="left", padx=8)
        self._tabla(self.main_area, obtener_stock_general())

    def _vista_dashboard(self):
        self._clear_main("Dashboard")
        fila = ctk.CTkFrame(self.main_area, fg_color="transparent")
        fila.pack(fill="x", padx=20)
        sugerencias = sugerir_cantidades_compra()
        alertas = productos_proximos_a_agotarse(2)
        self._card(fila, "Sugerencias de compra", len(sugerencias), COLORS["orange"])
        self._card(fila, "Productos en alerta", len(alertas), COLORS["yellow"])
        self._tabla(self.main_area, sugerencias)

    def _vista_reportes(self):
        self._clear_main("Reportes")
        acciones = ctk.CTkFrame(self.main_area, fg_color=COLORS["white"], corner_radius=18)
        acciones.pack(fill="x", padx=28, pady=10)
        datos = obtener_inventario_general()

        def exportar():
            ruta = exportar_a_pdf("reporte_inventario.pdf", "Reporte de inventario general", datos)
            messagebox.showinfo("Reporte exportado", f"Archivo generado: {ruta}")

        ctk.CTkButton(acciones, text="Exportar inventario a PDF", fg_color=COLORS["orange"], command=exportar).pack(side="left", padx=14, pady=14)
        self._tabla(self.main_area, datos)

    def _vista_configuracion(self):
        self._clear_main("Configuracion")
        texto = "Modulo reservado para futuras preferencias del sistema. La configuracion actual usa config.py y la base SQLite existente."
        ctk.CTkLabel(self.main_area, text=texto, text_color=COLORS["dark"], wraplength=700).pack(anchor="w", padx=28, pady=16)


def ejecutar_app():
    inicializar_base_datos()
    app = SmartWarehouseApp()
    app.mainloop()
