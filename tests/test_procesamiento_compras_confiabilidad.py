from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_compras import procesar_compras_puro
from costeando.utilidades.errores_aplicacion import ErrorReglaNegocio, ErrorEsquemaArchivo


def _crear_excel_compras_valido(path_archivo: Path):
    df = pd.DataFrame(
        {
            "Resid. Elim.": ["N"],
            "Producto": ["1001"],
            "Observacion": [""],
            "Notas": [0],
            "Tipo": ["Normal"],
            "MONEDA": ["Peso"],
            "Prc.Unitario": [10.0],
            "Fch Emision": ["2026-03-01"],
            "ULTCOS": [10.0],
            "Costo Estand": [8.0],
        }
    )
    df.to_excel(path_archivo, index=False)


def test_compras_falla_si_dolar_no_positivo(tmp_path: Path):
    path_compras = tmp_path / "compras.xlsx"
    _crear_excel_compras_valido(path_compras)
    with pytest.raises(ErrorReglaNegocio) as error:
        procesar_compras_puro(
            ruta_compras=str(path_compras),
            dolar=0,
            carpeta_guardado=str(tmp_path),
        )
    assert error.value.codigo_error == "CST-NEG-001"


def test_compras_falla_si_faltan_columnas(tmp_path: Path):
    path_compras = tmp_path / "compras.xlsx"
    df = pd.DataFrame({"Producto": ["1001"], "MONEDA": ["Peso"]})
    df.to_excel(path_compras, index=False)
    with pytest.raises(ErrorEsquemaArchivo) as error:
        procesar_compras_puro(
            ruta_compras=str(path_compras),
            dolar=1000,
            carpeta_guardado=str(tmp_path),
        )
    assert error.value.codigo_error == "CST-VAL-001"
