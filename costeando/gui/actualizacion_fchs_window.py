import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import pandas as pd
import os
from costeando.modulos.procesamiento_actualizacion_fchs import procesar_actualizacion_fchs_puro

logger = logging.getLogger(__name__)

class ActualizacionFCHSWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Actualización de Fechas')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_estructuras = tk.StringVar()
        self.ruta_compras = tk.StringVar()
        self.ruta_maestro = tk.StringVar()
        self.ruta_ordenes_apuntadas = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "Actualización de Fechas\n"
                  "- Estructuras: archivo original de estructuras por nivel de TOTVS.\n"
                  "- Maestro: archivo original de TOTVS.\n"
                  "- Compras: archivo de compras y cotizaciones revisadas.\n"
                  "- Ordenes Apuntadas: archivo original de TOTVS."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky='w')
        
        # Selección de archivos
        ttk.Button(self, text='Seleccionar Estructuras', command=lambda: self.seleccionar_archivo(self.ruta_estructuras, "Seleccionar archivo Estructuras"), width=25).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_estructuras, width=50).grid(row=1, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Maestro', command=lambda: self.seleccionar_archivo(self.ruta_maestro, "Seleccionar archivo Maestro"), width=25).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_maestro, width=50).grid(row=2, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Compras', command=lambda: self.seleccionar_archivo(self.ruta_compras, "Seleccionar archivo Compras"), width=25).grid(row=3, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_compras, width=50).grid(row=3, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Ord. Apuntadas', command=lambda: self.seleccionar_archivo(self.ruta_ordenes_apuntadas, "Seleccionar archivo Ordenes Apuntadas"), width=25).grid(row=4, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_ordenes_apuntadas, width=50).grid(row=4, column=1, padx=10, pady=2, sticky='w')

        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=6, column=0, columnspan=2, sticky='e', padx=10, pady=2)

        ttk.Button(frame_botones, text='Procesar', command=self.ejecutar_hilo).pack(side='left', padx=(0, 5))
        ttk.Button(frame_botones, text='Cancelar', command=self.destroy).pack(side='left')

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=7, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()


    def seleccionar_archivo(self, variable, titulo):
        archivo = filedialog.askopenfilename(title=titulo, filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            variable.set(archivo)
            
    def mostrar_progreso(self):
        self.progress_bar.grid()
        self.progress_bar.start(10)
        
    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        
    def ejecutar_hilo(self):
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso).start()
          
    def procesar_con_progreso(self):
        try:
            self.procesar_actualizacion_fechas()
        except Exception as e:
            logger.error(f"Error en la actualización de fechas: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_actualizacion_fechas(self):
        archivos_requeridos = [
            self.ruta_estructuras.get(),
            self.ruta_compras.get(),
            self.ruta_maestro.get(),
            self.ruta_ordenes_apuntadas.get()
        ]
        if not all(archivos_requeridos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            self.ocultar_progreso()
            return
        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            messagebox.showinfo("Cancelado", "El proceso ha sido cancelado por el usuario.")
            self.ocultar_progreso()
            return
        try:
            resultado = procesar_actualizacion_fchs_puro(
                ruta_estructuras=self.ruta_estructuras.get(),
                ruta_compras=self.ruta_compras.get(),
                ruta_maestro=self.ruta_maestro.get(),
                ruta_ordenes_apuntadas=self.ruta_ordenes_apuntadas.get(),
                carpeta_guardado=carpeta_guardado
            )
            path_guardado = resultado.get("actualizacion_fchs", "")
            if path_guardado and os.path.exists(path_guardado):
                self.ocultar_progreso()
                messagebox.showinfo("Éxito", f"El archivo ha sido procesado y guardado con éxito en:\n{path_guardado}")
                self.destroy()  # Cerrar la ventana después de un proceso exitoso
            else:
                self.ocultar_progreso()
                messagebox.showwarning("Advertencia", "El procesamiento terminó pero no se encontró el archivo de salida, vuelva a seleccionar la carpeta de guardado.")
        except Exception as e:
            logger.error(f"Error en la actualización de fechas: {str(e)}", exc_info=True)
            self.ocultar_progreso()
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
            
    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 