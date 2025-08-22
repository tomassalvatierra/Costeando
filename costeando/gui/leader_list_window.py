import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import pandas as pd
import os
from costeando.modulos.procesamiento_leader_list import procesar_leader_list_puro

logger = logging.getLogger(__name__)

class LeaderListWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Leader List')
        self.geometry("+520+200")
        
        # Variables
        self.ruta_leader_list = tk.StringVar()
        self.ruta_listado_anterior = tk.StringVar()
        self.ruta_maestro = tk.StringVar()
        self.ruta_dobles = tk.StringVar()
        self.ruta_combinadas = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "- Maestro: El archivo original de TOTVS, convierta antes la columna 'Codigo' a numero y quitele los espacios.\n"
                  "- Listado Costos: Listado de costos anterior a la campaña a procesar, debe existir la columna 'COSTO LISTA ACC'.\n"
                  "- Los demás archivos ingresarlos originales."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))
        
        # Botones y entradas
        ttk.Button(self, text='Seleccionar Leader List', command=lambda: self.seleccionar_archivo(self.ruta_leader_list, "Seleccionar archivo Leader List"), width=25).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_leader_list, width=70).grid(row=1, column=1, padx=10, pady=2, sticky='w')
        
        ttk.Button(self, text='Seleccionar Maestro', command=lambda: self.seleccionar_archivo(self.ruta_maestro, "Seleccionar archivo Maestro"), width=25).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_maestro, width=70).grid(row=2, column=1, padx=10, pady=2, sticky='w')
        
        ttk.Button(self, text='Seleccionar Combinadas', command=lambda: self.seleccionar_archivo(self.ruta_combinadas, "Seleccionar archivo Combinadas"), width=25).grid(row=3, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_combinadas, width=70).grid(row=3, column=1, padx=10, pady=2, sticky='w')
        
        ttk.Button(self, text='Seleccionar Dobles', command=lambda: self.seleccionar_archivo(self.ruta_dobles, "Seleccionar archivo Dobles"), width=25).grid(row=4, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_dobles, width=70).grid(row=4, column=1, padx=10, pady=2, sticky='w')
        
        ttk.Button(self, text='Seleccionar Lista N-1', command=lambda: self.seleccionar_archivo(self.ruta_listado_anterior, "Seleccionar Listado de Costos N-1"), width=25).grid(row=5, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_listado_anterior, width=70).grid(row=5, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Stock', command=lambda: self.seleccionar_archivo(self.ruta_stock, "Seleccionar Stock"), width=25).grid(row=6, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_stock, width=70).grid(row=6, column=1, padx=10, pady=2, sticky='w')
        
        # Entradas adicionales: campaña y año
        ttk.Label(self, text='Campaña a procesar (CC):').grid(row=7, column=0, padx=10, pady=(10, 2))
        self.entry_campaña = ttk.Entry(self, width=10)
        self.entry_campaña.grid(row=7, column=1, padx=10, pady=(10, 2), sticky='w')
        
        ttk.Label(self, text='Año (AAAA):').grid(row=8, column=0, padx=10, pady=2)
        self.entry_año = ttk.Entry(self, width=10)
        self.entry_año.grid(row=8, column=1, padx=10, pady=2, sticky='w')

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=9, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()

        # Frame para botones inferiores
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=8, column=0, columnspan=2, sticky='e', padx=10, pady=2)
        
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
            self.procesar_leader_list()
        except Exception as e:
            logger.error(f"Error en el procesamiento de leader list: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_leader_list(self):
        campaña = self.entry_campaña.get().zfill(2)
        año = self.entry_año.get()
        leader_list = self.ruta_leader_list.get()
        listado = self.ruta_listado_anterior.get()
        maestro = self.ruta_maestro.get()
        dobles = self.ruta_dobles.get()
        combinadas = self.ruta_combinadas.get()
        stock = self.ruta_stock.get()
        if not campaña.isdigit() or len(campaña) != 2:
            messagebox.showerror("Error", "El campo 'Campaña' debe ser un número de 2 dígitos, formato (CC).")
            self.ocultar_progreso()
            return
        if not año.isdigit() or len(año) != 4:
            messagebox.showerror("Error", "El año debe ser un número de 4 dígitos, formato (AAAA).")
            self.ocultar_progreso()
            return
        if not all([campaña, año, leader_list, listado, maestro, dobles, combinadas, stock]):
            messagebox.showerror("Error", "Todos los campos son obligatorios. Verifique los archivos seleccionados.")
            self.ocultar_progreso()
            return
        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        if not carpeta_guardado:
            messagebox.showerror("Error", "Debes seleccionar una carpeta para guardar los resultados.")
            self.ocultar_progreso()
            return
        try:
            resultado = procesar_leader_list_puro(
                ruta_leader_list=leader_list,
                ruta_listado_anterior=listado,
                ruta_maestro=maestro,
                ruta_dobles=dobles,
                ruta_combinadas=combinadas,
                ruta_stock=stock,
                campana=campaña,
                anio=año,
                carpeta_guardado=carpeta_guardado
            )
            messagebox.showinfo("Éxito", f"Los archivos han sido procesados y guardados con éxito en:\n{carpeta_guardado}")
            self.destroy()  # Cerrar la ventana después de un proceso exitoso
        except Exception as e:
            logger.error(f"Error en el procesamiento de leader list: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
            self.ocultar_progreso()
        
    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 