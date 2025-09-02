import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from costeando.modulos.procesamiento_listado_gral import procesar_listado_gral_puro

logger = logging.getLogger(__name__)

class ListadoGralWindow(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title('Listado General Completo')
        self.geometry("+600+200")
        
        # Variables
        self.ruta_produciendo = tk.StringVar()
        self.ruta_comprando = tk.StringVar()
        self.ruta_costo_primo = tk.StringVar()
        self.ruta_base_descuentos = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        self.ruta_mdo = tk.StringVar()
        self.ruta_leader_list = tk.StringVar()
        self.ruta_compilado_fechas_ult_compra = tk.StringVar()
        
        # Crear interfaz
        self.crear_interfaz()
           
    def crear_interfaz(self):
        # Instrucciones
        ttk.Label(self, text=
            "- Produciendo: archivo de la campaña a procesar.\n"
            "- Comprando: archivo de la campaña a procesar.\n"
            "- Costo primo: maestro con costos primo original.\n"
            "- Base descuentos: ultima base utilizada.\n"
            "- Listado: archivo el cual quiere completar.\n"
            "- Mano de Obra: tiene que tener las tres manos de obra incluidas.\n"
            "- Leader List: puede ser Leader List original o el depurado\n"
            "- Fch Utl Compra: archivo compilado de fechas ult compra."
        ).grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky='w')

        # Selección de archivos (cada uno en su fila)
        ttk.Button(self, text='Seleccionar lista', command=lambda: self.seleccionar_archivo(self.ruta_listado, "Seleccionar la lista a procesar"), width=25).grid(row=1, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_listado, width=50).grid(row=1, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar produciendo', command=lambda: self.seleccionar_archivo(self.ruta_produciendo, "Seleccionar archivo Produciendo N"), width=25).grid(row=2, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_produciendo, width=50).grid(row=2, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar comprando', command=lambda: self.seleccionar_archivo(self.ruta_comprando, "Seleccionar archivo Comprando N"), width=25).grid(row=3, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_comprando, width=50).grid(row=3, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar costo primo', command=lambda: self.seleccionar_archivo(self.ruta_costo_primo, "Seleccionar archivo maestro Costo primo"), width=25).grid(row=4, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_costo_primo, width=50).grid(row=4, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar base descuento', command=lambda: self.seleccionar_archivo(self.ruta_base_descuentos, "Seleccionar base de descuentos especiales"), width=25).grid(row=5, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_base_descuentos, width=50).grid(row=5, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar MDO', command=lambda: self.seleccionar_archivo(self.ruta_mdo, "Seleccionar archivo Mano de obra"), width=25).grid(row=6, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_mdo, width=50).grid(row=6, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar Leader List', command=lambda: self.seleccionar_archivo(self.ruta_leader_list, "Seleccionar archivo Leader list"), width=25).grid(row=7, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_leader_list, width=50).grid(row=7, column=1, padx=5, pady=2)

        ttk.Button(self, text='Seleccionar Compilado fchs', command=lambda: self.seleccionar_archivo(self.ruta_compilado_fechas_ult_compra, "Seleccionar archivo compilado de fechas ult compra"), width=25).grid(row=8, column=0, padx=5, pady=2)
        ttk.Entry(self, textvariable=self.ruta_compilado_fechas_ult_compra, width=50).grid(row=8, column=1, padx=5, pady=2)

        # Entradas de campaña y año
        ttk.Label(self, text='Campaña (CC):').grid(row=9, column=0, padx=5, pady=2)
        self.entry_campaña = ttk.Entry(self)
        self.entry_campaña.grid(row=9, column=1, padx=5, pady=2, sticky='w')

        ttk.Label(self, text='Año (AAAA):').grid(row=10, column=0, padx=5, pady=2)
        self.entry_anio = ttk.Entry(self)
        self.entry_anio.grid(row=10, column=1, padx=5, pady=2, sticky='w')

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate')
        self.progress_bar.grid(row=11, column=0, columnspan=2, padx=10, pady=(5, 10), sticky='ew')
        self.progress_bar.grid_remove()

        # Botones
        frame_botones = ttk.Frame(self)
        frame_botones.grid(row=10, column=0, columnspan=2, sticky='e', padx=5, pady=2)
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
            self.procesar_datos_dyc()
        except Exception as e:
            logger.error(f"Error en el procesamiento del listado general: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}")
            
    def procesar_datos_dyc(self):
        campania = self.entry_campaña.get()
        anio = self.entry_anio.get()
        listado = self.ruta_listado.get()
        produciendo = self.ruta_produciendo.get()
        comprando = self.ruta_comprando.get()
        costo_primo = self.ruta_costo_primo.get()
        base_descuentos = self.ruta_base_descuentos.get()
        mano_de_obra = self.ruta_mdo.get()
        leader_list = self.ruta_leader_list.get()
        compilado_fechas_ult_compra = self.ruta_compilado_fechas_ult_compra.get()

        if not campania or not anio:
            messagebox.showerror("Error", "Campaña y Año son campos obligatorios.")
            self.ocultar_progreso()
            return
        if not all([listado, produciendo, comprando, costo_primo, base_descuentos, mano_de_obra, leader_list, compilado_fechas_ult_compra]):
            messagebox.showerror("Error", "Todos los archivos son obligatorios.")
            self.ocultar_progreso()
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            messagebox.showinfo("Cancelado", "El proceso ha sido cancelado por el usuario.")
            self.ocultar_progreso()
            return
        try:
            resultado=procesar_listado_gral_puro(
                ruta_produciendo=produciendo,
                ruta_comprando=comprando,
                ruta_costo_primo=costo_primo,
                ruta_base_descuentos=base_descuentos,
                ruta_listado=listado,
                ruta_mdo=mano_de_obra,
                ruta_leader_list=leader_list,
                ruta_compilado_fechas_ult_compra=compilado_fechas_ult_compra,
                campania=campania,
                anio=anio,
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