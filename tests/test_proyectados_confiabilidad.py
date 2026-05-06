import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_proyectados import procesar_proyectados_puro
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_coeficientes(campania_inicial: str, anio_inicial: str) -> pd.DataFrame:
    campania_numero = int(campania_inicial) + 1
    anio = int(anio_inicial)
    campanias = []
    for _ in range(10):
        if campania_numero > 18:
            campania_numero = 1
            anio += 1
        campanias.append(f"C{str(campania_numero).zfill(2)}-{anio}")
        campania_numero += 1
    return pd.DataFrame({"CAMPAÑA-AÑO": campanias, "VAR_A": [0.05] * 10, "VAR_B": [0.01] * 10})


def _crear_fixture_proyectados(tmp_path: Path):
    path_lista = tmp_path / "lista.xlsx"
    path_coef = tmp_path / "coef.xlsx"

    pd.DataFrame(
        {
            "Producto": ["1001", "1002", "1003"],
            "VARIABLE": ["VAR_A", "VAR_B", "VAR_A"],
            "LLEVA CF": [0, 1, 0],
            "Tipo": ["PA", "GG", "PA"],
            "Estado": ["ACT", "ACT", "INA"],
            "COSTO LISTA 602": [100.0, 200.0, 150.0],
        }
    ).to_excel(path_lista, index=False)

    _crear_coeficientes("02", "2026").to_excel(path_coef, index=False)

    return {
        "ruta_lista": str(path_lista),
        "ruta_coef": str(path_coef),
        "camp_inicial": "02",
        "anio_inicial": "2026",
        "carpeta_guardado": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_proyectados(tmp_path)
    data["camp_inicial"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_proyectados_puro(**data)
    assert error.value.codigo_error == "CST-NEG-060"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_proyectados(tmp_path)
    data["ruta_lista"] = str(tmp_path / "inexistente.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_proyectados_puro(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_lista(tmp_path: Path):
    data = _crear_fixture_proyectados(tmp_path)
    pd.DataFrame({"Producto": ["1001"]}).to_excel(data["ruta_lista"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_proyectados_puro(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_falla_si_falta_coeficiente_para_variable(tmp_path: Path):
    data = _crear_fixture_proyectados(tmp_path)
    coeficientes = _crear_coeficientes("02", "2026").drop(columns=["VAR_B"])
    coeficientes.to_excel(data["ruta_coef"], index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_proyectados_puro(**data)

    assert error.value.codigo_error == "CST-VAL-006"


def test_caso_minimo_valido_genera_salidas_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_proyectados(tmp_path)
    resultados = procesar_proyectados_puro(**data)

    assert Path(resultados["proyectado"]).exists()
    assert Path(resultados["proyectado_comercial"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "proyectados"

