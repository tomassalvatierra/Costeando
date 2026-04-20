import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from concurrent.futures import Future, ProcessPoolExecutor

from costeando.modulos.procesamiento_primer_produciendo import procesar_primer_produciendo
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_primer_produciendo_en_proceso(parametros: dict) -> dict:
    return procesar_primer_produciendo(**parametros)


class PrimerProduciendoWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.ruta_maestro_produciendo = tk.StringVar()
        self.ruta_produciendo_anterior = tk.StringVar()
        self.ruta_stock = tk.StringVar()
        self.ruta_descuentos_especiales = tk.StringVar()
        self.ruta_rotacion = tk.StringVar()
        self.ruta_estructuras = tk.StringVar()

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
            text="Primer Produciendo",
            font=("Roboto", 24, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(20, 10), sticky="w")

        instrucciones = (
            "- Maestro: Original TOTVS.\n"
            "- Produciendo: Archivo produciendo (N-1).\n"
            "- Stock: Informe 'Stock Actual Valorizado por Producto'.\n"
            "- Base Descuentos: La mas actualizada.\n"
            "- Rotacion: Informe de rotacion."
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
            ("Seleccionar Maestro", self.ruta_maestro_produciendo),
            ("Seleccionar Produciendo N-1", self.ruta_produciendo_anterior),
            ("Seleccionar Stock", self.ruta_stock),
            ("Seleccionar Base Descuentos", self.ruta_descuentos_especiales),
            ("Seleccionar Rotacion", self.ruta_rotacion),
            ("Seleccionar Estructuras", self.ruta_estructuras),
        ]

        base_row = 2
        for i, (texto, variable) in enumerate(archivos_config):
            self.crear_fila_selector(base_row + i, texto, variable)

        last_row = base_row + len(archivos_config)
        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=last_row, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(frame_datos, text="Campania (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(
            frame_datos,
            textvariable=self.campania_var,
            width=80,
            placeholder_text="Ej: 05",
        )
        self.entry_campania.pack(side="left", padx=(0, 30))

        ctk.CTkLabel(frame_datos, text="Anio (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_anio = ctk.CTkEntry(
            frame_datos,
            textvariable=self.anio_var,
            width=80,
            placeholder_text="Ej: 2024",
        )
        self.entry_anio.pack(side="left")

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
        self.entry_campania.configure(state="disabled")
        self.entry_anio.configure(state="disabled")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.progress_bar.grid_forget()
        self.btn_procesar.configure(state="normal", text="INICIAR PROCESO")
        self.entry_campania.configure(state="normal")
        self.entry_anio.configure(state="normal")

    def ejecutar_hilo(self):
        if self.proceso_activo:
            return

        if not self.campania_var.get() or not self.anio_var.get():
            messagebox.showerror("Error", "Debe completar Campania y Anio.")
            return

        archivos = [
            self.ruta_maestro_produciendo.get(),
            self.ruta_stock.get(),
            self.ruta_descuentos_especiales.get(),
            self.ruta_produciendo_anterior.get(),
            self.ruta_rotacion.get(),
            self.ruta_estructuras.get(),
        ]
        if not all(archivos):
            messagebox.showerror("Error", "Debe seleccionar todos los archivos requeridos.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            return

        parametros = {
            "campania_actual": self.campania_var.get(),
            "anio_actual": self.anio_var.get(),
            "ruta_produciendo_anterior": self.ruta_produciendo_anterior.get(),
            "ruta_maestro_produciendo": self.ruta_maestro_produciendo.get(),
            "ruta_stock": self.ruta_stock.get(),
            "ruta_descuentos_especiales": self.ruta_descuentos_especiales.get(),
            "ruta_rotacion": self.ruta_rotacion.get(),
            "ruta_estructuras": self.ruta_estructuras.get(),
            "ruta_salida": carpeta_guardado,
        }

        self.mostrar_progreso()
        self.proceso_activo = True
        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_primer_produciendo_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar Primer Produciendo: %s", str(error), exc_info=True)
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
            logger.error("Error en Primer Produciendo: %s", str(error), exc_info=True)
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
