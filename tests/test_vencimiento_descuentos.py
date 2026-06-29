import pandas as pd

from costeando.utilidades.vencimiento_descuentos import (
    NOTA_SIN_STOCK,
    NOTA_VENCIMIENTO_COMPONENTES,
    NOTA_VENCIMIENTO_GENERAL,
    actualizar_vencimiento_descuentos,
    calcular_campania_limite_stock,
    campania_a_absoluta,
)


def _base_descuentos():
    return pd.DataFrame(
        {
            "Codigo": [
                "GENERAL_BORDE",
                "GENERAL_VENCE",
                "STOCK_BORDE",
                "STOCK_VENCE",
                "COMP_BORDE",
                "COMP_VENCE",
                "PRIORIDAD",
                "VENCIDO_PREVIO",
            ],
            "VENCIDO": ["No", "No", "No", "No", "No", "No", "No", "Si"],
            "APLICA DDE CA:": [
                "2025/01",
                "2024/18",
                "2026/04",
                "2026/04",
                "2025/10",
                "2025/09",
                "2024/01",
                "2024/01",
            ],
            "TIPO-DESCUENTO": [
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-COMPONENTES",
                "AGOTAMIENTO-COMPONENTES",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
            ],
            "Stock Actual": [1000, 1000, 500, 499, 1000, 1000, 100, 0],
            "NOTAS": ["", "", "", "", "", "", "", "Ya estaba vencido"],
        }
    )


def test_campania_a_absoluta_y_limite_stock_con_cruce_de_anio():
    assert campania_a_absoluta(1, 2026) == 91
    assert calcular_campania_limite_stock(-3, 2026) == (15, 2025)


def test_actualizar_vencimiento_respeta_bordes_y_preserva_filas():
    df_base = _base_descuentos()

    df_final, df_no_vencidos, df_cambios = actualizar_vencimiento_descuentos(
        df_base,
        campania_actual=10,
        anio_actual=2026,
        campania_stock=5,
    )

    notas = df_final.set_index("Codigo")["NOTAS"]
    vencidos = df_final.set_index("Codigo")["VENCIDO"]

    assert len(df_final) == len(df_base)
    assert vencidos["GENERAL_BORDE"] == "No"
    assert notas["GENERAL_VENCE"] == NOTA_VENCIMIENTO_GENERAL
    assert vencidos["STOCK_BORDE"] == "No"
    assert notas["STOCK_VENCE"] == NOTA_SIN_STOCK
    assert vencidos["COMP_BORDE"] == "No"
    assert notas["COMP_VENCE"] == NOTA_VENCIMIENTO_COMPONENTES
    assert notas["PRIORIDAD"] == NOTA_VENCIMIENTO_GENERAL
    assert notas["VENCIDO_PREVIO"] == "Ya estaba vencido"
    assert set(df_no_vencidos["Codigo"]) == {"GENERAL_BORDE", "STOCK_BORDE", "COMP_BORDE"}
    assert set(df_cambios["Codigo"]) == {"GENERAL_VENCE", "STOCK_VENCE", "COMP_VENCE", "PRIORIDAD"}


def test_actualizar_vencimiento_no_muta_dataframe_original():
    df_base = _base_descuentos()
    columnas_originales = list(df_base.columns)

    actualizar_vencimiento_descuentos(
        df_base,
        campania_actual=10,
        anio_actual=2026,
        campania_stock=5,
    )

    assert list(df_base.columns) == columnas_originales
    assert df_base.loc[df_base["Codigo"] == "GENERAL_VENCE", "VENCIDO"].iloc[0] == "No"

def test_actualizar_vencimiento_maneja_base_vacia():
    df_base = pd.DataFrame(
        columns=["Codigo", "VENCIDO", "APLICA DDE CA:", "TIPO-DESCUENTO", "Stock Actual", "NOTAS"]
    )

    df_final, df_no_vencidos, df_cambios = actualizar_vencimiento_descuentos(
        df_base,
        campania_actual=10,
        anio_actual=2026,
        campania_stock=5,
    )

    assert df_final.empty
    assert df_no_vencidos.empty
    assert df_cambios.empty


def test_actualizar_vencimiento_no_reporta_vencidos_previos_como_cambios():
    df_base = pd.DataFrame(
        {
            "Codigo": ["PREVIO"],
            "VENCIDO": ["Si"],
            "APLICA DDE CA:": ["2024/01"],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO"],
            "Stock Actual": [0],
            "NOTAS": ["Ya estaba vencido"],
        }
    )

    df_final, df_no_vencidos, df_cambios = actualizar_vencimiento_descuentos(
        df_base,
        campania_actual=10,
        anio_actual=2026,
        campania_stock=5,
    )

    assert list(df_final["Codigo"]) == ["PREVIO"]
    assert df_no_vencidos.empty
    assert df_cambios.empty

