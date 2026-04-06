import logging
from tkinter import messagebox

from costeando.utilidades.errores_aplicacion import (
    generar_id_ejecucion,
    mapear_error_a_mensaje_usuario,
)

logger = logging.getLogger(__name__)


def mostrar_error_legible(error: Exception, id_ejecucion: str | None = None) -> str:
    id_final = id_ejecucion or generar_id_ejecucion()
    mensaje = mapear_error_a_mensaje_usuario(error, id_final)
    logger.error(
        "Error mostrado a usuario. Codigo=%s ID=%s",
        mensaje.codigo_error,
        mensaje.id_ejecucion,
        exc_info=True,
    )
    messagebox.showerror(mensaje.titulo_usuario, mensaje.formatear_detalle())
    return mensaje.id_ejecucion
