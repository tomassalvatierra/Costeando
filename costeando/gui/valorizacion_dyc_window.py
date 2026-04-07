import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

from costeando.modulos.procesamiento_valorizacion_dyc import procesar_valorizacion_dyc_puro
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


class ValorizacionDYCWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.ruta_listado = tk.StringVar()
        self.ruta_combinadas = tk.StringVar()
        self.ruta_dobles = tk.StringVar()
        self.campana_var = tk.StringVar()
        self.anio_var = tk.StringVar()
        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="Valorizacion de Dobles y Combinadas",
            font=("Roboto", 24, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        instrucciones = (
            "- Listado: Archivo de costos con columna 'COSTO LISTA'.\n"
            "- Combinadas y Dobles: Archivos originales para valorizacion."
        )
        lbl_desc = ctk.CTkLabel(self, text=instrucciones, justify="left", text_color="gray70", font=("Roboto", 12))
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        self.crear_fila_selector(2, "Seleccionar Listado", self.ruta_listado)
        self.crear_fila_selector(3, "Seleccionar Combinadas", self.ruta_combinadas)
        self.crear_fila_selector(4, "Seleccionar Dobles", self.ruta_dobles)

        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=5, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(frame_datos, text="Campaña (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(frame_datos, textvariable=self.campana_var, width=80, placeholder_text="Ej: 05")
        self.entry_campania.pack(side="left", padx=(0, 30))

        ctk.CTkLabel(frame_datos, text="Año (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_anio = ctk.CTkEntry(frame_datos, textvariable=self.anio_var, width=80, placeholder_text="Ej: 2024")
        self.entry_anio.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.grid(row=6, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        self.btn_procesar = ctk.CTkButton(
            self,
            text="INICIAR PROCESO",
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_procesar.grid(row=7, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        btn = ctk.CTkButton(
            self,
            text=texto_boton,
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=220,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
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
        if not self.campana_var.get() or not self.anio_var.get():
            messagebox.showerror("Error", "Debe completar campaña y año.")
            return
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_datos_dyc()
        except Exception as error:
            logger.error("Error en valorizacion DYC: %s", str(error), exc_info=True)
            self.after(0, lambda: mostrar_error_legible(error))
            self.after(0, self.ocultar_progreso)

    def procesar_datos_dyc(self):
        ruta_listado = self.ruta_listado.get()
        ruta_combinadas = self.ruta_combinadas.get()
        ruta_dobles = self.ruta_dobles.get()
        campana = self.campana_var.get().zfill(2)
        anio = self.anio_var.get()

        if not all([ruta_listado, ruta_combinadas, ruta_dobles]):
            self.after(0, lambda: messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos."))
            self.after(0, self.ocultar_progreso)
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            procesar_valorizacion_dyc_puro(
                ruta_listado=ruta_listado,
                ruta_combinadas=ruta_combinadas,
                ruta_dobles=ruta_dobles,
                campana=campana,
                anio=anio,
                carpeta_guardado=carpeta_guardado,
            )
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Exito", "El procesamiento finalizo con exito."))
        except Exception as error:
            logger.error("Error en logica valorizacion DYC: %s", str(error), exc_info=True)
            self.after(0, lambda: mostrar_error_legible(error))
            self.after(0, self.ocultar_progreso)
