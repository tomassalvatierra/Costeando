import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_valorizacion_dyc import procesar_valorizacion_dyc_puro
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_fixture_valorizacion_dyc(tmp_path: Path):
    path_listado = tmp_path / "listado.xlsx"
    path_combinadas = tmp_path / "combinadas.xlsx"
    path_dobles = tmp_path / "dobles.xlsx"

    pd.DataFrame(
        {
            "Producto": ["A001", "A002", "M001"],
            "COSTO LISTA 602": [100.0, 50.0, 20.0],
        }
    ).to_excel(path_listado, index=False)

    pd.DataFrame(
        {
            "COMBINADA": ["CMB01", "CMB01"],
            "CODIGON": ["A001", "A002"],
            "CANTIDAD": [2, 1],
            "DESCR_COMB": ["Combinada 1", "Combinada 1"],
        }
    ).to_excel(path_combinadas, index=False)

    pd.DataFrame(
        {
            "CODIGO_ORI": ["A001"],
            "CODIGO_DOB": ["D001"],
            "DESCR_DOB": ["Doble 1"],
        }
    ).to_excel(path_dobles, index=False)

    return {
        "ruta_listado": str(path_listado),
        "ruta_combinadas": str(path_combinadas),
        "ruta_dobles": str(path_dobles),
        "campana": "02",
        "anio": "2026",
        "carpeta_guardado": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_valorizacion_dyc(tmp_path)
    data["campana"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_valorizacion_dyc_puro(**data)
    assert error.value.codigo_error == "CST-NEG-070"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_valorizacion_dyc(tmp_path)
    data["ruta_combinadas"] = str(tmp_path / "inexistente.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_valorizacion_dyc_puro(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_combinadas(tmp_path: Path):
    data = _crear_fixture_valorizacion_dyc(tmp_path)
    pd.DataFrame({"COMBINADA": ["CMB01"]}).to_excel(data["ruta_combinadas"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_valorizacion_dyc_puro(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salida_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_valorizacion_dyc(tmp_path)
    resultados = procesar_valorizacion_dyc_puro(**data)

    assert Path(resultados["valorizacion_dyc"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "valorizacion_dyc"
