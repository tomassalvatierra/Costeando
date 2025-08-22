import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
import pandas as pd
# Importar la función de lógica pura
from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando

logger = logging.getLogger(__name__)

class PrimerComprandoWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Primer Comprando')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_maestro = tk.StringVar()
        self.ruta_compras = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        self.ruta_dto_especiales = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        self.ruta_calculo_comprando_ant = tk.StringVar()
        self.ruta_ficha = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "Procesamiento de Primer Comprando\n"
                  "- Maestro: el archivo original de TOTVS. Convierta antes la columna 'Codigo' a numero y quitele los espacios.\n"
                  "- Compras: archivo 'Compras y Cotizaciones revisadas'.\n"
                  "- Stock: informe especifico 'Stock Actual Valorizado por Producto'. Convierta antes la columna 'Codigo' o 'Producto' a numero.\n"
                  "- Base Descuentos: la base de descuentos mas actualizada.\n"
                  "- Lista: lista de costos anterior a la campaña a procesar(n-1), debe existir la columna 'COSTOS LISTA ACC',siendo CC la campaña n-1.\n"
                  "- Comprando: archivo Comprando anterior(n-1), debe existir la columna 'Costo sin Descuento CXX', siendo XX la campaña n-1."
                  ).grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky='w')
        
        # Selección de archivos
        ttk.Button(self, text='Seleccionar Maestro', command=lambda: self.seleccionar_archivo(self.ruta_maestro, "Seleccionar archivo Maestro"), width=25).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_maestro, width=50).grid(row=1, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Compras', command=lambda: self.seleccionar_archivo(self.ruta_compras, "Seleccionar archivo Compras"), width=25).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_compras, width=50).grid(row=2, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Stock', command=lambda: self.seleccionar_archivo(self.ruta_stock, "Seleccionar archivo Stock"), width=25).grid(row=3, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_stock, width=50).grid(row=3, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Base Descuentos', command=lambda: self.seleccionar_archivo(self.ruta_dto_especiales, "Seleccionar archivo Base Dtos Especiales"), width=25).grid(row=4, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_dto_especiales, width=50).grid(row=4, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Lista N-1', command=lambda: self.seleccionar_archivo(self.ruta_listado, "Seleccionar archivo Listado de Costos Anterior"), width=25).grid(row=5, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_listado, width=50).grid(row=5, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Comprando N-1', command=lambda: self.seleccionar_archivo(self.ruta_calculo_comprando_ant, "Seleccionar archivo Comprando anterior"), width=25).grid(row=6, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_calculo_comprando_ant, width=50).grid(row=6, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Ficha', command=lambda: self.seleccionar_archivo(self.ruta_ficha, "Seleccionar archivo Ficha"), width=25).grid(row=7, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_ficha, width=50).grid(row=7, column=1, padx=10, pady=2, sticky='w')

        # Campos de entrada
        ttk.Label(self, text='Campaña a procesar (CC):').grid(row=1, column=2, sticky='w')
        self.entry_campaña = ttk.Entry(self)
        self.entry_campaña.grid(row=1, column=3)

        ttk.Label(self, text='Año (AAAA):').grid(row=2, column=2)
        self.entry_año = ttk.Entry(self)
        self.entry_año.grid(row=2, column=3)

        ttk.Label(self, text='Mano de Obra:').grid(row=3, column=2)
        self.entry_mano_de_obra = ttk.Entry(self)
        self.entry_mano_de_obra.grid(row=3, column=3, padx=10, pady=2)

        ttk.Label(self, text='Índice A:').grid(row=4, column=2, padx=10, pady=2)
        self.entry_indice_a = ttk.Entry(self)
        self.entry_indice_a.grid(row=4, column=3)

        ttk.Label(self, text='Índice B:').grid(row=5, column=2, padx=10, pady=2)
        self.entry_indice_b = ttk.Entry(self)
        self.entry_indice_b.grid(row=5, column=3, padx=10, pady=2)

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=8, column=0, columnspan=4, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()

        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=7, column=2, columnspan=2, sticky='e', padx=10, pady=5)

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
            self.procesar_primer_comprando()
        except Exception as e:
            logger.error(f"Error en el procesamiento de primer comprando: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            self.ocultar_progreso()
            
    def procesar_primer_comprando(self):
        archivos_requeridos = [
            self.ruta_maestro.get(),
            self.ruta_compras.get(),
            self.ruta_stock.get(),
            self.ruta_dto_especiales.get(),
            self.ruta_listado.get(),
            self.ruta_calculo_comprando_ant.get(),
            self.ruta_ficha.get()
        ]
        if not all(archivos_requeridos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            self.ocultar_progreso()
            return
        campaña = self.entry_campaña.get()
        año = self.entry_año.get()
        mano_de_obra = self.entry_mano_de_obra.get()
        indice_a = self.entry_indice_a.get()
        indice_b = self.entry_indice_b.get()
        if not all([campaña, año, mano_de_obra, indice_a, indice_b]):
            messagebox.showerror("Error", "Debe completar todos los campos requeridos.")
            self.ocultar_progreso()
            return
        # Pedir carpeta de salida
        ruta_salida = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not ruta_salida:
            messagebox.showinfo("Cancelado", "El proceso ha sido cancelado por el usuario.")
            self.ocultar_progreso()
            return
        try:
            resultado = procesar_primer_comprando(
                campaña=campaña,
                año=año,
                indice_a=float(indice_a),
                indice_b=float(indice_b),
                mano_de_obra=float(mano_de_obra),
                ruta_maestro=self.ruta_maestro.get(),
                ruta_compras=self.ruta_compras.get(),
                ruta_stock=self.ruta_stock.get(),
                ruta_dto_especiales=self.ruta_dto_especiales.get(),
                ruta_listado=self.ruta_listado.get(),
                ruta_calculo_comprando_ant=self.ruta_calculo_comprando_ant.get(),
                ruta_ficha=self.ruta_ficha.get(),
                ruta_salida=ruta_salida
            )
            messagebox.showinfo("Éxito", f"El procesamiento ha finalizado con éxito.")
            self.destroy()  # Cerrar la ventana después de un proceso exitoso
        except Exception as e:
            logger.error(f"Error en el procesamiento de primer comprando: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
            self.ocultar_progreso()

    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 