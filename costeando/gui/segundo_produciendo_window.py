import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging

from costeando.modulos.procesamiento_segundo_produciendo import procesar_segundo_produciendo

logger = logging.getLogger(__name__)

class SegundoProduciendoWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Segundo Produciendo')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_segundo_produciendo = tk.StringVar()
        self.ruta_base_especiales = tk.StringVar()
        self.ruta_importador_descuentos = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "Procesamiento de Segundo Produciendo\n"
                  "- Produciendo: archivo produciendo primera etapa.\n"
                  "- Base Descuentos: la base de descuentos mas actualizada.\n"
                  "- Importador Dtos: importador con los descuentos que quiere agregar.\n"
                  "- Fecha de inicio y fin: fechas del periodo de las compras, formato dd/mm/aaaa."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky='w')
        
        # Selección de archivos
        ttk.Button(self, text='Seleccionar Produciendo', command=lambda: self.seleccionar_archivo(self.ruta_segundo_produciendo, "Seleccionar archivo Produciendo primera Etapa"), width=25).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_segundo_produciendo, width=50).grid(row=1, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Base Descuentos', command=lambda: self.seleccionar_archivo(self.ruta_base_especiales, "Seleccionar archivo Base de datos de descuentos"), width=25).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_base_especiales, width=50).grid(row=2, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Importador Dtos', command=lambda: self.seleccionar_archivo(self.ruta_importador_descuentos, "Seleccionar archivo Importador Base Descuentos"), width=25).grid(row=3, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_importador_descuentos, width=50).grid(row=3, column=1, padx=10, pady=2, sticky='w')

        # Campos de entrada
        ttk.Label(self, text='Fecha de inicio de compras:').grid(row=5, column=0, padx=10, pady=5)
        self.entry_fecha_inicio = ttk.Entry(self)
        self.entry_fecha_inicio.grid(row=5, column=1, padx=10, pady=5, sticky='w')
        
        ttk.Label(self, text='Fecha de final de compras:').grid(row=6, column=0, padx=10, pady=5)
        self.entry_fecha_final = ttk.Entry(self)
        self.entry_fecha_final.grid(row=6, column=1, padx=10, pady=5, sticky='w')
        
        ttk.Label(self, text='Campaña (CC):').grid(row=7, column=0, padx=10, pady=5)
        self.entry_campaña = ttk.Entry(self)
        self.entry_campaña.grid(row=7, column=1, padx=10, pady=5, sticky='w')
        
        ttk.Label(self, text='Año (AAAA):').grid(row=8, column=0, padx=10, pady=5)
        self.entry_año = ttk.Entry(self)
        self.entry_año.grid(row=8, column=1, padx=10, pady=5, sticky='w')

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=9, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()

        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=8, column=1, columnspan=3, sticky='e', padx=10, pady=2)

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
            self.procesar_segundo_produciendo()
        except Exception as e:
            logger.error(f"Error en el procesamiento de segundo produciendo: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_segundo_produciendo(self):
        # Validar que todos los archivos estén seleccionados
        archivos_requeridos = [
            self.ruta_segundo_produciendo.get(),
            self.ruta_base_especiales.get()
        ]
        
        if not all(archivos_requeridos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            self.ocultar_progreso()
            return
            
        # Validar campos de entrada
        fecha_inicio = self.entry_fecha_inicio.get()
        fecha_final = self.entry_fecha_final.get()
        campaña = self.entry_campaña.get()
        año = self.entry_año.get()
        
        if not all([fecha_inicio, fecha_final, campaña, año]):
            messagebox.showerror("Error", "Debe completar todos los campos requeridos.")
            self.ocultar_progreso()
            return
        
        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        if not carpeta_guardado:
            messagebox.showerror("Error", "Debes seleccionar una carpeta para guardar los resultados.")
            self.ocultar_progreso()
            return
        try:
            resultado=procesar_segundo_produciendo(
                ruta_produciendo=self.ruta_segundo_produciendo.get(),
                ruta_base_especiales=self.ruta_base_especiales.get(),
                ruta_importador_descuentos=self.ruta_importador_descuentos.get() or None,
                campaña=campaña,
                año=año,
                fecha_compras_inicio=fecha_inicio,
                fecha_compras_final=fecha_final,
                carpeta_guardado=carpeta_guardado
            )
       
            self.ocultar_progreso()
            messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito.")
            self.destroy()  # Cerrar la ventana después de un proceso exitoso
        except Exception as e:
            logger.error(f"Error en el procesamiento de primer comprando: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento:\n{e}")
            self.ocultar_progreso()
        
    def destroy(self):
        self.ocultar_progreso()
        super().destroy() 