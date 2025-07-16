import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import pandas as pd

from costeando.modulos.procesamiento_primer_produciendo import procesar_primer_produciendo

logger = logging.getLogger(__name__)

class PrimerProduciendoWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Primer Produciendo')
        self.geometry("+600+200")
        # Variables
        self.ruta_maestro_produciendo = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        self.ruta_descuentos_especiales = tk.StringVar()
        self.ruta_produciendo_anterior = tk.StringVar()
        self.ruta_rotacion = tk.StringVar()
        self.ruta_estructuras = tk.StringVar()
        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        ttk.Label(self, text=
                  "Procesamiento de Primer Produciendo\n"
                  "- Maestro: el archivo original de TOTVS, convierta antes la columna 'Codigo' a numero y quitele los espacios.\n"
                  "- Produciendo: archivo produciendo (n-1) .\n"
                  "- Stock: informe especifico 'Stock Actual Valorizado por Producto'.\n"
                  "- Base Descuentos: la base de descuentos mas actualizada.\n"
                  "- Rotacion: informe de rotacion."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky='w')
        ttk.Button(self, text='Seleccionar Maestro', command=lambda: self.seleccionar_archivo(self.ruta_maestro_produciendo, "Seleccionar archivo Maestro"), width=28).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_maestro_produciendo, width=65).grid(row=1, column=1, padx=10, pady=2, sticky='w')
        ttk.Button(self, text='Seleccionar Produciendo N-1', command=lambda: self.seleccionar_archivo(self.ruta_produciendo_anterior, "Seleccionar Produciendo N-1"), width=28).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_produciendo_anterior, width=65).grid(row=2, column=1, padx=10, pady=2, sticky='w')
        ttk.Button(self, text='Seleccionar Stock', command=lambda: self.seleccionar_archivo(self.ruta_stock, "Seleccionar archivo Stock"), width=28).grid(row=3, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_stock, width=65).grid(row=3, column=1, padx=10, pady=2, sticky='w')
        ttk.Button(self, text='Seleccionar Base Descuentos', command=lambda: self.seleccionar_archivo(self.ruta_descuentos_especiales, "Seleccionar archivo Base Dtos Especiales"), width=28).grid(row=4, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_descuentos_especiales, width=65).grid(row=4, column=1, padx=10, pady=2, sticky='w')   
        ttk.Button(self, text='Seleccionar Rotacion', command=lambda: self.seleccionar_archivo(self.ruta_rotacion, "Seleccionar archivo Rotacion"), width=28).grid(row=5, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_rotacion, width=65).grid(row=5, column=1, padx=10, pady=2, sticky='w')    
        ttk.Button(self, text='Seleccionar Estructuras', command=lambda: self.seleccionar_archivo(self.ruta_estructuras, "Seleccionar archivo Estructuras por Nivel"), width=28).grid(row=6, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_estructuras, width=65).grid(row=6, column=1, padx=10, pady=2, sticky='w')  
        ttk.Label(self, text='Campaña a procesar (CC):').grid(row=7, column=0)
        self.entry_campaña = ttk.Entry(self)
        self.entry_campaña.grid(row=7, column=1, sticky='w', padx=10, pady=2)
        ttk.Label(self, text='Año (AAAA):').grid(row=8, column=0)
        self.entry_año = ttk.Entry(self)
        self.entry_año.grid(row=8, column=1, sticky='w', padx=10, pady=5)
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=9, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=8, column=1, columnspan=3, padx=10, pady=5, sticky='e')
        ttk.Button(frame_botones, text='Procesar', command=self.ejecutar_hilo).pack(side='left', padx=(0, 5))
        ttk.Button(frame_botones, text='Cancelar', command=self.destroy).pack(side='left')

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
            self.procesar_primer_produciendo()
        except Exception as e:
            logger.error(f"Error en el procesamiento de primer produciendo: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            self.ocultar_progreso()

    def procesar_primer_produciendo(self):
        archivos_requeridos = [
            self.ruta_maestro_produciendo.get(),
            self.ruta_stock.get(),
            self.ruta_descuentos_especiales.get(),
            self.ruta_produciendo_anterior.get(),
            self.ruta_rotacion.get(),
            self.ruta_estructuras.get()
        ]
        if not all(archivos_requeridos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            self.ocultar_progreso()
            return
        campaña = self.entry_campaña.get()
        año = self.entry_año.get()
        if not all([campaña, año]):
            messagebox.showerror("Error", "Debe completar todos los campos requeridos.")
            self.ocultar_progreso()
            return
        ruta_salida = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not ruta_salida:
            messagebox.showinfo("Cancelado", "El proceso ha sido cancelado por el usuario.")
            self.ocultar_progreso()
            return
        try:
            resultado = procesar_primer_produciendo(
                campaña_actual=campaña,
                año_actual=año,
                ruta_produciendo_anterior=self.ruta_produciendo_anterior.get(),
                ruta_maestro_produciendo=self.ruta_maestro_produciendo.get(),
                ruta_stock=self.ruta_stock.get(),
                ruta_descuentos_especiales=self.ruta_descuentos_especiales.get(),
                ruta_rotacion=self.ruta_rotacion.get(),
                ruta_estructuras=self.ruta_estructuras.get(),
                ruta_salida=ruta_salida
            )
            messagebox.showinfo("Éxito", f"El procesamiento ha finalizado con éxito.\n\nArchivos generados:\n" + '\n'.join([f"- {v}" for v in resultado.values()]))
        except Exception as e:
            logger.error(f"Error en el procesamiento de primer produciendo: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
        finally:
            self.ocultar_progreso()

    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 