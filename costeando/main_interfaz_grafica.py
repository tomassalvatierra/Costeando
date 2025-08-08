import tkinter as tk
from tkinter import messagebox, ttk
import threading
import logging

from costeando.utilidades.configuracion_logging import configurar_logging

# Imports de las ventanas individuales
from costeando.gui.compras_window import ComprasWindow
from costeando.gui.leader_list_window import LeaderListWindow
from costeando.gui.valorizacion_dyc_window import ValorizacionDYCWindow
from costeando.gui.proyectados_window import ProyectadosWindow
from costeando.gui.primer_comprando_window import PrimerComprandoWindow
from costeando.gui.segundo_comprando_window import SegundoComprandoWindow
from costeando.gui.primer_produciendo_window import PrimerProduciendoWindow
from costeando.gui.segundo_produciendo_window import SegundoProduciendoWindow
from costeando.gui.actualizacion_fchs_window import ActualizacionFCHSWindow
from costeando.gui.listado_gral_window import ListadoGralWindow

configurar_logging()
logger = logging.getLogger(__name__)

class ProcesadorCostosApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Costeando")
        self.geometry("+200+200")  # Tamaño y posición de la ventana

        estilo = ttk.Style()
        estilo.theme_use("vista")  

        # Variable para almacenar la selección del usuario
        self.opcion_var = tk.IntVar(value=0)

        # Diccionario de ventanas
        self.ventanas = {
            1: LeaderListWindow,
            2: ComprasWindow,
            3: ValorizacionDYCWindow,
            4: PrimerComprandoWindow,
            5: SegundoComprandoWindow,
            6: PrimerProduciendoWindow,
            7: SegundoProduciendoWindow,
            8: ProyectadosWindow,
            9: ActualizacionFCHSWindow,
            10: ListadoGralWindow}

        # Crear la UI
        self.crear_interfaz()
        
    def crear_interfaz(self):
        
        ttk.Label(self, text="Seleccione un proceso y presione 'Ejecutar': ", font=("Arial",9, "bold")).pack(pady=10,padx=10)

        frame_procesos = ttk.Frame(self)
        frame_procesos.pack(pady=5)
        
        opciones = [
            ("Leader List", 1),
            ("Compras", 2),
            ("Valorización DyC", 3),
            ("Primer Comprando", 4),
            ("Segundo Comprando", 5),
            ("Primer Produciendo", 6),
            ("Segundo Produciendo", 7),
            ("Proyectados", 8),
            ("Actualización de Fechas", 9),
            ("Completar Listado General", 10)]

        for text, value in opciones:
            ttk.Radiobutton(frame_procesos, text=text, variable=self.opcion_var, value=value).pack(anchor="w", padx=5, pady=2)

        frame_botones = ttk.Frame(self)
        frame_botones.pack(pady=10)

        ttk.Button(frame_botones, text="Ejecutar", command=self.ejecutar_proceso_seleccionado).pack(side="left", padx=5)
        ttk.Button(frame_botones, text="Salir", command=self.cerrar_ventana).pack(side="right", padx=5)

        self.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
    
    def ejecutar_proceso_seleccionado(self):
        if hasattr(self, 'proceso_en_ejecucion') and self.proceso_en_ejecucion.is_alive():
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución.")
            return
    
        seleccion = self.opcion_var.get()
        

        if seleccion == 0:
            messagebox.showerror("Advertencia", "Por favor, seleccione un proceso antes de ejecutar.")
            return
        
        logger.debug(f"Proceso seleccionado por el usuario: {seleccion} - {self.ventanas[seleccion].__name__}")

        ventana = self.ventanas.get(seleccion)
        if ventana:
            self.proceso_en_ejecucion = threading.Thread(target=self.ejecutar_en_hilo, args=(ventana,), daemon=True)
            self.proceso_en_ejecucion.start()
    
    def ejecutar_en_hilo(self, ventana):
        
        """Ejecuta la ventana en un hilo separado con manejo de errores"""
        nombre_ventana = ventana.__name__.replace("Window", "").replace("_", " ").title()
        try:
            logger.info(f"Iniciando ventana: {nombre_ventana}")
            ventana_clase = ventana(master=self)
            logger.info(f"Ventana {nombre_ventana} iniciada exitosamente")
          
        except Exception as e:
            logger.error(f"Error en ventana {nombre_ventana}: {str(e)}", exc_info=True)
            self.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Error en la ventana {nombre_ventana}: {str(e)}"
            ))
       
    def cerrar_ventana(self):
        logger.info("Solicitud para cerrar la ventana")
        if hasattr(self, 'proceso_en_ejecucion') and self.proceso_en_ejecucion.is_alive():
            logger.warning("Intento de cierre con proceso en ejecución")
            
            if not messagebox.askyesno("Advertencia", "Hay un proceso en ejecución. ¿Seguro que quieres salir?"):
                logger.info("Cierre cancelado por el usuario")
                return
        if messagebox.askyesno("Salir", "¿Seguro que quieres salir?"):
            logger.info("Aplicación cerrada por el usuario")
            self.destroy()


# Ejecutar la aplicación
if __name__ == "__main__":
    app = ProcesadorCostosApp()
    app.mainloop()
