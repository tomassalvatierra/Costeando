import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from concurrent.futures import Future, ProcessPoolExecutor

from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_primer_comprando_en_proceso(parametros: dict) -> dict:
    return procesar_primer_comprando(**parametros)


class PrimerComprandoWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.ruta_maestro = tk.StringVar()
        self.ruta_compras = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        self.ruta_dto_especiales = tk.StringVar()
        self.ruta_listado = tk.StringVar()
        self.ruta_calculo_comprando_ant = tk.StringVar()
        self.ruta_ficha = tk.StringVar()

        self.campana_var = tk.StringVar()
        self.anio_var = tk.StringVar()
        self.mdo_var = tk.StringVar()
        self.indice_a_var = tk.StringVar()
        self.indice_b_var = tk.StringVar()

        self.proceso_activo = False
        self.executor_proceso: ProcessPoolExecutor | None = None
        self.future_proceso: Future | None = None
        self.id_verificacion_after: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="Primer Comprando",
            font=("Roboto", 24, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        instrucciones = (
            "- Maestro: Original TOTVS.\n"
            "- Compras: Archivo 'Compras y Cotizaciones revisadas'.\n"
            "- Stock: 'Stock Actual Valorizado'.\n"
            "- Lista (N-1): Debe tener 'COSTOS LISTA ACC'.\n"
            "- Comprando (N-1): Debe tener 'Costo sin Descuento CXX'."
        )
        lbl_desc = ctk.CTkLabel(
            self,
            text=instrucciones,
            justify="left",
            text_color="gray70",
            font=("Roboto", 12),
        )
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        archivos_config = [
            ("Seleccionar Maestro", self.ruta_maestro),
            ("Seleccionar Compras", self.ruta_compras),
            ("Seleccionar Stock", self.ruta_stock),
            ("Seleccionar Base Descuentos", self.ruta_dto_especiales),
            ("Seleccionar Lista N-1", self.ruta_listado),
            ("Seleccionar Comprando N-1", self.ruta_calculo_comprando_ant),
            ("Seleccionar Ficha", self.ruta_ficha),
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        last_row = base_row + len(archivos_config)
        frame_params = ctk.CTkFrame(self, fg_color="transparent")
        frame_params.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        self.crear_input_param(frame_params, "Campania (CC):", self.campana_var, 0, 0)
        self.crear_input_param(frame_params, "Anio (AAAA):", self.anio_var, 0, 1)
        self.crear_input_param(frame_params, "Mano Obra:", self.mdo_var, 0, 2)
        self.crear_input_param(frame_params, "Indice A:", self.indice_a_var, 1, 0)
        self.crear_input_param(frame_params, "Indice B:", self.indice_b_var, 1, 1)

        self.fila_progreso = last_row + 1
        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.grid(row=self.fila_progreso, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="ew")
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
        self.btn_procesar.grid(row=last_row + 2, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="ew")

    def crear_fila_selector(self, row, texto_boton, variable):
        btn = ctk.CTkButton(
            self,
            text=texto_boton,
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=220,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )
        btn.grid(row=row, column=0, padx=(20, 10), pady=4, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")

    def crear_input_param(self, parent, label_text, variable, row, col):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")
        ctk.CTkLabel(frame, text=label_text, font=("Roboto", 12)).pack(anchor="w")
        ctk.CTkEntry(frame, textvariable=variable, width=100).pack()

    def seleccionar_archivo(self, variable, titulo):
        if self.proceso_activo:
            return
        archivo = filedialog.askopenfilename(title=titulo, filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            variable.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid(row=self.fila_progreso, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="ew")
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

        if not all(
            [
                self.campana_var.get(),
                self.anio_var.get(),
                self.mdo_var.get(),
                self.indice_a_var.get(),
                self.indice_b_var.get(),
            ]
        ):
            messagebox.showerror("Error", "Debe completar todos los parametros numericos.")
            return

        archivos = [
            self.ruta_maestro.get(),
            self.ruta_compras.get(),
            self.ruta_stock.get(),
            self.ruta_dto_especiales.get(),
            self.ruta_listado.get(),
            self.ruta_calculo_comprando_ant.get(),
            self.ruta_ficha.get(),
        ]
        if not all(archivos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            return

        try:
            mano_de_obra = float(self.mdo_var.get().replace(",", "."))
            indice_a = float(self.indice_a_var.get().replace(",", "."))
            indice_b = float(self.indice_b_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Error", "Mano de Obra e indices deben ser numericos.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            return

        parametros = {
            "campania": self.campana_var.get(),
            "anio": self.anio_var.get(),
            "indice_a": indice_a,
            "indice_b": indice_b,
            "mano_de_obra": mano_de_obra,
            "ruta_maestro": self.ruta_maestro.get(),
            "ruta_compras": self.ruta_compras.get(),
            "ruta_stock": self.ruta_stock.get(),
            "ruta_dto_especiales": self.ruta_dto_especiales.get(),
            "ruta_listado": self.ruta_listado.get(),
            "ruta_calculo_comprando_ant": self.ruta_calculo_comprando_ant.get(),
            "ruta_ficha": self.ruta_ficha.get(),
            "ruta_salida": carpeta_guardado,
        }

        self.mostrar_progreso()
        self.proceso_activo = True
        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_primer_comprando_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar Primer Comprando: %s", str(error), exc_info=True)
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
            logger.error("Error en Primer Comprando: %s", str(error), exc_info=True)
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
