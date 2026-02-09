import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import logging

# Importamos la lógica de negocio original
from costeando.modulos.procesamiento_compras import procesar_compras_puro

logger = logging.getLogger(__name__)

class ComprasWindow(ctk.CTkFrame): # <-- Heredamos de CTkFrame
    def __init__(self, master):
        super().__init__(master)
        
        # Variables
        self.ruta_compras = tk.StringVar()
        self.dolar_var = tk.StringVar() # Usamos StringVar para facilitar el control
        
        # Configuración del Grid
        self.grid_columnconfigure(1, weight=1)

        # Crear interfaz
        self.crear_interfaz()

    def crear_interfaz(self):
        # --- TÍTULO ---
        lbl_titulo = ctk.CTkLabel(
            self, 
            text="Depurador de Compras", 
            font=("Roboto", 24, "bold")
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        # --- INSTRUCCIONES ---
        # Unimos las instrucciones en un texto claro
        instrucciones = (
            "• Compras: Archivo de pedidos. Convierta la columna 'Código' a número y quite espacios.\n"
            "• Dólar: Utilice el PUNTO (.) como separador decimal (Ej: 1050.50)."
        )
        lbl_desc = ctk.CTkLabel(
            self, 
            text=instrucciones,
            justify="left",
            text_color="gray70",
            font=("Roboto", 12)
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        # --- SELECCIÓN DE ARCHIVO ---
        self.crear_fila_selector(2, "Seleccionar Compras", self.ruta_compras)

        # --- CAMPO DÓLAR ---
        # Lo ponemos en un frame aparte para alinearlo bien
        frame_dolar = ctk.CTkFrame(self, fg_color="transparent")
        frame_dolar.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

        lbl_dolar = ctk.CTkLabel(frame_dolar, text="Cotización Dólar:", font=("Roboto", 14))
        lbl_dolar.pack(side="left", padx=(0, 10))

        self.entry_dolar = ctk.CTkEntry(
            frame_dolar, 
            textvariable=self.dolar_var, 
            width=120,
            placeholder_text="Ej: 1200.50"
        )
        self.entry_dolar.pack(side="left")

        # --- BARRA DE PROGRESO ---
        self.progress_bar = ctk.CTkProgressBar(self, mode='indeterminate')
        self.progress_bar.grid(row=4, column=0, columnspan=3, padx=20, pady=(30, 10), sticky='ew')
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        # --- BOTÓN PROCESAR ---
        self.btn_procesar = ctk.CTkButton(
            self, 
            text='INICIAR PROCESO', 
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870"
        )
        self.btn_procesar.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        """Helper para la fila de archivo (mismo estilo que otros módulos)"""
        btn = ctk.CTkButton(
            self, 
            text=texto_boton, 
            command=self.seleccionar_archivo_compras,
            width=200,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione el archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")

    def seleccionar_archivo_compras(self):
        archivo = filedialog.askopenfilename(title="Seleccionar Compras a depurar", filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            self.ruta_compras.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid()
        self.progress_bar.start()
        self.btn_procesar.configure(state="disabled", text="Procesando...")
        self.entry_dolar.configure(state="disabled")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")
        self.entry_dolar.configure(state="normal")

    def ejecutar_hilo(self):
        # Validación rápida antes de lanzar hilo
        if not self.dolar_var.get() or not self.ruta_compras.get():
             messagebox.showerror("Error", "Todos los campos son obligatorios.")
             return
        
        self.mostrar_progreso()
        threading.Thread(target=self.procesar_con_progreso, daemon=True).start()

    def procesar_con_progreso(self):
        try:
            self.procesar_compras()
        except Exception as e:
            logger.error(f"Error en el procesamiento de compras: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ha ocurrido un error: {str(e)}"))
            self.after(0, self.ocultar_progreso)

    def procesar_compras(self):
        # 1. Validar Valor Dolar
        try:
            # Reemplazamos coma por punto por si el usuario se equivocó
            valor_raw = self.dolar_var.get().replace(",", ".")
            dolar = float(valor_raw)
        except ValueError:
            self.after(0, lambda: messagebox.showerror("Error", "El valor de Dólar debe ser numérico."))
            self.after(0, self.ocultar_progreso)
            return

        compras = self.ruta_compras.get()
        
        # 2. Pedir Carpeta (Ojo: esto bloquea el hilo, pero es aceptable aquí)
        carpeta_guardado = filedialog.askdirectory(title='Selecciona la carpeta para guardar los resultados')
        
        if not carpeta_guardado:
            # Cancelado
            self.after(0, self.ocultar_progreso)
            return

        try:
            # 3. Lógica de negocio
            procesar_compras_puro(
                ruta_compras=compras,
                dolar=dolar,
                carpeta_guardado=carpeta_guardado
            )
            
            self.after(0, self.ocultar_progreso)
            self.after(0, lambda: messagebox.showinfo("Éxito", "El procesamiento ha finalizado con éxito."))
            
        except Exception as e:
            logger.error(f"Error en lógica compras: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error:\n{e}"))
            self.after(0, self.ocultar_progreso)