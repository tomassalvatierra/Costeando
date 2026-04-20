import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from concurrent.futures import Future, ProcessPoolExecutor

from costeando.modulos.procesamiento_compras import procesar_compras_puro
from costeando.utilidades.errores_aplicacion import generar_id_ejecucion
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_compras_en_proceso(parametros: dict) -> dict:
    return procesar_compras_puro(**parametros)


class ComprasWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.ruta_compras = tk.StringVar()
        self.dolar_var = tk.StringVar()

        self.proceso_activo = False
        self.executor_proceso: ProcessPoolExecutor | None = None
        self.future_proceso: Future | None = None
        self.id_verificacion_after: str | None = None
        self.id_ejecucion_activo: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(self, text="Depurador de Compras", font=("Roboto", 24, "bold"))
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        instrucciones = (
            "- Compras: Archivo de pedidos. Convertir la columna 'Codigo' a numero y quitar espacios.\n"
            "- Dolar: Usar punto (.) como separador decimal. Ejemplo: 1050.50."
        )
        lbl_desc = ctk.CTkLabel(self, text=instrucciones, justify="left", text_color="gray70", font=("Roboto", 12))
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        self.crear_fila_selector(2, "Seleccionar Compras", self.ruta_compras)

        frame_dolar = ctk.CTkFrame(self, fg_color="transparent")
        frame_dolar.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        lbl_dolar = ctk.CTkLabel(frame_dolar, text="Cotizacion Dolar:", font=("Roboto", 14))
        lbl_dolar.pack(side="left", padx=(0, 10))
        self.entry_dolar = ctk.CTkEntry(frame_dolar, textvariable=self.dolar_var, width=120, placeholder_text="Ej: 1200.50")
        self.entry_dolar.pack(side="left")

        self.fila_progreso = 4
        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.grid(row=self.fila_progreso, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_forget()

        self.btn_procesar = ctk.CTkButton(
            self,
            text="INICIAR PROCESO",
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_procesar.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        btn = ctk.CTkButton(
            self,
            text=texto_boton,
            command=self.seleccionar_archivo_compras,
            width=200,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")
        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione el archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")

    def seleccionar_archivo_compras(self):
        if self.proceso_activo:
            return
        archivo = filedialog.askopenfilename(title="Seleccionar Compras a depurar", filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            self.ruta_compras.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid(row=self.fila_progreso, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="ew")
        self.progress_bar.start()
        self.btn_procesar.configure(state="disabled", text="Procesando...")
        self.entry_dolar.configure(state="disabled")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.progress_bar.grid_forget()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")
        self.entry_dolar.configure(state="normal")

    def ejecutar_hilo(self):
        if self.proceso_activo:
            return

        if not self.dolar_var.get() or not self.ruta_compras.get():
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return

        try:
            dolar = float(self.dolar_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "El valor de Dolar debe ser numerico.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Selecciona la carpeta para guardar los resultados")
        if not carpeta_guardado:
            return

        self.id_ejecucion_activo = generar_id_ejecucion()
        parametros = {
            "ruta_compras": self.ruta_compras.get(),
            "dolar": dolar,
            "carpeta_guardado": carpeta_guardado,
            "id_ejecucion": self.id_ejecucion_activo,
        }

        self.mostrar_progreso()
        self.proceso_activo = True
        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_compras_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar procesamiento de compras. ID=%s", self.id_ejecucion_activo, exc_info=True)
            self.finalizar_ejecucion()
            mostrar_error_legible(error, self.id_ejecucion_activo)

    def verificar_estado_proceso(self):
        if self.future_proceso is None:
            self.finalizar_ejecucion()
            return

        if not self.future_proceso.done():
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
            return

        self.id_verificacion_after = None
        try:
            self.future_proceso.result()
            messagebox.showinfo("Exito", "El procesamiento finalizo con exito.")
        except Exception as error:
            logger.error("Error en logica de compras. ID=%s", self.id_ejecucion_activo, exc_info=True)
            mostrar_error_legible(error, self.id_ejecucion_activo)
        finally:
            self.finalizar_ejecucion()

    def finalizar_ejecucion(self):
        if self.id_verificacion_after is not None:
            try:
                self.after_cancel(self.id_verificacion_after)
            except Exception:
                pass
            self.id_verificacion_after = None

        self.proceso_activo = False
        self.ocultar_progreso()
        if self.executor_proceso is not None:
            self.executor_proceso.shutdown(wait=False, cancel_futures=True)
        self.executor_proceso = None
        self.future_proceso = None
        self.id_ejecucion_activo = None

    def destroy(self):
        if self.executor_proceso is not None:
            self.executor_proceso.shutdown(wait=False, cancel_futures=True)
            self.executor_proceso = None
            self.future_proceso = None
        super().destroy()
