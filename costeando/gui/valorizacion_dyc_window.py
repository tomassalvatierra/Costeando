import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Lógica de negocio original
from costeando.modulos.procesamiento_valorizacion_dyc import procesar_valorizacion_dyc_puro

logger = logging.getLogger(__name__)

class ValorizacionDYCWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        
        self.ruta_combinadas = tk.StringVar()
        self.ruta_dobles = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        
        self.campana_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        # Configuración del Grid
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TÍTULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Valorización de Dobles y Combinadas", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "• Lista: Debe tener la columna 'COSTO LISTA CXX'.\n"
            "• Dobles y Combinadas: Archivos originales."
        )
        lbl_desc = ctk.CTkLabel(
            self, 
            text=instrucciones,
            justify="left",
            text_color="gray70",
            font=("Roboto", 12)
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        # --- SELECTORES DE ARCHIVOS ---
        archivos_config = [
            ("Seleccionar Dobles", self.ruta_dobles),
            ("Seleccionar Combinadas", self.ruta_combinadas),
            ("Seleccionar Listado", self.ruta_listado)
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        # --- INPUTS DE CAMPAÑA Y AÑO ---
        last_row = base_row + len(archivos_config)
        
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # Campaña
        ctk.CTkLabel(frame_datos, text="Campaña (CC):").pack(side="left", padx=(0, 10))
        self.entry_campaña = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.campana_var,
            width=80, 
            placeholder_text="Ej: 05"
        )
        self.entry_campaña.pack(side="left", padx=(0, 30))

        # Año
        ctk.CTkLabel(frame_datos, text="Año (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_año = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.anio_var,
            width=80, 
            placeholder_text="Ej: 2024"
        )
        self.entry_año.pack(side="left")

        # --- BARRA DE PROGRESO ---
        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        self.progress_bar.grid(row=last_row + 1, column=0, columnspan=3, padx=20, pady=(10, 10), sticky='ew')
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        # --- BOTÓN PROCESAR ---
        self.btn_procesar = ctk.CTkButton(
            self, 
            text='INICIAR PROCESO', 
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870"
        )
        self.btn_procesar.grid(row=last_row + 2, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        """Helper para crear filas de selección"""
        btn = ctk.CTkButton(
            self, 
            text=texto_boton, 
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=200,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")

    def seleccionar_archivo(self, variable, titulo):
        archivo = filedialog.askopenfilename(title=titulo, filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            variable.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid()
        self.progress_bar.start()
        self.btn_procesar.configure(state="disabled", text="Procesando...")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")

    def ejecutar_hilo(self):
        # Validación UI
        if not self.campana_var.get() or not self.anio_var.get():
             messagebox.showerror("Error", "Campaña y Año son obligatorios.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_datos_dyc()
        except Exception as e:
            logger.error(f"Error en valorización DyC: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}"))
            self.after(0, self.ocultar_progreso)

    def procesar_datos_dyc(self):
        # 1. Obtener Datos
        campaña = self.campana_var.get()
        año = self.anio_var.get()
        listado = self.ruta_listado.get()
        combinadas = self.ruta_combinadas.get()
        dobles = self.ruta_dobles.get()

        if not all([listado, combinadas, dobles]):
            self.after(0, lambda: messagebox.showerror("Error", "Todos los archivos son obligatorios."))
            self.after(0, self.ocultar_progreso)
            return

        # 2. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Procesar
            procesar_valorizacion_dyc_puro(
                ruta_listado=listado,
                ruta_combinadas=combinadas,
                ruta_dobles=dobles,
                campana=campaña,
                anio=año,
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito."))
            
        except Exception as e:
            logger.error(f"Error lógica DyC: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error:\n{e}"))
            self.after(0, self.ocultar_progreso)