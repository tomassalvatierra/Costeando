import logging
from dataclasses import dataclass
from uuid import uuid4

logger = logging.getLogger(__name__)


def generar_id_ejecucion() -> str:
    return uuid4().hex[:12].upper()


class ErrorAplicacion(Exception):
    def __init__(
        self,
        mensaje_tecnico: str,
        codigo_error: str,
        titulo_usuario: str,
        mensaje_usuario: str,
        accion_sugerida: str,
        id_ejecucion: str | None = None,
    ):
        super().__init__(mensaje_tecnico)
        self.mensaje_tecnico = mensaje_tecnico
        self.codigo_error = codigo_error
        self.titulo_usuario = titulo_usuario
        self.mensaje_usuario = mensaje_usuario
        self.accion_sugerida = accion_sugerida
        self.id_ejecucion = id_ejecucion

    def con_id_ejecucion(self, id_ejecucion: str) -> "ErrorAplicacion":
        self.id_ejecucion = id_ejecucion
        return self


class ErrorEntradaArchivo(ErrorAplicacion):
    pass


class ErrorEsquemaArchivo(ErrorAplicacion):
    pass


class ErrorReglaNegocio(ErrorAplicacion):
    pass


class ErrorEscrituraSalida(ErrorAplicacion):
    pass


class ErrorInternoInesperado(ErrorAplicacion):
    pass


@dataclass
class MensajeErrorUsuario:
    codigo_error: str
    titulo_usuario: str
    mensaje_usuario: str
    accion_sugerida: str
    id_ejecucion: str

    def formatear_detalle(self) -> str:
        return (
            f"Que fallo: {self.mensaje_usuario}\n\n"
            f"Que hacer: {self.accion_sugerida}\n\n"
            f"Codigo: {self.codigo_error}\n"
            f"ID de ejecucion: {self.id_ejecucion}"
        )


def _mensaje_generico(id_ejecucion: str) -> MensajeErrorUsuario:
    return MensajeErrorUsuario(
        codigo_error="CST-INT-001",
        titulo_usuario="Error inesperado",
        mensaje_usuario="Ocurrio un error no controlado durante el proceso.",
        accion_sugerida=(
            "Reintente la operacion. Si el problema persiste, contacte soporte "
            "indicando el codigo de error y el ID de ejecucion."
        ),
        id_ejecucion=id_ejecucion,
    )


def mapear_error_a_mensaje_usuario(
    error: Exception,
    id_ejecucion: str,
) -> MensajeErrorUsuario:
    if isinstance(error, ErrorAplicacion):
        if not error.id_ejecucion:
            error.id_ejecucion = id_ejecucion
        return MensajeErrorUsuario(
            codigo_error=error.codigo_error,
            titulo_usuario=error.titulo_usuario,
            mensaje_usuario=error.mensaje_usuario,
            accion_sugerida=error.accion_sugerida,
            id_ejecucion=error.id_ejecucion,
        )
    logger.error(
        "Error no controlado en GUI. ID ejecucion=%s. Detalle=%s",
        id_ejecucion,
        str(error),
        exc_info=True,
    )
    return _mensaje_generico(id_ejecucion)
