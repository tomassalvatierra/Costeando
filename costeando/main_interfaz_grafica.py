import customtkinter as ctk
from tkinter import messagebox
import logging

from costeando.utilidades.configuracion_logging import configurar_logging

# --- IMPORTS DE TUS MÓDULOS ---
from costeando.gui.leader_list_window import LeaderListWindow
from costeando.gui.compras_window import ComprasWindow
from costeando.gui.valorizacion_dyc_window import ValorizacionDYCWindow
from costeando.gui.primer_comprando_window import PrimerComprandoWindow
from costeando.gui.segundo_comprando_window import SegundoComprandoWindow
from costeando.gui.primer_produciendo_window import PrimerProduciendoWindow
from costeando.gui.segundo_produciendo_window import SegundoProduciendoWindow
from costeando.gui.proyectados_window import ProyectadosWindow
from costeando.gui.actualizacion_fchs_window import ActualizacionFCHSWindow
from costeando.gui.listado_gral_window import ListadoGralWindow

configurar_logging()
logger = logging.getLogger(__name__)

# Configuración Global de Tema
ctk.set_appearance_mode("Dark")  # "System" (estándar), "Dark", "Light"
ctk.set_default_color_theme("green")  # "blue" (estándar), "green", "dark-blue"

class ProcesadorCostosApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Costeando - Sistema de Gestión")
        self.geometry("1200x720")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_actual = None # Aquí guardaremos la pantalla que se está viendo

        self.vistas = {
            "Leader List": LeaderListWindow,
            "Compras": ComprasWindow,
            "Actualización Fechas": ActualizacionFCHSWindow,
            "Primer Comprando": PrimerComprandoWindow,
            "Segundo Comprando": SegundoComprandoWindow,
            "Primer Produciendo": PrimerProduciendoWindow,
            "Segundo Produciendo": SegundoProduciendoWindow,
            "Proyectados": ProyectadosWindow,
            "Listado General": ListadoGralWindow,
            "Valorización DyC": ValorizacionDYCWindow
        }

        self.crear_sidebar()
        self.crear_area_principal()

    def crear_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(11, weight=1) # Empujar botón salir al fondo

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="COSTEANDO", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        nombres_botones = list(self.vistas.keys())
        
        for i, nombre in enumerate(nombres_botones, start=1):
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=nombre,
                command=lambda n=nombre: self.seleccionar_modulo(n),
                fg_color="transparent",
                text_color=("gray10", "#DCE4EE"), # Color texto (Light, Dark)
                hover_color=("gray70", "gray30"),
                anchor="w",
                height=40
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=2)

        self.btn_salir = ctk.CTkButton(
            self.sidebar_frame,
            text="Salir",
            command=self.cerrar_aplicacion,
            fg_color="#c0392b",
            hover_color="#922b21",
            height=40
        )
        self.btn_salir.grid(row=12, column=0, padx=20, pady=20, sticky="ew")

    def crear_area_principal(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.lbl_bienvenida = ctk.CTkLabel(
            self.main_container, 
            text="Seleccione un módulo del menú lateral para comenzar.",
            font=ctk.CTkFont(size=18),
            text_color="gray50"
        )
        self.lbl_bienvenida.place(relx=0.5, rely=0.5, anchor="center")

    def seleccionar_modulo(self, nombre_modulo):
        #Lógica para cambiar de pantalla
        
        if self.frame_actual is not None:
            self.frame_actual.destroy()
        
        # Ocultar mensaje de bienvenida si existe
        if hasattr(self, 'lbl_bienvenida') and self.lbl_bienvenida.winfo_exists():
            self.lbl_bienvenida.destroy()

        # Instanciar nueva pantalla
        ClaseModulo = self.vistas.get(nombre_modulo)
        
        if ClaseModulo:
            try:
                logger.info(f"Cargando módulo: {nombre_modulo}")
                
                # Instanciamos la clase pasándole el contenedor principal como 'master'
                self.frame_actual = ClaseModulo(self.main_container)
                
                # Hacemos que ocupe todo el espacio disponible
                self.frame_actual.pack(fill="both", expand=True)
                
            except Exception as e:
                logger.error(f"Error cargando {nombre_modulo}: {e}", exc_info=True)
                messagebox.showerror("Error", f"No se pudo cargar el módulo {nombre_modulo}.\n\nDetalle: {e}")

    def cerrar_aplicacion(self):
        # Aquí podrías agregar chequeos si hay hilos corriendo (opcional)
        if messagebox.askyesno("Salir", "¿Desea cerrar la aplicación?"):
            self.destroy()

if __name__ == "__main__":
    app = ProcesadorCostosApp()
    app.mainloop()