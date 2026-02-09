import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Lógica de negocio original
from costeando.modulos.procesamiento_proyectados import procesar_proyectados_puro

logger = logging.getLogger(__name__)

class ProyectadosWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # --- Variables de Archivo ---
        self.ruta_lista = tk.StringVar()
        self.ruta_coef = tk.StringVar()
        
        # --- Variables de Parámetros ---
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
            text="Costos Proyectados", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        # --- INSTRUCCIONES ---
        instrucciones = (
            "• Lista: Debe tener columnas 'COSTO LISTA ACC' y 'VARIABLE'.\n"
            "• Coeficientes: Tabla con mínimo N+10 campañas futuras."
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
        # Solo son 2 archivos, pero usamos el helper para mantener consistencia visual
        self.crear_fila_selector(2, "Seleccionar Lista", self.ruta_lista)
        self.crear_fila_selector(3, "Seleccionar Coeficientes", self.ruta_coef)

        # --- INPUTS DE CAMPAÑA Y AÑO ---
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=4, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        # Campaña
        ctk.CTkLabel(frame_datos, text="Campaña (CC):").pack(side="left", padx=(0, 10))
        self.entry_camp = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.campana_var,
            width=80,
            placeholder_text="Ej: 01"
        )
        self.entry_camp.pack(side="left", padx=(0, 30))

        # Año
        ctk.CTkLabel(frame_datos, text="Año (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_año = ctk.CTkEntry(
            frame_datos, 
            textvariable=self.anio_var,
            width=80,
            placeholder_text="Ej: 2025"
        )
        self.entry_año.pack(side="left")

        # --- BARRA DE PROGRESO ---
        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        self.progress_bar.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 10), sticky='ew')
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        # --- BOTÓN PROCESAR ---
        self.btn_procesar = ctk.CTkButton(
            self, 
            text='INICIAR PROYECCIÓN', 
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870"
        )
        self.btn_procesar.grid(row=6, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        """Helper para filas de archivo"""
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
        self.btn_procesar.configure(state="normal", text="INICIAR PROYECCIÓN")

    def ejecutar_hilo(self):
        # Validación UI
        camp = self.campana_var.get()
        anio = self.anio_var.get()
        
        if not camp or not anio:
             messagebox.showerror("Error", "Todos los campos son obligatorios.")
             return
        
        if not (camp.isdigit() and len(camp) == 2):
            messagebox.showerror("Error", "La campaña debe tener 2 dígitos. Ejemplo: 01")
            return

        if not (anio.isdigit() and len(anio) == 4):
            messagebox.showerror("Error", "El año debe tener 4 dígitos. Ejemplo: 2025")
            return

        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_proyectados()
        except Exception as e:
            logger.error(f"Error en proyectados: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}"))
            self.after(0, self.ocultar_progreso)

    def procesar_proyectados(self):
        # 1. Obtener Datos
        lista = self.ruta_lista.get()
        coef = self.ruta_coef.get()
        camp_inicial = self.campana_var.get()
        año_inicial = self.anio_var.get()

        if not all([lista, coef]):
            self.after(0, lambda: messagebox.showerror("Error", "Debe seleccionar ambos archivos."))
            self.after(0, self.ocultar_progreso)
            return

        # 2. Carpeta Salida
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Procesar
            procesar_proyectados_puro(
                ruta_lista=lista,
                ruta_coef=coef,
                camp_inicial=camp_inicial,
                anio_inicial=año_inicial,
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito."))
            
        except Exception as e:
            logger.error(f"Error lógica proyectados: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error:\n{e}"))
            self.after(0, self.ocultar_progreso)