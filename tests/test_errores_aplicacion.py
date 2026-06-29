import pickle
from concurrent.futures import ProcessPoolExecutor

import pytest

from costeando.utilidades.errores_aplicacion import (
    ErrorReglaNegocio,
    generar_id_ejecucion,
    mapear_error_a_mensaje_usuario,
)


def _lanzar_error_controlado_en_proceso():
    raise ErrorReglaNegocio(
        mensaje_tecnico="Detalle tecnico",
        codigo_error="CST-NEG-009",
        titulo_usuario="Error de regla",
        mensaje_usuario="No se puede continuar.",
        accion_sugerida="Revise el dato de entrada.",
        id_ejecucion="ABC123XYZ789",
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


def test_error_controlado_se_puede_serializar_preservando_campos():
    error = ErrorReglaNegocio(
        mensaje_tecnico="Detalle tecnico",
        codigo_error="CST-NEG-009",
        titulo_usuario="Error de regla",
        mensaje_usuario="No se puede continuar.",
        accion_sugerida="Revise el dato de entrada.",
        id_ejecucion="ABC123XYZ789",
    )

    restaurado = pickle.loads(pickle.dumps(error))

    assert isinstance(restaurado, ErrorReglaNegocio)
    assert str(restaurado) == "Detalle tecnico"
    assert restaurado.codigo_error == "CST-NEG-009"
    assert restaurado.titulo_usuario == "Error de regla"
    assert restaurado.mensaje_usuario == "No se puede continuar."
    assert restaurado.accion_sugerida == "Revise el dato de entrada."
    assert restaurado.id_ejecucion == "ABC123XYZ789"


def test_error_controlado_cruza_process_pool_preservando_campos():
    try:
        executor = ProcessPoolExecutor(max_workers=1)
    except PermissionError as error:
        pytest.skip(f"No se pudo crear ProcessPoolExecutor en este entorno: {error}")

    with executor:
        future = executor.submit(_lanzar_error_controlado_en_proceso)

        try:
            future.result()
        except ErrorReglaNegocio as error:
            assert str(error) == "Detalle tecnico"
            assert error.codigo_error == "CST-NEG-009"
            assert error.titulo_usuario == "Error de regla"
            assert error.mensaje_usuario == "No se puede continuar."
            assert error.accion_sugerida == "Revise el dato de entrada."
            assert error.id_ejecucion == "ABC123XYZ789"
        else:
            raise AssertionError("Se esperaba ErrorReglaNegocio")
