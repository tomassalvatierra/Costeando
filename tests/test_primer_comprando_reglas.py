from datetime import datetime, timedelta

import pandas as pd

from costeando.modulos.procesamiento_primer_comprando import (
    asignacion_campanias,
    asignar_clasificacion,
    asignar_coeficiente,
    calcular_costo_sin_descuento,
    calcular_obsolescencia,
)


def test_asignar_clasificacion_bordes():
    assert asignar_clasificacion(0) == "SIN ROTACION"
    assert asignar_clasificacion(0.05) == "BAJA ROTACION"
    assert asignar_clasificacion(0.75) == "ROTACION NORMAL"
    assert asignar_clasificacion(100) == "BUENA ROTACION"


def test_asignacion_campanias_caso_01():
    campania_anterior, anio_campania_anterior = asignacion_campanias("01", "2026")
    assert campania_anterior == "18"
    assert anio_campania_anterior == "518"


def test_asignar_coeficiente():
    fila_a = {"Cod Actualiz": "A"}
    fila_b = {"Cod Actualiz": "B"}
    fila_x = {"Cod Actualiz": "X"}
    assert asignar_coeficiente(1.2, 1.1, fila_a) == 1.2
    assert asignar_coeficiente(1.2, 1.1, fila_b) == 1.1
    assert asignar_coeficiente(1.2, 1.1, fila_x) is None


def test_calcular_obsolescencia_bordes():
    fecha_actual = datetime(2026, 4, 1)
    fila_364 = {"Ult. Compra": fecha_actual - timedelta(days=364)}
    fila_365 = {"Ult. Compra": fecha_actual - timedelta(days=365)}
    fila_731 = {"Ult. Compra": fecha_actual - timedelta(days=731)}
    fila_3650 = {"Ult. Compra": fecha_actual - timedelta(days=3650)}
    assert calcular_obsolescencia(fecha_actual, fila_364) == 0
    assert calcular_obsolescencia(fecha_actual, fila_365) == 10
    assert calcular_obsolescencia(fecha_actual, fila_731) == 20
    assert calcular_obsolescencia(fecha_actual, fila_3650) == 75


def test_calcular_costo_sin_descuento_con_y_sin_compra():
    fila_con_compra = pd.Series({"Costo Compra": 120.0, "Costo sin Descuento C01": 100.0, "Coef de Actualizacion": 1.5})
    fila_sin_compra = pd.Series({"Costo Compra": None, "Costo sin Descuento C01": 100.0, "Coef de Actualizacion": 1.5})
    assert calcular_costo_sin_descuento("01", fila_con_compra) == 120.0
    assert calcular_costo_sin_descuento("01", fila_sin_compra) == 150.0
