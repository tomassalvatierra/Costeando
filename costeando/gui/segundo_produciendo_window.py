import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Lógica de negocio original
from costeando.modulos.procesamiento_segundo_produciendo import procesar_segundo_produciendo

logger = logging.getLogger(__name__)

class SegundoProduciendoWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # --- Variables de Archivo ---
        self.ruta_segundo_produciendo = tk.StringVar()
        self.ruta_base_especiales = tk.StringVar()
        self.ruta_importador_descuentos = tk.StringVar()
        
        # --- Variables de Texto ---
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()
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
            text="Segundo Produciendo", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "• Produciendo: Archivo resultante de la primera etapa.\n"
            "• Base Descuentos: La más actualizada.\n"
            "• Importador Dtos: Opcional, si desea agregar descuentos.\n"
            "• Fechas: Formato dd/mm/aaaa."
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
            ("Seleccionar Produciendo (Etapa 1)", self.ruta_segundo_produciendo),
            ("Seleccionar Base Descuentos", self.ruta_base_especiales),
            ("Seleccionar Importador Dtos", self.ruta_importador_descuentos)
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        # --- PARÁMETROS (FECHAS Y CAMPAÑA) ---
        last_row = base_row + len(archivos_config)
        
        frame_params = ctk.CTkFrame(self, fg_color="transparent")
        frame_params.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # Fila 1: Fechas
        self.crear_input_param(frame_params, "Inicio (dd/mm/aaaa):", self.fecha_inicio_var, 0, 0, "Ej: 01/05/2024")
        self.crear_input_param(frame_params, "Fin (dd/mm/aaaa):", self.fecha_fin_var, 0, 1, "Ej: 31/05/2024")

        # Fila 2: Campaña y Año
        self.crear_input_param(frame_params, "Campaña (CC):", self.campana_var, 1, 0, "Ej: 05")
        self.crear_input_param(frame_params, "Año (AAAA):", self.anio_var, 1, 1, "Ej: 2024")

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
            width=220,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=4, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")

    def crear_input_param(self, parent, label_text, variable, row, col, placeholder=""):
        """Helper para inputs pequeños"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=10, pady=8, sticky="w")
        
        ctk.CTkLabel(frame, text=label_text, font=("Roboto", 12)).pack(anchor="w")
        ctk.CTkEntry(frame, textvariable=variable, width=140, placeholder_text=placeholder).pack()

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
        if not all([self.fecha_inicio_var.get(), self.fecha_fin_var.get(), 
                    self.campana_var.get(), self.anio_var.get()]):
             messagebox.showerror("Error", "Debe completar todas las fechas y datos de campaña.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_segundo_produciendo()
        except Exception as e:
            logger.error(f"Error en segundo produciendo: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}"))
            self.after(0, self.ocultar_progreso)

    def procesar_segundo_produciendo(self):
        # 1. Obtener Datos
        produciendo = self.ruta_segundo_produciendo.get()
        base = self.ruta_base_especiales.get()
        importador = self.ruta_importador_descuentos.get()

        if not produciendo or not base:
            self.after(0, lambda: messagebox.showerror("Error", "Produciendo y Base Descuentos son obligatorios."))
            self.after(0, self.ocultar_progreso)
            return

        # 2. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Procesar
            # importador es opcional ("or None")
            procesar_segundo_produciendo(
                ruta_produciendo=produciendo,
                ruta_base_especiales=base,
                ruta_importador_descuentos=importador if importador else None,
                campaña=self.campana_var.get(),
                año=self.anio_var.get(),
                fecha_compras_inicio=self.fecha_inicio_var.get(),
                fecha_compras_final=self.fecha_fin_var.get(),
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito."))
            
        except Exception as e:
            logger.error(f"Error lógica segundo produciendo: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error:\n{e}"))
            self.after(0, self.ocultar_progreso)