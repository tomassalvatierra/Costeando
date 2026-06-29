from datetime import datetime, timedelta

import pandas as pd

from costeando.modulos.procesamiento_primer_comprando import (
    asignacion_campanias,
    asignar_clasificacion,
    asignar_coeficiente,
    calcular_costo_sin_descuento,
    calcular_obsolescencia,
    procesar_descuento,
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

def test_procesar_descuento_conserva_vencidos_previos_y_reporta_solo_cambios_nuevos():
    df_calculo = pd.DataFrame(
        {
            "Codigo": ["PREV", "GENERAL", "OC", "OK"],
            "% de obsolescencia": [10, 20, 30, 40],
        }
    )
    df_descuentos = pd.DataFrame(
        {
            "Codigo": ["PREV", "GENERAL", "OC", "OK"],
            "VENCIDO": ["Si", "No", "No", "No"],
            "APLICA DDE CA:": ["2024/01", "2024/01", "2026/09", "2026/09"],
            "TIPO-DESCUENTO": [
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
            ],
            "Stock Actual": [0, 1000, 1000, 1000],
            "NOTAS": ["Vencido anterior", "", "", ""],
            "DESCUENTO ESPECIAL": [5, 10, 15, 20],
        }
    )
    df_compras = pd.DataFrame(
        {
            "Codigo": ["OC"],
            "Fch Emision": ["2026-06-01"],
        }
    )

    df_calculo_resultado, df_final, df_no_vencidos, df_cambios = procesar_descuento(
        df_calculo,
        df_descuentos,
        "10",
        "2026",
        df_compras,
    )

    assert list(df_final["Codigo"]) == ["PREV", "GENERAL", "OC", "OK"]
    assert df_final.loc[df_final["Codigo"] == "PREV", "NOTAS"].iloc[0] == "Vencido anterior"
    assert set(df_no_vencidos["Codigo"]) == {"OK"}
    assert set(df_cambios["Codigo"]) == {"GENERAL", "OC"}
    assert "PREV" not in set(df_cambios["Codigo"])
    assert df_calculo_resultado.loc[df_calculo_resultado["Codigo"] == "OC", "% de obsolescencia"].iloc[0] == 0

def test_procesar_descuento_devuelve_base_si_no_hay_descuentos_activos():
    df_calculo = pd.DataFrame({"Codigo": ["PREV"], "% de obsolescencia": [10]})
    df_descuentos = pd.DataFrame(
        {
            "Codigo": ["PREV"],
            "VENCIDO": ["Si"],
            "APLICA DDE CA:": ["2024/01"],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO"],
            "Stock Actual": [0],
            "NOTAS": ["Vencido anterior"],
            "DESCUENTO ESPECIAL": [5],
        }
    )
    df_compras = pd.DataFrame({"Codigo": [], "Fch Emision": []})

    _, df_final, df_no_vencidos, df_cambios = procesar_descuento(
        df_calculo,
        df_descuentos,
        "10",
        "2026",
        df_compras,
    )

    assert list(df_final["Codigo"]) == ["PREV"]
    assert df_no_vencidos.empty
    assert df_cambios.empty
    assert "Stock Actual" not in df_final.columns

