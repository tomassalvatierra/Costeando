import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_segundo_produciendo import procesar_segundo_produciendo
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_fixture_segundo_produciendo(tmp_path: Path):
    path_produciendo = tmp_path / "produciendo.xlsx"
    path_base_especiales = tmp_path / "base_especiales.xlsx"
    path_importador = tmp_path / "importador.xlsx"

    pd.DataFrame(
        {
            "Producto": ["2001", "2002"],
            "Descripcion": ["Prod 2001", "Prod 2002"],
            "¿Atiende Ne?": ["P", "P"],
            "% de obsolescencia": [10.0, 0.0],
            "DESCUENTO ESPECIAL": [5.0, 2.0],
            "ROYALTY": [0.0, 0.0],
            "APLICA DDE CA:": ["2026/02", "2026/02"],
            "Costo sin Descuento C02": [100.0, 50.0],
        }
    ).to_excel(path_produciendo, index=False)

    pd.DataFrame(
        {
            "Producto": ["2001", "2002"],
            "DESCUENTO ESPECIAL": [5.0, 2.0],
            "APLICA DDE CA:": ["2026/02", "2026/02"],
            "VENCIDO": ["No", "No"],
            "NOTAS": ["", ""],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO", "AGOTAMIENTO-PRODUCTO TERMINADO"],
        }
    ).to_excel(path_base_especiales, index=False)

    pd.DataFrame(
        {
            "Producto": ["2001"],
            "DESCUENTO ESPECIAL": [3.0],
            "APLICA DDE CA:": ["2026/02"],
        }
    ).to_excel(path_importador, index=False)

    return {
        "ruta_produciendo": str(path_produciendo),
        "ruta_base_especiales": str(path_base_especiales),
        "ruta_importador_descuentos": None,
        "campania": "2",
        "anio": "2026",
        "fecha_compras_inicio": "01/01/2026",
        "fecha_compras_final": "31/01/2026",
        "carpeta_guardado": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    data["campania"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_segundo_produciendo(**data)
    assert error.value.codigo_error == "CST-NEG-050"


def test_falla_si_fecha_inicio_supera_fecha_final(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    data["fecha_compras_inicio"] = "31/01/2026"
    data["fecha_compras_final"] = "01/01/2026"

    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_segundo_produciendo(**data)

    assert error.value.codigo_error == "CST-NEG-055"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    data["ruta_base_especiales"] = str(tmp_path / "base_inexistente.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_segundo_produciendo(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_produciendo(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    pd.DataFrame({"Producto": ["2001"]}).to_excel(data["ruta_produciendo"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_segundo_produciendo(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salidas_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    resultados = procesar_segundo_produciendo(**data)

    assert Path(resultados["importador"]).exists()
    assert Path(resultados["produciendo"]).exists()
    assert Path(resultados["especiales"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "segundo_produciendo"
