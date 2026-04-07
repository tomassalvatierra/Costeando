from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_primer_produciendo import procesar_primer_produciendo
from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
)


def _crear_estructuras_excel(path_estructuras: Path):
    columnas = [
        "COD_NIVEL0",
        "QUANT_NIVEL1",
        "QUANT_NIVEL2",
        "QUANT_NIVEL3",
        "COSTO_NIVEL3",
        "DESC_NIVEL3",
        "COMP_NIVEL3",
        "COMP_NIVEL1",
        "COMP_NIVEL2",
        "COSTO_NIVEL2",
        "DESC_NIVEL2",
        "COSTO_NIVEL1",
        "DESC_NIVEL1",
        "X1",
        "X2",
    ]
    df = pd.DataFrame(
        [
            ["2001", 1, 1, 1, 0, "comp3", "3001", "2101", "2201", 0, "comp2", 0, "comp1", "", ""],
            ["MOD0806", 1, 1, 1, 10, "ok", "3002", "2102", "2202", 10, "ok", 10, "ok", "", ""],
        ],
        columns=columnas,
    )
    with pd.ExcelWriter(path_estructuras, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, startrow=4)


def _crear_fixture_primer_produciendo(tmp_path: Path):
    path_produciendo_anterior = tmp_path / "produciendo_anterior.xlsx"
    path_maestro = tmp_path / "maestro.xlsx"
    path_stock = tmp_path / "stock.xlsx"
    path_descuentos = tmp_path / "descuentos.xlsx"
    path_rotacion = tmp_path / "rotacion.xlsx"
    path_estructuras = tmp_path / "estructuras.xlsx"

    pd.DataFrame(
        {
            "Producto": ["2001", "MOD0806"],
            "LLEVA CF": ["Si", "No"],
            "Revision de tipo": ["", ""],
        }
    ).to_excel(path_produciendo_anterior, index=False)

    pd.DataFrame(
        {
            "Producto": ["2001", "MOD0806"],
            "Blq. de Pant": [2, 2],
            "Atiende Ne?": ["P", "P"],
            "Tipo": ["PA", "PA"],
            "Grupo": [1, 1],
            "Ult. Compra": ["2025-01-01", "2025-01-01"],
            "Costo Estand": [84.0, 50.0],
            "Descripcion": ["Prod 2001", "Prod MOD0806"],
        }
    ).to_excel(path_maestro, index=False)

    pd.DataFrame({"Producto": ["2001", "MOD0806"], "Stock Actual": [1000, 100]}).to_excel(path_stock, index=False)

    pd.DataFrame(
        {
            "Producto": ["2001", "MOD0806"],
            "VENCIDO": ["No", "No"],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "TIPO-DESCUENTO": ["AGOTAMIENTO-PRODUCTO TERMINADO", "AGOTAMIENTO-PRODUCTO TERMINADO"],
            "DESCUENTO ESPECIAL": [5.0, 0.0],
            "ROYALTY": [0.0, 0.0],
        }
    ).to_excel(path_descuentos, index=False)

    pd.DataFrame({"Producto": ["2001", "MOD0806"], "Clasificacion": ["ROTACION NORMAL", "BAJA ROTACION"]}).to_excel(path_rotacion, index=False)
    _crear_estructuras_excel(path_estructuras)

    return {
        "campania_actual": "02",
        "anio_actual": "2026",
        "ruta_produciendo_anterior": str(path_produciendo_anterior),
        "ruta_maestro_produciendo": str(path_maestro),
        "ruta_stock": str(path_stock),
        "ruta_descuentos_especiales": str(path_descuentos),
        "ruta_rotacion": str(path_rotacion),
        "ruta_estructuras": str(path_estructuras),
        "ruta_salida": str(tmp_path / "salida"),
    }


def test_falla_si_faltan_parametros_requeridos(tmp_path: Path):
    data = _crear_fixture_primer_produciendo(tmp_path)
    data["campania_actual"] = ""
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_primer_produciendo(**data)
    assert error.value.codigo_error == "CST-NEG-020"


def test_falla_si_archivo_no_existe(tmp_path: Path):
    data = _crear_fixture_primer_produciendo(tmp_path)
    data["ruta_stock"] = str(tmp_path / "no_existe.xlsx")
    with pytest.raises(ErrorEntradaArchivo) as error:
        procesar_primer_produciendo(**data)
    assert error.value.codigo_error == "CST-IO-001"


def test_falla_si_faltan_columnas_en_maestro(tmp_path: Path):
    data = _crear_fixture_primer_produciendo(tmp_path)
    pd.DataFrame({"Producto": ["2001"]}).to_excel(data["ruta_maestro_produciendo"], index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_primer_produciendo(**data)
    assert error.value.codigo_error == "CST-VAL-001"


def test_caso_minimo_valido_genera_salidas_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_primer_produciendo(tmp_path)
    resultados = procesar_primer_produciendo(**data)
    assert Path(resultados["produciendo"]).exists()
    assert Path(resultados["base_descuentos"]).exists()
    assert Path(resultados["cambios"]).exists()
    assert Path(resultados["manifiesto"]).exists()
    assert resultados["id_ejecucion"]

