import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# LA'AAgica de negocio original
from costeando.modulos.procesamiento_segundo_comprando import procesar_segundo_comprando
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)

class SegundoComprandoWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # --- Variables de Archivo ---
        self.ruta_comprando = tk.StringVar()
        self.ruta_costos_especiales = tk.StringVar()
        self.ruta_importador_descuentos = tk.StringVar()
        
        # --- Variables de Texto ---
        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()
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
            text="Segundo Comprando", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "AAAasAAA Base Descuentos: La mA'AAs actualizada.\n"
            "AAAasAAA Comprando: Archivo resultante de la primera etapa.\n"
            "AAAasAAA Fechas: Formato dd/mm/aaaa (Ej: 01/05/2024)."
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
            ("Seleccionar Comprando (Etapa 1)", self.ruta_comprando),
            ("Seleccionar Base Descuentos", self.ruta_costos_especiales),
            ("Seleccionar Importador", self.ruta_importador_descuentos)
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        # --- PARA'AAMETROS (FECHAS Y CAMPAA'AaEA) ---
        last_row = base_row + len(archivos_config)
        
        frame_params = ctk.CTkFrame(self, fg_color="transparent")
        frame_params.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # Fila 1: Fechas
        self.crear_input_param(frame_params, "Inicio (dd/mm/aaaa):", self.fecha_inicio_var, 0, 0, "Ej: 01/01/2025")
        self.crear_input_param(frame_params, "Fin (dd/mm/aaaa):", self.fecha_fin_var, 0, 1, "Ej: 31/01/2025")

        # Fila 2: CampaA'Ana y AA'Ano
        self.crear_input_param(frame_params, "CampaA'Ana (CC):", self.campania_var, 1, 0, "Ej: 05")
        self.crear_input_param(frame_params, "AA'Ano (AAAA):", self.anio_var, 1, 1, "Ej: 2025")

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
        """Helper para selecciA'AAn de archivos"""
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
        """Helper para inputs pequeA'Anos"""
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
        # ValidaciA'AAn UI
        if not all([self.fecha_inicio_var.get(), self.fecha_fin_var.get(), 
                    self.campania_var.get(), self.anio_var.get()]):
             messagebox.showerror("Error", "Debe completar todas las fechas y datos de campaA'Ana.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_segundo_comprando()
        except Exception as e:
            logger.error(f"Error en segundo comprando: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)

    def procesar_segundo_comprando(self):
        # 1. Obtener Datos
        comprando = self.ruta_comprando.get()
        costos = self.ruta_costos_especiales.get()
        importador = self.ruta_importador_descuentos.get()

        if not comprando or not costos:
            self.after(0, lambda: messagebox.showerror("Error", "Los archivos de Comprando y Base Descuentos son obligatorios."))
            self.after(0, self.ocultar_progreso)
            return

        # 2. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Procesar
            # Nota: 'importador' puede ser vacA'AAo segA'AAn tu lA'AAgica original ("or None")
            procesar_segundo_comprando(
                ruta_comprando=comprando,
                ruta_costos_especiales=costos,
                ruta_importador_descuentos=importador if importador else None,
                campania=self.campania_var.get(),
                anio=self.anio_var.get(),
                fecha_compras_inicio=self.fecha_inicio_var.get(),
                fecha_compras_final=self.fecha_fin_var.get(),
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("A'AaAxito", "El procesamiento ha finalizado con A'AAxito."))
            
        except Exception as e:
            logger.error(f"Error lA'AAgica segundo comprando: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)