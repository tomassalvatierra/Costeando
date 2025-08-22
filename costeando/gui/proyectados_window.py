import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from costeando.modulos.procesamiento_proyectados import procesar_proyectados_puro

logger = logging.getLogger(__name__)

class ProyectadosWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Costos Proyectados')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_lista = tk.StringVar()
        self.ruta_coef = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "- Lista: lista de costos a proyectar, deben existir las columnas 'COSTO LISTA ACC' y 'VARIABLE'.\n"
                  "- Coeficientes: tabla de coeficientes, minimo debe tener N+10 campañas de coeficientes."
                  ).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5))
        
        # Selección de archivos
        ttk.Button(self, text='Seleccionar Lista', command=lambda: self.seleccionar_archivo(self.ruta_lista, "Seleccionar Lista a proyectar"), width=25).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_lista, width=50).grid(row=1, column=1, padx=10, pady=2, sticky='w')

        ttk.Button(self, text='Seleccionar Coeficientes', command=lambda: self.seleccionar_archivo(self.ruta_coef, "Seleccionar Tabla de Coeficientes"), width=25).grid(row=2, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_coef, width=50).grid(row=2, column=1, padx=10, pady=2, sticky='w')

        # Entradas de campaña y año
        ttk.Label(self, text='Campaña a procesar (CC):').grid(row=3, column=0, padx=10, pady=2)
        self.entry_camp = ttk.Entry(self)
        self.entry_camp.grid(row=3, column=1, padx=10, pady=2, sticky='w')

        ttk.Label(self, text='Año (AAAA):').grid(row=4, column=0, padx=10, pady=2)
        self.entry_año = ttk.Entry(self)
        self.entry_año.grid(row=4, column=1, padx=10, pady=2, sticky='w')
        
        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=4, column=0, columnspan=3, sticky='e', padx=10, pady=2)

        ttk.Button(frame_botones, text='Procesar', command=self.ejecutar_hilo).pack(side='left', padx=(0, 5))
        ttk.Button(frame_botones, text='Cancelar', command=self.destroy).pack(side='left')
        
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=6, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
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
            self.procesar_proyectados()
        except Exception as e:
            logger.error(f"Error en el procesamiento de proyectados: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_proyectados(self):
        camp_inicial = self.entry_camp.get()
        año_inicial = self.entry_año.get()
        lista = self.ruta_lista.get()
        coef = self.ruta_coef.get()

        if not all([camp_inicial, año_inicial, lista, coef]):
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            self.ocultar_progreso()
            return
        
        if not (camp_inicial.isdigit() and len(camp_inicial) == 2):
            messagebox.showerror("Error", "La campaña debe tener 2 dígitos. Ejemplo: 01")
            self.ocultar_progreso()
            return

        if not (año_inicial.isdigit() and len(año_inicial) == 4):
            messagebox.showerror("Error", "El año debe tener 4 dígitos. Ejemplo: 2025")
            self.ocultar_progreso()
            return
        
        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        if not carpeta_guardado:
            messagebox.showerror("Error", "Debes seleccionar una carpeta para guardar los resultados.")
            self.ocultar_progreso()
            return
        try:
            resultado=procesar_proyectados_puro(
                ruta_lista=lista,
                ruta_coef=coef,
                camp_inicial=camp_inicial,
                anio_inicial=año_inicial,
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