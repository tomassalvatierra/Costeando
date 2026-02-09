import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Importamos la lógica de negocio original
from costeando.modulos.procesamiento_actualizacion_fchs import procesar_actualizacion_fchs_puro

logger = logging.getLogger(__name__)

class ActualizacionFCHSWindow(ctk.CTkFrame): # <-- Cambio a Frame
    def __init__(self, master):
        super().__init__(master)
        
        # Variables (tk.StringVar funciona perfecto con CustomTkinter)
        self.ruta_estructuras = tk.StringVar()
        self.ruta_compras = tk.StringVar()
        self.ruta_maestro = tk.StringVar()
        self.ruta_ordenes_apuntadas = tk.StringVar()
        
        # Configuración del Grid para que el contenido se expanda bien
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz visual
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TÍTULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Actualización de Fechas", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        # --- DESCRIPCIÓN / INSTRUCCIONES ---
        lbl_desc = ctk.CTkLabel(
            self, 
            text=("Estructuras: Archivo original por nivel (TOTVS).\n"
                  "Maestro: Archivo original TOTVS.\n"
                  "Compras: Archivo de compras y cotizaciones revisadas.\n"
                  "Órdenes Apuntadas: Archivo original TOTVS."),
            justify="left",
            text_color="gray70",
            font=("Roboto", 12)
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        # --- SELECTORES DE ARCHIVOS (Usando Helper) ---
        self.crear_fila_selector(2, "Seleccionar Estructuras", self.ruta_estructuras)
        self.crear_fila_selector(3, "Seleccionar Maestro", self.ruta_maestro)
        self.crear_fila_selector(4, "Seleccionar Compras", self.ruta_compras)
        self.crear_fila_selector(5, "Seleccionar Ord. Apuntadas", self.ruta_ordenes_apuntadas)

        # --- BARRA DE PROGRESO ---
        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        self.progress_bar.grid(row=6, column=0, columnspan=3, padx=20, pady=(30, 10), sticky='ew')
        self.progress_bar.set(0)
        self.progress_bar.grid_remove() # Oculto por defecto

        # --- BOTÓN DE PROCESAR ---
        self.btn_procesar = ctk.CTkButton(
            self, 
            text='INICIAR PROCESO', 
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5", 
            hover_color="#144870"
        )
        self.btn_procesar.grid(row=7, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        """Helper para generar filas de selección de archivo limpias"""
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

        entry = ctk.CTkEntry(
            self, 
            textvariable=variable, 
            placeholder_text="Seleccione un archivo..."
        )
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
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_actualizacion_fechas()
        except Exception as e:
            logger.error(f"Error en la actualización de fechas: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}"))
            self.after(0, self.ocultar_progreso)

    def procesar_actualizacion_fechas(self):
        # 1. Validar entradas
        archivos_requeridos = [
            self.ruta_estructuras.get(),
            self.ruta_compras.get(),
            self.ruta_maestro.get(),
            self.ruta_ordenes_apuntadas.get()
        ]
        
        if not all(archivos_requeridos):
            self.after(0, lambda: messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos."))
            self.after(0, self.ocultar_progreso)
            return

        # 2. Pedir carpeta de salida (Nota: askdirectory suele bloquear el hilo, cuidado aquí)
        # Idealmente esto iría en el hilo principal antes de lanzar el thread, pero lo dejamos
        # aquí manteniendo tu lógica original.
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        
        if not carpeta_guardado:
            # Cancelado por usuario
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Llamar a la lógica pesada
            procesar_actualizacion_fchs_puro(
                ruta_estructuras=self.ruta_estructuras.get(),
                ruta_compras=self.ruta_compras.get(),
                ruta_maestro=self.ruta_maestro.get(),
                ruta_ordenes_apuntadas=self.ruta_ordenes_apuntadas.get(),
                carpeta_guardado=carpeta_guardado
            )
            
            # 4. Finalización exitosa
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito."))
            
            # Nota: Eliminamos self.destroy() porque ahora es un panel fijo.
            # Podrías agregar un self.limpiar_inputs() si quisieras vaciar los campos.

        except Exception as e:
            logger.error(f"Error en el procesamiento: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}"))
            self.after(0, self.ocultar_progreso)