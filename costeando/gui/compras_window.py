import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from costeando.modulos.procesamiento_compras import procesar_compras_puro

logger = logging.getLogger(__name__)

class ComprasWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Depurador de Compras')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_compras = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
                  "- Compras: archivo pedidos de compra, convierta la columna 'Codigo' a numero y quitele los espacios.\n"
                  "- Dolar: valor del dólar correspondiente, utilize el punto como separdor decimal y no la coma."
                  ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10,5), sticky='w')

        # Selección de archivo
        ttk.Button(self, text="Seleccionar Compras", command=self.seleccionar_archivo_compras).grid(row=1, column=0, padx=10, pady=2)
        ttk.Entry(self, textvariable=self.ruta_compras, width=55).grid(row=1, column=1, padx=10, pady=2, sticky='w')
        
        # Campo dólar
        ttk.Label(self, text="Dolar:").grid(row=2, column=0, padx=10, pady=2)
        self.entry_dolar = ttk.Entry(self, width=10)
        self.entry_dolar.grid(row=2, column=1, padx=10, pady=2, sticky='w')
        
        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=2, column=0, columnspan=2, sticky='e', padx=10, pady=2)

        ttk.Button(frame_botones, text='Procesar', command=self.ejecutar_hilo).pack(side='left', padx=(0, 5))
        ttk.Button(frame_botones, text='Cancelar', command=self.destroy).pack(side='left')
         
        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()


    def seleccionar_archivo_compras(self):
        archivo = filedialog.askopenfilename(title="Seleccionar Comprar a depurar", filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            self.ruta_compras.set(archivo)
            
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
            self.procesar_compras()
        except Exception as e:
            logger.error(f"Error en el procesamiento de compras: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_compras(self):
        try:
            dolar = float(self.entry_dolar.get()) 
        except ValueError:
            messagebox.showerror("Error", "El valor de Dolar es obligatorio y debe ser un número.")
            return

        compras = self.ruta_compras.get()

        if not all([dolar, compras]):
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        if not carpeta_guardado:
            messagebox.showerror("Error", "Debes seleccionar una carpeta para guardar los resultados.")
            self.ocultar_progreso()
            return
        try:
            resultado=procesar_compras_puro(
                ruta_compras=compras,
                dolar=dolar,
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