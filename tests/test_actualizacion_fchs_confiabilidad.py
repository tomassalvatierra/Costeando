import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_actualizacion_fchs import procesar_actualizacion_fchs_puro
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_estructuras_excel(path_estructuras: Path):
    columnas = [
        "COD_NIVEL0",
        "CODIGO_PLANO",
        "COL3",
        "COL4",
        "COL5",
        "COL6",
        "COL7",
        "COL8",
        "COL9",
        "COL10",
        "COL11",
        "COL12",
        "COL13",
        "COL14",
        "COL15",
        "COL16",
    ]
    df = pd.DataFrame(
        [["A001", "1610001", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]],
        columns=columnas,
    )
    with pd.ExcelWriter(path_estructuras, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, startrow=4)


def _crear_fixture_actualizacion_fchs(tmp_path: Path):
    path_estructuras = tmp_path / "estructuras.xlsx"
    path_compras = tmp_path / "compras.xlsx"
    path_maestro = tmp_path / "maestro.xlsx"
    path_ordenes_apuntadas = tmp_path / "ordenes_apuntadas.xlsx"

    _crear_estructuras_excel(path_estructuras)

    pd.DataFrame(
        {
            "Producto": ["X9999", "1610001", "A001"],
            "Fch Emision": ["2026-01-10", "2026-01-12", "2026-01-15"],
            "Descripcion": ["Serv", "Comp 161", "Prod A001"],
            "Cantidad": [1, 2, 3],
        }
    ).to_excel(path_compras, index=False)

    pd.DataFrame(
        {
            "Codigo": ["A001", "1610001", "9999"],
            "Descripcion": ["Prod A001", "Comp 161", "Servicio 9999"],
            "Sub Grupo": [10, 20, 30],
            "Grupo": [2, 2, 2],
        }
    ).to_excel(path_maestro, index=False)

    pd.DataFrame(
        {
            "Producto": ["A001", "A001", "9999"],
            "Tipo Orden": ["Produccion", "Servicio", "Produccion"],
            "Fch Apunte": ["2026-01-20", "2026-01-10", "2026-01-22"],
        }
    ).to_excel(path_ordenes_apuntadas, index=False)

    return {
        "ruta_estructuras": str(path_estructuras),
        "ruta_compras": str(path_compras),
        "ruta_maestro": str(path_maestro),
        "ruta_ordenes_apuntadas": str(path_ordenes_apuntadas),
        "carpeta_guardado": str(tmp_path / "salida"),
    }


def test_falla_si_falta_carpeta_guardado(tmp_path: Path):
    data = _crear_fixture_actualizacion_fchs(tmp_path)
    data["carpeta_guardado"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_actualizacion_fchs_puro(**data)
    assert error.value.codigo_error == "CST-NEG-080"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_actualizacion_fchs(tmp_path)
    data["ruta_maestro"] = str(tmp_path / "no_existe.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_actualizacion_fchs_puro(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_compras(tmp_path: Path):
    data = _crear_fixture_actualizacion_fchs(tmp_path)
    pd.DataFrame({"Producto": ["A001"]}).to_excel(data["ruta_compras"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_actualizacion_fchs_puro(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salida_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_actualizacion_fchs(tmp_path)
    resultados = procesar_actualizacion_fchs_puro(**data)

    assert Path(resultados["actualizacion_fchs"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)
    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "actualizacion_fchs"
