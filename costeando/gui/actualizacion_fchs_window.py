import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from concurrent.futures import Future, ProcessPoolExecutor

from costeando.modulos.procesamiento_actualizacion_fchs import procesar_actualizacion_fchs_puro
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_actualizacion_fchs_en_proceso(parametros: dict) -> dict:
    return procesar_actualizacion_fchs_puro(**parametros)


class ActualizacionFCHSWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.ruta_estructuras = tk.StringVar()
        self.ruta_compras = tk.StringVar()
        self.ruta_maestro = tk.StringVar()
        self.ruta_ordenes_apuntadas = tk.StringVar()

        self.proceso_activo = False
        self.executor_proceso: ProcessPoolExecutor | None = None
        self.future_proceso: Future | None = None
        self.id_verificacion_after: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="Actualizacion de Fechas",
            font=("Roboto", 24, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        lbl_desc = ctk.CTkLabel(
            self,
            text=(
                "- Estructuras: Archivo original por nivel (TOTVS).\n"
                "- Maestro: Archivo original TOTVS.\n"
                "- Compras: Archivo de compras y cotizaciones revisadas.\n"
                "- Ordenes Apuntadas: Archivo original TOTVS."
            ),
            justify="left",
            text_color="gray70",
            font=("Roboto", 12),
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        self.crear_fila_selector(2, "Seleccionar Estructuras", self.ruta_estructuras)
        self.crear_fila_selector(3, "Seleccionar Maestro", self.ruta_maestro)
        self.crear_fila_selector(4, "Seleccionar Compras", self.ruta_compras)
        self.crear_fila_selector(5, "Seleccionar Ord. Apuntadas", self.ruta_ordenes_apuntadas)

        self.fila_progreso = 6
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
        self.btn_procesar.grid(row=7, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        btn = ctk.CTkButton(
            self,
            text=texto_boton,
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=200,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=8, sticky="w")

        entry = ctk.CTkEntry(
            self,
            textvariable=variable,
            placeholder_text="Seleccione un archivo...",
        )
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")

    def seleccionar_archivo(self, variable, titulo):
        if self.proceso_activo:
            return
        archivo = filedialog.askopenfilename(title=titulo, filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            variable.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid(row=self.fila_progreso, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="ew")
        self.progress_bar.start()
        self.btn_procesar.configure(state="disabled", text="Procesando...")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.progress_bar.grid_forget()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")

    def ejecutar_hilo(self):
        if self.proceso_activo:
            return

        archivos_requeridos = [
            self.ruta_estructuras.get(),
            self.ruta_compras.get(),
            self.ruta_maestro.get(),
            self.ruta_ordenes_apuntadas.get(),
        ]
        if not all(archivos_requeridos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de guardado")
        if not carpeta_guardado:
            return

        parametros = {
            "ruta_estructuras": self.ruta_estructuras.get(),
            "ruta_compras": self.ruta_compras.get(),
            "ruta_maestro": self.ruta_maestro.get(),
            "ruta_ordenes_apuntadas": self.ruta_ordenes_apuntadas.get(),
            "carpeta_guardado": carpeta_guardado,
        }

        self.mostrar_progreso()
        self.proceso_activo = True
        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_actualizacion_fchs_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar Actualizacion FCHS: %s", str(error), exc_info=True)
            self.finalizar_ejecucion()
            mostrar_error_legible(error)

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
            messagebox.showinfo("Exito", "El procesamiento ha finalizado con exito.")
        except Exception as error:
            logger.error("Error en Actualizacion FCHS: %s", str(error), exc_info=True)
            mostrar_error_legible(error)
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

    def destroy(self):
        if self.executor_proceso is not None:
            self.executor_proceso.shutdown(wait=False, cancel_futures=True)
            self.executor_proceso = None
            self.future_proceso = None
        super().destroy()
