from costeando.utilidades.errores_aplicacion import (
    ErrorReglaNegocio,
    generar_id_ejecucion,
    mapear_error_a_mensaje_usuario,
)


def test_generar_id_ejecucion_formato():
    id_ejecucion = generar_id_ejecucion()
    assert len(id_ejecucion) == 12
    assert id_ejecucion.isalnum()


def test_mapear_error_controlado_preserva_codigo_y_id():
    error = ErrorReglaNegocio(
        mensaje_tecnico="Detalle tecnico",
        codigo_error="CST-NEG-009",
        titulo_usuario="Error de regla",
        mensaje_usuario="No se puede continuar.",
        accion_sugerida="Revise el dato de entrada.",
    )
    mensaje = mapear_error_a_mensaje_usuario(error, "ABC123XYZ789")
    assert mensaje.codigo_error == "CST-NEG-009"
    assert mensaje.id_ejecucion == "ABC123XYZ789"
    assert "No se puede continuar." in mensaje.formatear_detalle()


def test_mapear_error_no_controlado_devuelve_codigo_generico():
    mensaje = mapear_error_a_mensaje_usuario(RuntimeError("fallo"), "RUN001")
    assert mensaje.codigo_error == "CST-INT-001"
    assert mensaje.id_ejecucion == "RUN001"
