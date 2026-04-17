import json
from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_listado_gral import procesar_listado_gral_puro
from costeando.utilidades.errores_aplicacion import ErrorEsquemaArchivo, ErrorReglaNegocio


def _crear_fixture_listado_general(tmp_path: Path):
    campania = "02"
    anio = "2026"

    path_produciendo = tmp_path / "produciendo.xlsx"
    path_comprando = tmp_path / "comprando.xlsx"
    path_costo_primo = tmp_path / "costo_primo.xlsx"
    path_base_descuentos = tmp_path / "base_descuentos.xlsx"
    path_listado = tmp_path / "listado.xlsx"
    path_mdo = tmp_path / "mdo.xlsx"
    path_leader = tmp_path / "leader.xlsx"
    path_compilado = tmp_path / "compilado.xlsx"
    path_salida = tmp_path / "salida"

    pd.DataFrame(
        {
            "Producto": ["1001"],
            "Costo Producción": [100.0],
            "Costo sin Descuento C02": [110.0],
            "% de obsolescencia": [2.0],
            "ROYALTY": [1.0],
            "DESCUENTO ESPECIAL": [3.0],
            "APLICA DDE CA:": ["2025/01"],
        }
    ).to_excel(path_produciendo, index=False)

    pd.DataFrame(
        {
            "Producto": ["1001"],
            "Costo sin Descuento C02": [110.0],
            "% de obsolescencia": [2.0],
            "ROYALTY": [1.0],
            "DESCUENTO ESPECIAL": [3.0],
            "APLICA DDE CA:": ["2025/01"],
        }
    ).to_excel(path_comprando, index=False)

    pd.DataFrame({"Producto": ["1001"], "Costo Estand": [80.0]}).to_excel(path_costo_primo, index=False)
    pd.DataFrame({"Producto": ["1001"], "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO"]}).to_excel(path_base_descuentos, index=False)
    pd.DataFrame(
        {
            "Producto": ["1001"],
            "Costo Estandard": [120.0],
            "Stock Actual": [10],
            "Periodo": ["2026-02"],
            "Descripcion": ["ITEM 1001"],
            "TIPO DE COSTO": ["X"],
            "ADI NÂ°": [""],
            "Ult. Compra": ["2026-01-01"],
            "Estado": ["ACTIVO"],
            "Cod Actualiz": ["A"],
            "VARIABLE": ["N"],
            "LLEVA CF": ["Si"],
            "Tipo": ["PA"],
            "Desc.Tipo": ["TIPO"],
            "Grupo": [1],
            "Desc. Grupo": ["G1"],
            "Sub Grupo": [1],
            "Desc.Sub Grupo": ["SG1"],
            "Entra MRP": ["Si"],
            "Atiende Necsdd": ["C"],
            "Prov": ["P1"],
            "Ult P/C": ["C"],
            "Razon Social": ["PROV 1"],
            "Fecha Alta": ["2020-01-01"],
        }
    ).to_excel(path_listado, index=False)

    df_mdo = pd.DataFrame(
        {
            "Producto": ["1001", "1001", "1001"],
            "Componente": ["MOD0806", "MOD0807", "MOD0808"],
            "Cantidad": [1.0, 2.0, 3.0],
        }
    )
    with pd.ExcelWriter(path_mdo, engine="openpyxl") as writer:
        df_mdo.to_excel(writer, index=False, startrow=1)

    pd.DataFrame({"Producto": ["1001"], "TIPO_OF": ["A"], "LEYEOFE": ["L1"]}).to_excel(path_leader, index=False)
    pd.DataFrame({"Producto": ["1001"], "Tipo Orden": ["OC"]}).to_excel(path_compilado, index=False)

    return {
        "ruta_produciendo": str(path_produciendo),
        "ruta_comprando": str(path_comprando),
        "ruta_costo_primo": str(path_costo_primo),
        "ruta_base_descuentos": str(path_base_descuentos),
        "ruta_listado": str(path_listado),
        "ruta_mdo": str(path_mdo),
        "ruta_leader_list": str(path_leader),
        "ruta_compilado_fechas_ult_compra": str(path_compilado),
        "campania": campania,
        "anio": anio,
        "carpeta_guardado": str(path_salida),
        "id_ejecucion": "IDLST001",
    }


def test_listado_general_ok_genera_salida_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_listado_general(tmp_path)
    resultado = procesar_listado_gral_puro(**data)

    assert Path(resultado["Listado_general_completo"]).exists()
    assert Path(resultado["manifiesto"]).exists()
    assert resultado["id_ejecucion"] == "IDLST001"

    with open(resultado["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)

    assert manifiesto["estado"] == "OK"
    assert manifiesto["proceso"] == "listado_general"
    assert manifiesto["metricas"]["filas_salida"] == 1


def test_listado_general_falla_si_falta_columna_en_leader(tmp_path: Path):
    data = _crear_fixture_listado_general(tmp_path)
    path_leader = Path(data["ruta_leader_list"])
    pd.DataFrame({"Producto": ["1001"], "TIPO_OF": ["A"]}).to_excel(path_leader, index=False)

    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_listado_gral_puro(**data)

    assert error.value.codigo_error == "CST-VAL-001"
    manifiestos = list(Path(data["carpeta_guardado"]).glob("*manifiesto_listado_general_*.json"))
    assert manifiestos


def test_listado_general_falla_si_parametros_incompletos(tmp_path: Path):
    data = _crear_fixture_listado_general(tmp_path)
    data["campania"] = ""

    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_listado_gral_puro(**data)

    assert error.value.codigo_error == "CST-NEG-030"

