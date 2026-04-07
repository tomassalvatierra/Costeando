import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Logica de negocio original
from costeando.modulos.procesamiento_leader_list import procesar_leader_list_puro
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)

class LeaderListWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # Variables
        self.ruta_leader_list = tk.StringVar()
        self.ruta_listado_anterior = tk.StringVar()
        self.ruta_maestro = tk.StringVar()
        self.ruta_dobles = tk.StringVar()
        self.ruta_combinadas = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        
        # Variables para Campania y anio (usamos StringVar para facil acceso)
        self.campania_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        # Configuracion del Grid
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TITULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Leader List", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "Maestro: Archivo original TOTVS.\n"
            "Listado Costos: Debe tener columna 'COSTO LISTA ACC' (N-1).\n"
            "Resto de archivos: Originales sin modificar."
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
        # Usamos un indice base para facilitar el orden
        base_row = 2
        self.crear_fila_selector(base_row, "Seleccionar Leader List", self.ruta_leader_list)
        self.crear_fila_selector(base_row + 1, "Seleccionar Maestro", self.ruta_maestro)
        self.crear_fila_selector(base_row + 2, "Seleccionar Combinadas", self.ruta_combinadas)
        self.crear_fila_selector(base_row + 3, "Seleccionar Dobles", self.ruta_dobles)
        self.crear_fila_selector(base_row + 4, "Seleccionar Lista N-1", self.ruta_listado_anterior)
        self.crear_fila_selector(base_row + 5, "Seleccionar Stock", self.ruta_stock)

        # --- DATOS DE FECHA (CAMPAAA / AAO) ---
        row_datos = base_row + 6
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=row_datos, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # CampaAa
        ctk.CTkLabel(frame_datos, text="Campaña (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.campania_var,
            width=80, 
            placeholder_text="Ej: 05"
        )
        self.entry_campania.pack(side="left", padx=(0, 30))

        # AAo
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
        self.progress_bar.grid(row=row_datos + 1, column=0, columnspan=3, padx=20, pady=(10, 10), sticky='ew')
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
        self.btn_procesar.grid(row=row_datos + 2, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        """Helper estandarizado para seleccion de archivos"""
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
        self.entry_campania.configure(state="disabled")
        self.entry_anio.configure(state="disabled")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")
        self.entry_campania.configure(state="normal")
        self.entry_anio.configure(state="normal")

    def ejecutar_hilo(self):
        # Validacion inicial UI
        if not self.campania_var.get() or not self.anio_var.get():
             messagebox.showerror("Error", "Debe completar Campaña y Año.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_leader_list()
        except Exception as e:
            logger.error(f"Error en leader list: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)

    def procesar_leader_list(self):
        # 1. Obtener y Limpiar datos
        campania = self.campania_var.get().zfill(2) # Asegura 2 dA'AAgitos
        anio= self.anio_var.get()
        
        leader_list = self.ruta_leader_list.get()
        listado = self.ruta_listado_anterior.get()
        maestro = self.ruta_maestro.get()
        dobles = self.ruta_dobles.get()
        combinadas = self.ruta_combinadas.get()
        stock = self.ruta_stock.get()

        # 2. Validaciones
        if not campania.isdigit() or len(campania) != 2:
            self.after(0, lambda: messagebox.showerror("Error", "Campaña debe ser 2 digitos (Ej: 05)."))
            self.after(0, self.ocultar_progreso)
            return

        if not anio.isdigit() or len(anio) != 4:
            self.after(0, lambda: messagebox.showerror("Error", "Año debe ser 4 digitos (Ej: 2024)."))
            self.after(0, self.ocultar_progreso)
            return

        if not all([leader_list, listado, maestro, dobles, combinadas, stock]):
            self.after(0, lambda: messagebox.showerror("Error", "Todos los archivos son obligatorios."))
            self.after(0, self.ocultar_progreso)
            return

        # 3. Directorio de salida
        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 4. Procesamiento
            procesar_leader_list_puro(
                ruta_leader_list=leader_list,
                ruta_listado_anterior=listado,
                ruta_maestro=maestro,
                ruta_dobles=dobles,
                ruta_combinadas=combinadas,
                ruta_stock=stock,
                campania=campania,
                anio=anio,
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Exito", "El procesamiento ha finalizado con exito."))
            
        except Exception as e:
            logger.error(f"Error logica leader list: {str(e)}", exc_info=True)
            self.after(0, lambda: mostrar_error_legible(e))
            self.after(0, self.ocultar_progreso)