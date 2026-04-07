import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_segundo_comprando import procesar_segundo_comprando
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


def test_segundo_comprando_ok_genera_salidas_y_manifiesto(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    resultado = procesar_segundo_comprando(**data)

    assert Path(resultado["comprando"]).exists()
    assert Path(resultado["especiales"]).exists()
    assert Path(resultado["importador"]).exists()
    assert Path(resultado["manifiesto"]).exists()
    assert resultado["id_ejecucion"] == "ID2COMP001"

    with open(resultado["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)

    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "segundo_comprando"
    assert manifiesto["metricas"]["filas_salida"] == 2


def test_segundo_comprando_falla_si_faltan_parametros(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    data["campania"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_segundo_comprando(**data)
    assert error.value.codigo_error == "CST-NEG-040"


def test_segundo_comprando_falla_si_falta_columna_minima(tmp_path: Path):
    data, _ = _crear_fixture_segundo_comprando(tmp_path)
    path_comprando = Path(data["ruta_comprando"])
    df = pd.read_excel(path_comprando, engine="openpyxl")
    df = df.drop(columns=["DESCUENTO ESPECIAL"])
    df.to_excel(path_comprando, index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_segundo_comprando(**data)
    assert error.value.codigo_error == "CST-VAL-001"

