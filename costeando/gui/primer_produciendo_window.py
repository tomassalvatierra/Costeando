import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Logica de negocio original
from costeando.modulos.procesamiento_primer_produciendo import procesar_primer_produciendo
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)

class PrimerProduciendoWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # --- Variables de Archivo ---
        self.ruta_maestro_produciendo = tk.StringVar()
        self.ruta_produciendo_anterior = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        self.ruta_descuentos_especiales = tk.StringVar()
        self.ruta_rotacion = tk.StringVar()
        self.ruta_estructuras = tk.StringVar()
        
        # --- Variables de ParA'AAmetros ---
        self.campania_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        # ConfiguraciA'AAn del Grid
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TA'AATULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Primer Produciendo", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "AAAasAAA Maestro: Original TOTVS (CA'AAdigo numA'AArico, sin espacios).\n"
            "AAAasAAA Produciendo: Archivo produciendo (N-1).\n"
            "AAAasAAA Stock: Informe 'Stock Actual Valorizado por Producto'.\n"
            "AAAasAAA Base Descuentos: La mA'AAs actualizada.\n"
            "AAAasAAA RotaciA'AAn: Informe de rotaciA'AAn."
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
        # ConfiguraciA'AAn de los 6 archivos
        archivos_config = [
            ("Seleccionar Maestro", self.ruta_maestro_produciendo),
            ("Seleccionar Produciendo N-1", self.ruta_produciendo_anterior),
            ("Seleccionar Stock", self.ruta_stock),
            ("Seleccionar Base Descuentos", self.ruta_descuentos_especiales),
            ("Seleccionar RotaciA'AAn", self.ruta_rotacion),
            ("Seleccionar Estructuras", self.ruta_estructuras)
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        # --- INPUTS DE CAMPAA'AaEA Y AA'AaEO ---
        last_row = base_row + len(archivos_config)
        
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # CampaA'Ana
        ctk.CTkLabel(frame_datos, text="Campaña (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.campania_var,
            width=80,
            placeholder_text="Ej: 05"
        )
        self.entry_campania.pack(side="left", padx=(0, 30))

        # AA'Ano
        ctk.CTkLabel(frame_datos, text="Año (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_anio = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.anio_var,
            width=80,
            placeholder_text="Ej: 2024"
        )
        self.entry_anio.pack(side="left")

        # --- BARRA DE PROGRESO ---
        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        self.progress_bar.grid(row=last_row + 1, column=0, columnspan=3, padx=20, pady=(10, 10), sticky='ew')
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        # --- BOTA'AaA"N PROCESAR ---
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
        """Helper para crear filas de selecciA'AAn"""
        btn = ctk.CTkButton(
            self, 
            text=texto_boton, 
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=220,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=4, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")

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
        # ValidaciA'AAn UI
        if not self.campania_var.get() or not self.anio_var.get():
             messagebox.showerror("Error", "Debe completar CampaA'Ana y AA'Ano.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_primer_produciendo()
        except Exception as e:
            logger.error(f"Error en primer produciendo: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)

    def procesar_primer_produciendo(self):
        # 1. Obtener Datos
        archivos = [
            self.ruta_maestro_produciendo.get(),
            self.ruta_stock.get(),
            self.ruta_descuentos_especiales.get(),
            self.ruta_produciendo_anterior.get(),
            self.ruta_rotacion.get(),
            self.ruta_estructuras.get()
        ]

        # 2. Validaciones
        if not all(archivos):
            self.after(0, lambda: messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos."))
            self.after(0, self.ocultar_progreso)
            return

        campania = self.campania_var.get()
        anio = self.anio_var.get()

        # 3. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 4. Procesamiento
            procesar_primer_produciendo(
                campania_actual=campania,
                anio_actual=anio,
                ruta_produciendo_anterior=self.ruta_produciendo_anterior.get(),
                ruta_maestro_produciendo=self.ruta_maestro_produciendo.get(),
                ruta_stock=self.ruta_stock.get(),
                ruta_descuentos_especiales=self.ruta_descuentos_especiales.get(),
                ruta_rotacion=self.ruta_rotacion.get(),
                ruta_estructuras=self.ruta_estructuras.get(),
                ruta_salida=carpeta_guardado
            )
         
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("A'AaAxito", "El procesamiento ha finalizado con A'AAxito."))
            
        except Exception as e:
            logger.error(f"Error lA'AAgica primer produciendo: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)