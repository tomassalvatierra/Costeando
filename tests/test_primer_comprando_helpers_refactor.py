import pandas as pd

from costeando.modulos.procesamiento_primer_comprando import (
    _anexar_columnas_base,
    _preparar_base_calculo_comprando,
)


def test_preparar_base_filtra_por_tipo_bloqueo_y_atiende():
    df_maestro = pd.DataFrame(
        {
            "Codigo": ["OK1", "TIPO_GG", "BLOQ", "PROD"],
            "Cod Actualiz": ["1", "1", "1", "1"],
            "Blq. de Pant": ["No", "No", "Si", "No"],
            "AAtiende Ne?": ["C", "C", "C", "P"],
            "Tipo": ["PA", "GG", "PA", "PA"],
            "Grupo": [1, 1, 1, 1],
            "Ult. Compra": ["2025-01-01"] * 4,
        }
    )

    df_resultado = _preparar_base_calculo_comprando(df_maestro, "AAtiende Ne?")

    assert list(df_resultado["Codigo"]) == ["OK1"]
    assert df_resultado.iloc[0]["Cod Actualiz"] == "A"


def test_anexar_columnas_base_deja_nulos_si_no_hay_match():
    df_base = pd.DataFrame({"Codigo": ["X1"]})
    df_compras = pd.DataFrame(
        {
            "Codigo": ["OTRO"],
            "ULTCOS": [10.0],
            "Fch Emision": ["2026-01-01"],
            "OBSERVACIONES COSTOS": [""],
            "RESPUESTA COMPRAS": [""],
            "Campaña": ["02"],
            "MONEDA": ["Peso"],
        }
    )
    df_stock = pd.DataFrame({"Codigo": ["OTRO"], "Stock Actual": [100]})
    df_listado = pd.DataFrame({"Codigo": ["OTRO"], "COSTO LISTA 601": [90.0]})
    df_anterior = pd.DataFrame({"Codigo": ["OTRO"], "Costo sin Descuento C01": [95.0]})

    df_resultado = _anexar_columnas_base(
        df_base,
        df_compras,
        df_stock,
        df_listado,
        df_anterior,
        "601",
        "01",
    )

    assert df_resultado.loc[0, "Codigo"] == "X1"
    assert pd.isna(df_resultado.loc[0, "ULTCOS"])
    assert pd.isna(df_resultado.loc[0, "COSTO LISTA 601"])
    assert pd.isna(df_resultado.loc[0, "Costo sin Descuento C01"])
