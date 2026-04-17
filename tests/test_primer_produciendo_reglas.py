from datetime import datetime, timedelta

import pandas as pd

from costeando.modulos.procesamiento_primer_produciendo import (
    calcular_costo_sin_descuento,
    calcular_obsolescencia,
)


def test_calcular_obsolescencia_bordes():
    fecha_actual = datetime(2026, 4, 1)
    fila_364 = {"Ult. Compra": fecha_actual - timedelta(days=364)}
    fila_365 = {"Ult. Compra": fecha_actual - timedelta(days=365)}
    fila_1096 = {"Ult. Compra": fecha_actual - timedelta(days=1096)}
    fila_3650 = {"Ult. Compra": fecha_actual - timedelta(days=3650)}
    assert calcular_obsolescencia(fecha_actual, fila_364) == 0
    assert calcular_obsolescencia(fecha_actual, fila_365) == 10
    assert calcular_obsolescencia(fecha_actual, fila_1096) == 30
    assert calcular_obsolescencia(fecha_actual, fila_3650) == 75


def test_calcular_costo_sin_descuento_con_lleva_cf_si():
    df = pd.DataFrame(
        {
            "LLEVA CF": ["Si"],
            "Grupo": [1],
            "Tipo": ["PA"],
            "Costo Producción": [84.0],
        }
    )
    costo = calcular_costo_sin_descuento(df.iloc[0], df)
    assert costo == 100.0


def test_calcular_costo_sin_descuento_autodetecta_lleva_cf_no():
    df = pd.DataFrame(
        {
            "LLEVA CF": [None],
            "Grupo": [2],
            "Tipo": ["PD"],
            "Costo Producción": [50.0],
        }
    )
    costo = calcular_costo_sin_descuento(df.iloc[0], df)
    assert costo == 50.0

