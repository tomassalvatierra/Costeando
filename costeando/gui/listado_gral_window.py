import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Logica de negocio original
from costeando.modulos.procesamiento_listado_gral import procesar_listado_gral_puro
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)

class ListadoGralWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # Variables
        self.ruta_produciendo = tk.StringVar()
        self.ruta_comprando = tk.StringVar()
        self.ruta_costo_primo = tk.StringVar()
        self.ruta_base_descuentos = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        self.ruta_mdo = tk.StringVar()
        self.ruta_leader_list = tk.StringVar()
        self.ruta_compilado_fechas = tk.StringVar()
        
        # Variables de texto
        self.campana_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        # Configuracion del Grid
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TITULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Listado General Completo", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "Produciendo/Comprando: Archivos de campaAa a procesar.\n"
            "Costo Primo: Maestro original.\n"
            "Mano de Obra: Debe incluir las 3 manos de obra.\n"
            "Listado: El archivo a completar."
        )
        lbl_desc = ctk.CTkLabel(
            self, 
            text=instrucciones,
            justify="left",
            text_color="gray70",
            font=("Roboto", 12)
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        # --- SELECTORES DE ARCHIVOS (8 Archivos) ---
        # Usamos una lista para generar los campos automaticamente y mantener el codigo limpio
        archivos_config = [
            ("Seleccionar Lista a Completar", self.ruta_listado),
            ("Seleccionar Produciendo", self.ruta_produciendo),
            ("Seleccionar Comprando", self.ruta_comprando),
            ("Seleccionar Costo Primo", self.ruta_costo_primo),
            ("Seleccionar Base Descuentos", self.ruta_base_descuentos),
            ("Seleccionar Mano de Obra", self.ruta_mdo),
            ("Seleccionar Leader List", self.ruta_leader_list),
            ("Seleccionar Fchs Ult Compra", self.ruta_compilado_fechas)
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        # --- DATOS DE FECHA (CAMPAAA / AAO) ---
        last_row = base_row + len(archivos_config)
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # CampaAa
        ctk.CTkLabel(frame_datos, text="CampaAa (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.campana_var,
            width=80, 
            placeholder_text="Ej: 05"
        )
        self.entry_campania.pack(side="left", padx=(0, 30))

        # AAo
        ctk.CTkLabel(frame_datos, text="AAo (AAAA):").pack(side="left", padx=(0, 10))
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

        # --- BOTON PROCESAR ---
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
        """Helper para crear filas de seleccion"""
        btn = ctk.CTkButton(
            self, 
            text=texto_boton, 
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=220, # Un poco mas ancho por los nombres largos
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=4, sticky="w") # pady reducido para compactar

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
        # Validacion basica UI
        if not self.campana_var.get() or not self.anio_var.get():
             messagebox.showerror("Error", "Debe completar CampaAa y AAo.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_datos_dyc()
        except Exception as e:
            logger.error(f"Error en listado general: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)

    def procesar_datos_dyc(self):
        # 1. Obtener Datos
        campania = self.campana_var.get()
        anio = self.anio_var.get()
        
        archivos = [
            self.ruta_listado.get(),
            self.ruta_produciendo.get(),
            self.ruta_comprando.get(),
            self.ruta_costo_primo.get(),
            self.ruta_base_descuentos.get(),
            self.ruta_mdo.get(),
            self.ruta_leader_list.get(),
            self.ruta_compilado_fechas.get()
        ]

        # 2. Validaciones
        if not all(archivos):
            self.after(0, lambda: messagebox.showerror("Error", "Todos los archivos son obligatorios."))
            self.after(0, self.ocultar_progreso)
            return

        # 3. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 4. Procesamiento
            procesar_listado_gral_puro(
                ruta_produciendo=self.ruta_produciendo.get(),
                ruta_comprando=self.ruta_comprando.get(),
                ruta_costo_primo=self.ruta_costo_primo.get(),
                ruta_base_descuentos=self.ruta_base_descuentos.get(),
                ruta_listado=self.ruta_listado.get(),
                ruta_mdo=self.ruta_mdo.get(),
                ruta_leader_list=self.ruta_leader_list.get(),
                ruta_compilado_fechas_ult_compra=self.ruta_compilado_fechas.get(),
                campania=campania,
                anio=anio,
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Exito", "El procesamiento ha finalizado con exito."))
            
        except Exception as e:
            logger.error(f"Error logica listado general: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)