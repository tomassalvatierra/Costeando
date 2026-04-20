import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from concurrent.futures import Future, ProcessPoolExecutor

from costeando.modulos.procesamiento_proyectados import procesar_proyectados_puro
from costeando.utilidades.manejo_errores_gui import mostrar_error_legible

logger = logging.getLogger(__name__)


def ejecutar_proyectados_en_proceso(parametros: dict) -> dict:
    return procesar_proyectados_puro(**parametros)


class ProyectadosWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.ruta_lista = tk.StringVar()
        self.ruta_coef = tk.StringVar()
        self.campania_var = tk.StringVar()
        self.anio_var = tk.StringVar()

        self.proceso_activo = False
        self.executor_proceso: ProcessPoolExecutor | None = None
        self.future_proceso: Future | None = None
        self.id_verificacion_after: str | None = None

        self.grid_columnconfigure(1, weight=1)
        self.crear_interfaz()

    def crear_interfaz(self):
        lbl_titulo = ctk.CTkLabel(self, text="Costos Proyectados", font=("Roboto", 24, "bold"))
        lbl_titulo.grid(row=0, column=0, columnspan=3, padx=20, pady=(30, 10), sticky="w")

        instrucciones = (
            "- Lista: Debe tener columnas 'COSTO LISTA ACC' y 'VARIABLE'.\n"
            "- Coeficientes: Tabla con minimo N+10 campanias futuras."
        )
        lbl_desc = ctk.CTkLabel(self, text=instrucciones, justify="left", text_color="gray70", font=("Roboto", 12))
        lbl_desc.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 20), sticky="w")

        self.crear_fila_selector(2, "Seleccionar Lista", self.ruta_lista)
        self.crear_fila_selector(3, "Seleccionar Coeficientes", self.ruta_coef)

        frame_datos = ctk.CTkFrame(self, fg_color="transparent")
        frame_datos.grid(row=4, column=0, columnspan=3, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(frame_datos, text="Campania (CC):").pack(side="left", padx=(0, 10))
        self.entry_campania = ctk.CTkEntry(frame_datos, textvariable=self.campania_var, width=80, placeholder_text="Ej: 01")
        self.entry_campania.pack(side="left", padx=(0, 30))

        ctk.CTkLabel(frame_datos, text="Anio (AAAA):").pack(side="left", padx=(0, 10))
        self.entry_anio = ctk.CTkEntry(frame_datos, textvariable=self.anio_var, width=80, placeholder_text="Ej: 2025")
        self.entry_anio.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress_bar.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="ew")
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

        self.btn_procesar = ctk.CTkButton(
            self,
            text="INICIAR PROYECCION",
            command=self.ejecutar_hilo,
            height=45,
            font=("Roboto", 14, "bold"),
            fg_color="#1f6aa5",
            hover_color="#144870",
        )
        self.btn_procesar.grid(row=6, column=0, columnspan=3, padx=20, pady=(10, 20), sticky="ew")

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
        entry = ctk.CTkEntry(self, textvariable=variable, placeholder_text="Seleccione archivo...")
        entry.grid(row=row, column=1, columnspan=2, padx=(0, 20), pady=8, sticky="ew")

    def seleccionar_archivo(self, variable, titulo):
        if self.proceso_activo:
            return
        archivo = filedialog.askopenfilename(title=titulo, filetypes=[("Archivos Excel", "*.xlsx")])
        if archivo:
            variable.set(archivo)

    def mostrar_progreso(self):
        self.progress_bar.grid(row=5, column=0, columnspan=3, padx=20, pady=(10, 10), sticky="ew")
        self.progress_bar.start()
        self.btn_procesar.configure(state="disabled", text="Procesando...")
        self.entry_campania.configure(state="disabled")
        self.entry_anio.configure(state="disabled")

    def ocultar_progreso(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.progress_bar.grid_forget()
        self.btn_procesar.configure(state="normal", text="INICIAR PROYECCION")
        self.entry_campania.configure(state="normal")
        self.entry_anio.configure(state="normal")

    def ejecutar_hilo(self):
        if self.proceso_activo:
            return

        campania = self.campania_var.get()
        anio = self.anio_var.get()
        ruta_lista = self.ruta_lista.get()
        ruta_coef = self.ruta_coef.get()

        if not campania or not anio:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return
        if not (campania.isdigit() and len(campania) == 2):
            messagebox.showerror("Error", "La campania debe tener 2 digitos. Ejemplo: 01")
            return
        if not (anio.isdigit() and len(anio) == 4):
            messagebox.showerror("Error", "El anio debe tener 4 digitos. Ejemplo: 2025")
            return
        if not all([ruta_lista, ruta_coef]):
            messagebox.showerror("Error", "Debe seleccionar ambos archivos.")
            return

        carpeta_guardado = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if not carpeta_guardado:
            return

        self.mostrar_progreso()
        self.proceso_activo = True
        parametros = {
            "ruta_lista": ruta_lista,
            "ruta_coef": ruta_coef,
            "camp_inicial": campania,
            "anio_inicial": anio,
            "carpeta_guardado": carpeta_guardado,
        }

        try:
            self.executor_proceso = ProcessPoolExecutor(max_workers=1)
            self.future_proceso = self.executor_proceso.submit(ejecutar_proyectados_en_proceso, parametros)
            self.id_verificacion_after = self.after(150, self.verificar_estado_proceso)
        except Exception as error:
            logger.error("No se pudo iniciar proceso proyectados: %s", str(error), exc_info=True)
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
            messagebox.showinfo("Exito", "El procesamiento finalizo con exito.")
        except Exception as error:
            logger.error("Error en logica proyectados: %s", str(error), exc_info=True)
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
