import logging
from pathlib import Path
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


def mostrar_advertencia_usuario(titulo: str, mensaje: str, accion_sugerida: str | None = None):
    detalle = f"Que falta: {mensaje}"
    if accion_sugerida:
        detalle += f"\n\nQue hacer: {accion_sugerida}"
    messagebox.showwarning(titulo, detalle)


def mostrar_exito_proceso(nombre_proceso: str, resultado: dict | None = None):
    resultado = resultado or {}
    id_ejecucion = resultado.get("id_ejecucion")
    archivos_generados = [
        (nombre, ruta)
        for nombre, ruta in resultado.items()
        if nombre != "id_ejecucion" and isinstance(ruta, str) and ruta
    ]

    partes = [f"{nombre_proceso} finalizo correctamente."]
    if archivos_generados:
        partes.append("Archivos generados:")
        partes.extend(f"- {nombre}: {Path(ruta).name}" for nombre, ruta in archivos_generados)
    if id_ejecucion:
        partes.append(f"ID de ejecucion: {id_ejecucion}")

    logger.info(
        "Proceso finalizado correctamente. Proceso=%s ID=%s Archivos=%s",
        nombre_proceso,
        id_ejecucion or "sin_id",
        len(archivos_generados),
    )
    detalle = partes[0]
    if len(partes) > 1:
        detalle += "\n\n" + "\n".join(partes[1:])
    messagebox.showinfo("Exito", detalle)
