from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_segundo_comprando import (
    incorporar_nuevos_dtos,
    procesar_segundo_comprando,
)
from costeando.utilidades.errores_aplicacion import ErrorEsquemaArchivo, ErrorReglaNegocio


def _crear_fixture_segundo_comprando(tmp_path: Path):
    campania = "02"
    anio = "2026"
    path_comprando = tmp_path / "comprando.xlsx"
    path_especiales = tmp_path / "especiales.xlsx"
    path_importador = tmp_path / "importador.xlsx"
    path_salida = tmp_path / "salida"

    pd.DataFrame(
        {
            "Producto": ["1001", "1002"],
            "Descripcion": ["Prod 1", "Prod 2"],
            "Atiende Ne?": ["C", "C"],
            "% de obsolescencia": [10.0, 0.0],
            "DESCUENTO ESPECIAL": [5.0, 2.0],
            "ROYALTY": [-1.0, 0.0],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "Costo sin Descuento C02": [100.0, 80.0],
        }
    ).to_excel(path_comprando, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001", "1002"],
            "DESCUENTO ESPECIAL": [5.0, 2.0],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "VENCIDO": ["No", "No"],
            "NOTAS": ["", ""],
            "TIPO-DESCUENTO": [
                "AGOTAMIENTO-PRODUCTO TERMINADO",
                "AGOTAMIENTO-PRODUCTO TERMINADO",
            ],
        }
    ).to_excel(path_especiales, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001"],
            "DESCUENTO ESPECIAL": [4.0],
            "APLICA DDE CA:": ["2026/02"],
        }
    ).to_excel(path_importador, index=False)

    return {
        "ruta_comprando": str(path_comprando),
        "ruta_costos_especiales": str(path_especiales),
        "ruta_importador_descuentos": None,
        "campania": campania,
        "anio": anio,
        "fecha_compras_inicio": "01/01/2026",
        "fecha_compras_final": "31/01/2026",
        "carpeta_guardado": str(path_salida),
        "id_ejecucion": "ID2COMP001",
    }, str(path_importador)


def test_segundo_comprando_ok_genera_salidas_sin_manifiesto(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    resultado = procesar_segundo_comprando(**data)

    assert Path(resultado["comprando"]).exists()
    assert Path(resultado["especiales"]).exists()
    assert Path(resultado["importador"]).exists()
    assert resultado["id_ejecucion"] == "ID2COMP001"
    assert "manifiesto" not in resultado


def test_incorporar_nuevos_dtos_pisa_descuento_vigente_y_agrega_historial():
    df_especiales = pd.DataFrame(
        {
            "Codigo": ["1001", "1002"],
            "DESCUENTO ESPECIAL": [5.0, 0.0],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "VENCIDO": ["No", "No"],
            "NOTAS": ["", ""],
        }
    )
    df_importador = pd.DataFrame(
        {
            "Codigo": ["1001", "1002", "1003"],
            "DESCUENTO ESPECIAL": [12.0, 8.0, 4.0],
            "APLICA DDE CA:": ["2026/02", "2026/02", "2026/02"],
        }
    )
    df_productos = pd.DataFrame(
        {
            "Codigo": ["1001", "1002", "1003", "1004"],
            "DESCUENTO ESPECIAL": [5.0, 0.0, None, 3.0],
            "APLICA DDE CA:": ["2025/01", "2025/01", None, "2025/01"],
        }
    )

    df_base_actualizada, df_productos_actualizados = incorporar_nuevos_dtos(
        df_especiales,
        df_importador,
        df_productos,
    )

    descuentos_por_codigo = df_productos_actualizados.set_index("Codigo")["DESCUENTO ESPECIAL"]
    aplica_por_codigo = df_productos_actualizados.set_index("Codigo")["APLICA DDE CA:"]
    assert descuentos_por_codigo["1001"] == 12.0
    assert descuentos_por_codigo["1002"] == 8.0
    assert descuentos_por_codigo["1003"] == 4.0
    assert descuentos_por_codigo["1004"] == 3.0
    assert aplica_por_codigo["1001"] == "2026/02"
    assert aplica_por_codigo["1002"] == "2026/02"
    assert aplica_por_codigo["1003"] == "2026/02"
    assert aplica_por_codigo["1004"] == "2025/01"

    anteriores = df_base_actualizada[
        (df_base_actualizada["Codigo"].isin(["1001", "1002"]))
        & (df_base_actualizada["APLICA DDE CA:"] == "2025/01")
    ]
    assert anteriores["VENCIDO"].tolist() == ["Si", "Si"]
    assert anteriores["NOTAS"].tolist() == [
        "Vencido, ingreso un nuevo descuento",
        "Vencido, ingreso un nuevo descuento",
    ]

    nuevos = df_base_actualizada[df_base_actualizada["APLICA DDE CA:"] == "2026/02"]
    assert nuevos["Codigo"].tolist() == ["1001", "1002", "1003"]
    assert nuevos["DESCUENTO ESPECIAL"].tolist() == [12.0, 8.0, 4.0]


def test_segundo_comprando_falla_si_faltan_parametros(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    data["campania"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_segundo_comprando(**data)
    assert error.value.codigo_error == "CST-NEG-040"


def test_segundo_comprando_falla_si_fecha_inicio_supera_fecha_final(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    data["fecha_compras_inicio"] = "31/01/2026"
    data["fecha_compras_final"] = "01/01/2026"

    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_segundo_comprando(**data)

    assert error.value.codigo_error == "CST-NEG-043"


def test_segundo_comprando_falla_si_falta_columna_minima(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    path_comprando = Path(data["ruta_comprando"])
    df = pd.read_excel(path_comprando, engine="openpyxl")
    df = df.drop(columns=["DESCUENTO ESPECIAL"])
    df.to_excel(path_comprando, index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_segundo_comprando(**data)
    assert error.value.codigo_error == "CST-VAL-001"

