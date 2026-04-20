import logging
from concurrent.futures import Future, ProcessPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from costeando.modulos.procesamiento_segundo_produciendo import procesar_segundo_produciendo
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_segundo_produciendo_en_proceso(parametros: dict) -> dict:
    return procesar_segundo_produciendo(**parametros)


class SegundoProduciendoWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.ruta_segundo_produciendo = tk.StringVar()
        self.ruta_base_especiales = tk.StringVar()
        self.ruta_importador_descuentos = tk.StringVar()

        self.fecha_inicio_var = tk.StringVar()
        self.fecha_fin_var = tk.StringVar()
        self.campania_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        self.proceso_activo = False
        self.executor_proceso: ProcessPoolExecutor | None = None
        self.future_proceso: Future | None = None
        self.id_verificacion_after: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="Segundo Produciendo",
            font=("Roboto", 24, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        instrucciones = (
            "- Produciendo: Archivo resultante de la primera etapa.\n"
            "- Base Descuentos: La mas actualizada.\n"
            "- Importador Dtos: Opcional, si desea agregar descuentos.\n"
            "- Fechas: Formato dd/mm/aaaa."
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
            ("Seleccionar Produciendo (Etapa 1)", self.ruta_segundo_produciendo),
            ("Seleccionar Base Descuentos", self.ruta_base_especiales),
            ("Seleccionar Importador Dtos", self.ruta_importador_descuentos),
        ]
        base_row = 2
        for indice, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + indice, texto, variable)

        ultima_fila = base_row + len(archivos_config)
        frame_parametros = ctk.CTkFrame(self, fg_color="transparent")
        frame_parametros.grid(row=ultima_fila, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        self.crear_input_param(
            frame_parametros,
            "Inicio (dd/mm/aaaa):",
            self.fecha_inicio_var,
            0,
            0,
            "Ej: 01/05/2024",
        )
        self.crear_input_param(
            frame_parametros,
            "Fin (dd/mm/aaaa):",
            self.fecha_fin_var,
            0,
            1,
            "Ej: 31/05/2024",
        )
        self.crear_input_param(frame_parametros, "Campania (CC):", self.campania_var, 1, 0, "Ej: 05")
        self.crear_input_param(frame_parametros, "Anio (AAAA):", self.anio_var, 1, 1, "Ej: 2024")

        self.fila_progreso = ultima_fila + 1
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
        self.btn_procesar.grid(row=ultima_fila + 2, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="ew")

    def crear_fila_selector(self, fila, texto_boton, variable):
        boton = ctk.CTkButton(
            self,
            text=texto_boton,
            command=lambda: self.seleccionar_archivo(variable, texto_boton),
            width=220,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
        )
        boton.grid(row=fila, column=0, padx=(20, 10), pady=4, sticky="w")

        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=fila, column=1, columnspan=2, padx=(0, 20), pady=4, sticky="ew")

    def crear_input_param(self, parent, label_text, variable, fila, columna, placeholder=""):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=fila, column=columna, padx=10, pady=8, sticky="w")
        ctk.CTkLabel(frame, text=label_text, font=("Roboto", 12)).pack(anchor="w")
        ctk.CTkEntry(frame, textvariable=variable, width=140, placeholder_text=placeholder).pack()

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

        if not all([self.fecha_inicio_var.get(), self.fecha_fin_var.get(), self.campania_var.get(), self.anio_var.get()]):
            messagebox.showerror("Error", "Debe completar todas las fechas y datos de campania.")
            return

        ruta_produciendo = self.ruta_segundo_produciendo.get()
        ruta_base = self.ruta_base_especiales.get()
        if not ruta_produciendo or not ruta_base:
            messagebox.showerror("Error", "Produciendo y Base Descuentos son obligatorios.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            return

        parametros = {
            "ruta_produciendo": ruta_produciendo,
            "ruta_base_especiales": ruta_base,
            "ruta_importador_descuentos": self.ruta_importador_descuentos.get() or None,
            "campania": self.campania_var.get(),
            "anio": self.anio_var.get(),
            "fecha_compras_inicio": self.fecha_inicio_var.get(),
            "fecha_compras_final": self.fecha_fin_var.get(),
            "carpeta_guardado": carpeta_guardado,
        }

        self.mostrar_progreso()
        self.proceso_activo = True
        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_segundo_produciendo_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar Segundo Produciendo: %s", str(error), exc_info=True)
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
            logger.error("Error en Segundo Produciendo: %s", str(error), exc_info=True)
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
