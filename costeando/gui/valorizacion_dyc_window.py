import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import pandas as pd
import numpy as np
import os
from costeando.modulos.procesamiento_valorizacion_dyc import procesar_valorizacion_dyc_puro

logger = logging.getLogger(__name__)

class ValorizacionDYCWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Valorización de Dobles y Combinadas')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_combinadas = tk.StringVar()
        self.ruta_dobles = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "- Lista: lista de costos con la que desea valorizar, debe tener la columna 'COSTO LISTA CXX', siendo XX la campaña correspondiente.\n"
                  "- Los archivos de dobles y combinadas deben ser los originales."
                  ).grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky='w')
        
        # Entradas de campaña y año
        ttk.Label(self, text='Campaña (CC):').grid(row=1, column=2, padx=5, pady=2)
        self.entry_campaña = ttk.Entry(self)
        self.entry_campaña.grid(row=1, column=3, padx=5, pady=2)
        
        ttk.Label(self, text='Año (AAAA):').grid(row=2, column=2, padx=5, pady=2)
        self.entry_año = ttk.Entry(self)
        self.entry_año.grid(row=2, column=3, padx=5, pady=2)

        # Selección de archivos
        ttk.Button(self, text='Seleccionar Dobles', command=lambda: self.seleccionar_archivo(self.ruta_dobles, "Seleccionar archivo Dobles"), width=25).grid(row=1, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_dobles, width=50).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Button(self, text='Seleccionar Combinadas', command=lambda: self.seleccionar_archivo(self.ruta_combinadas, "Seleccionar archivo Combinadas"), width=25).grid(row=2, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_combinadas, width=50).grid(row=2, column=1, padx=5, pady=2)
        
        ttk.Button(self, text='Seleccionar Lista', command=lambda: self.seleccionar_archivo(self.ruta_listado, "Seleccionar Listado"), width=25).grid(row=3, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_listado, width=50).grid(row=3, column=1, padx=5, pady=2)
    
        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=3, column=2, columnspan=2, sticky='e', padx=5, pady=2)

        ttk.Button(frame_botones, text='Procesar', command=self.ejecutar_hilo).pack(side='left', padx=(0, 5))
        ttk.Button(frame_botones, text='Cancelar', command=self.destroy).pack(side='left')
        
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=5, column=0, columnspan=4, padx=10, pady=(5, 10), sticky='ew')
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
            self.procesar_datos_dyc()
        except Exception as e:
            logger.error(f"Error en el procesamiento de valorización DyC: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_datos_dyc(self):
        campaña = self.entry_campaña.get()
        año = self.entry_año.get()
        listado = self.ruta_listado.get()
        combinadas = self.ruta_combinadas.get()
        dobles = self.ruta_dobles.get()

        if not campaña or not año:
            messagebox.showerror("Error", "Campaña y Año son obligatorios.")
            self.ocultar_progreso()
            return
        if not all([listado, combinadas, dobles]):
            messagebox.showerror("Error", "Todos los archivos son obligatorios.")
            self.ocultar_progreso()
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            messagebox.showinfo("Cancelado", "El proceso ha sido cancelado por el usuario.")
            self.ocultar_progreso()
            return
        try:
            resultado = procesar_valorizacion_dyc_puro(
                ruta_listado=listado,
                ruta_combinadas=combinadas,
                ruta_dobles=dobles,
                campana=campaña,
                anio=año,
                carpeta_guardado=carpeta_guardado
            )
            path_guardado = resultado.get("valorizacion_dyc", "")
            if path_guardado and os.path.exists(path_guardado):
               
                messagebox.showinfo("Éxito", f"El archivo ha sido procesado y guardado con éxito en:\n{path_guardado}")
                self.destroy()
            else:
                self.ocultar_progreso()
                messagebox.showwarning("Advertencia", "El procesamiento terminó pero no se encontró el archivo de salida.")
        except Exception as e:
            logger.error(f"Error en el procesamiento de valorización DyC: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
            self.ocultar_progreso()
        
    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 