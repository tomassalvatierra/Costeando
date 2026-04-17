from pathlib import Path
import json

import pandas as pd
import pytest

from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_fixture_primer_comprando(tmp_path: Path):
    campania = "02"
    anio = "2026"
    campania_anterior = "01"
    anio_campania_anterior = "601"

    path_maestro = tmp_path / "maestro.xlsx"
    path_compras = tmp_path / "compras.xlsx"
    path_stock = tmp_path / "stock.xlsx"
    path_dto = tmp_path / "dto.xlsx"
    path_listado = tmp_path / "listado.xlsx"
    path_comprando_anterior = tmp_path / "comprando_anterior.xlsx"
    path_ficha = tmp_path / "ficha.xlsx"

    pd.DataFrame(
        {
            "Producto": ["1001", "MOD0806"],
            "Cod Actualiz": ["A", "A"],
            "Blq. de Pant": ["No", "No"],
            "Atiende Ne?": ["C", "C"],
            "Tipo": ["PA", "PA"],
            "Grupo": [1, 1],
            "Ult. Compra": ["2025-01-01", "2025-01-01"],
        }
    ).to_excel(path_maestro, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001", "MOD0806"],
            "ULTCOS": [100.0, 10.0],
            "Fch Emision": ["2026-02-01", "2026-02-01"],
            "OBSERVACIONES COSTOS": ["", ""],
            "RESPUESTA COMPRAS": ["", ""],
            "Campaña": [campania, campania],
            "MONEDA": ["Peso", "Peso"],
        }
    ).to_excel(path_compras, index=False)

    pd.DataFrame({"Producto": ["1001", "MOD0806"], "Stock Actual": [1000, 100]}).to_excel(path_stock, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001", "MOD0806"],
            "VENCIDO": ["No", "No"],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO", "AGOTAMIENTO-PRODUCTO TERMINADO"],
            "DESCUENTO ESPECIAL": [5.0, 0.0],
            "ROYALTY": [0.0, 0.0],
        }
    ).to_excel(path_dto, index=False)

    pd.DataFrame({"Producto": ["1001", "MOD0806"], "COSTO LISTA " + anio_campania_anterior: [90.0, 10.0]}).to_excel(path_listado, index=False)
    pd.DataFrame({"Producto": ["1001", "MOD0806"], "Costo sin Descuento C" + campania_anterior: [95.0, 10.0]}).to_excel(path_comprando_anterior, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001", "MOD0806"],
            "Stock Actual": [1000, 100],
            "Pedidos N+1": [10, 5],
            "Pedidos N+2": [10, 5],
            "Pedidos N+3": [10, 5],
            "Pedidos N+4": [10, 5],
            "Pedidos N+5": [10, 5],
            "Stock N+6": [100, 50],
            "Grupo": [1, 1],
            "Tipo": ["PA", "PA"],
        }
    ).to_excel(path_ficha, index=False)

    return {
        "campania": campania,
        "anio": anio,
        "indice_a": 1.1,
        "indice_b": 1.0,
        "mano_de_obra": 12.5,
        "ruta_maestro": str(path_maestro),
        "ruta_compras": str(path_compras),
        "ruta_stock": str(path_stock),
        "ruta_dto_especiales": str(path_dto),
        "ruta_listado": str(path_listado),
        "ruta_calculo_comprando_ant": str(path_comprando_anterior),
        "ruta_ficha": str(path_ficha),
        "ruta_salida": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    data["campania"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_primer_comprando(**data)
    assert error.value.codigo_error == "CST-NEG-010"


def test_falla_si_ruta_salida_vacia(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    data["ruta_salida"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_primer_comprando(**data)
    assert error.value.codigo_error == "CST-NEG-011"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    data["ruta_compras"] = str(tmp_path / "no_existe.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_primer_comprando(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_maestro(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    path_maestro = Path(data["ruta_maestro"])
    pd.DataFrame({"Producto": ["1001"]}).to_excel(path_maestro, index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_primer_comprando(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salidas_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    resultados = procesar_primer_comprando(**data)
    assert Path(resultados["calculo_comprando"]).exists()
    assert Path(resultados["rotacion"]).exists()
    assert Path(resultados["base_descuentos"]).exists()
    assert Path(resultados["cambios"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]


def test_acepta_columna_atiende_legacy(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    path_maestro = Path(data["ruta_maestro"])
    df_maestro = pd.read_excel(path_maestro, engine="openpyxl")
    df_maestro = df_maestro.rename(columns={"Atiende Ne?": "Atiende Ne?"})
    df_maestro.to_excel(path_maestro, index=False)

    resultados = procesar_primer_comprando(**data)

    assert Path(resultados["calculo_comprando"]).exists()
    assert Path(resultados["manifiesto"]).exists()


def test_falla_si_fechas_maestro_son_invalidas(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    path_maestro = Path(data["ruta_maestro"])
    df_maestro = pd.read_excel(path_maestro, engine="openpyxl")
    df_maestro["Ult. Compra"] = ["invalida", "sin_fecha"]
    df_maestro.to_excel(path_maestro, index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_primer_comprando(**data)

    assert error.value.codigo_error == "CST-VAL-004"


def test_error_controlado_genera_manifiesto_error_con_id_forzado(tmp_path: Path):
    data = _crear_fixture_primer_comprando(tmp_path)
    data["id_ejecucion"] = "IDPRUEBA001"
    path_maestro = Path(data["ruta_maestro"])
    pd.DataFrame({"Producto": ["1001"]}).to_excel(path_maestro, index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_primer_comprando(**data)

    assert error.value.codigo_error == "CST-VAL-001"

    archivos_manifiesto = list((Path(data["ruta_salida"])).glob("*manifiesto_primer_comprando_*.json"))
    assert archivos_manifiesto

    with open(archivos_manifiesto[0], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)

    assert manifiesto["estado"] == "ERROR"
    assert manifiesto["codigo_error"] == "CST-VAL-001"
    assert manifiesto["id_ejecucion"] == "IDPRUEBA001"

