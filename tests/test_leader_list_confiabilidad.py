import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_leader_list import procesar_leader_list_puro
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_fixture_leader_list(tmp_path: Path):
    path_leader = tmp_path / "leader.xlsx"
    path_listado_anterior = tmp_path / "listado_anterior.xlsx"
    path_maestro = tmp_path / "maestro.xlsx"
    path_dobles = tmp_path / "dobles.xlsx"
    path_combinadas = tmp_path / "combinadas.xlsx"
    path_stock = tmp_path / "stock.xlsx"

    pd.DataFrame(
        {
            "CODIGON": ["A001", "A002", "99000"],
            "CAMP": ["02", "02", "02"],
            "ANO": ["2026", "2026", "2026"],
            "DESCRIP": ["Prod A001", "Prod A002", "Excluir"],
            "UNID_EST": [100, 50, 1],
        }
    ).to_excel(path_leader, index=False)

    pd.DataFrame(
        {
            "Producto": ["A001", "A002"],
            "COSTO LISTA 601": [100.0, 80.0],
            "DESCUENTO ESPECIAL": [5.0, 0.0],
            "APLICA DDE CA:": ["2026/01", "2026/01"],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO", "AGOTAMIENTO-PRODUCTO TERMINADO"],
        }
    ).to_excel(path_listado_anterior, index=False)

    pd.DataFrame(
        {
            "Producto": ["A001", "A002"],
            "Atiende Ne?": ["P", "P"],
            "Estado": ["ACT", "ACT"],
        }
    ).to_excel(path_maestro, index=False)

    pd.DataFrame(
        {
            "CODIGO_DOB": ["A001"],
            "CODIGO_ORI": ["M001"],
        }
    ).to_excel(path_dobles, index=False)

    pd.DataFrame(
        {
            "CODIGON": ["A002", "A001"],
            "COMBINADA": ["CMB01", "CMB01"],
        }
    ).to_excel(path_combinadas, index=False)

    pd.DataFrame(
        {
            "Producto": ["A001", "A002"],
            "Stock Actual": [500, 200],
        }
    ).to_excel(path_stock, index=False)

    return {
        "ruta_leader_list": str(path_leader),
        "ruta_listado_anterior": str(path_listado_anterior),
        "ruta_maestro": str(path_maestro),
        "ruta_dobles": str(path_dobles),
        "ruta_combinadas": str(path_combinadas),
        "ruta_stock": str(path_stock),
        "campana": "02",
        "anio": "2026",
        "carpeta_guardado": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_leader_list(tmp_path)
    data["campana"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_leader_list_puro(**data)
    assert error.value.codigo_error == "CST-NEG-090"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_leader_list(tmp_path)
    data["ruta_stock"] = str(tmp_path / "stock_inexistente.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_leader_list_puro(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_leader_list(tmp_path: Path):
    data = _crear_fixture_leader_list(tmp_path)
    pd.DataFrame({"CODIGON": ["A001"]}).to_excel(data["ruta_leader_list"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_leader_list_puro(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salidas_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_leader_list(tmp_path)
    resultados = procesar_leader_list_puro(**data)

    assert Path(resultados["leader_list"]).exists()
    assert Path(resultados["combinadas_agrupadas"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "leader_list"
