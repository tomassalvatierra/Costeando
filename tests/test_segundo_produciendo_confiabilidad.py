from pathlib import Path

import pandas as pd
import pytest

from costeando.modulos.procesamiento_segundo_produciendo import (
    incorporar_nuevos_dtos,
    procesar_segundo_produciendo,
)
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


def test_caso_minimo_valido_genera_salidas_sin_manifiesto(tmp_path: Path):
    data = _crear_fixture_segundo_produciendo(tmp_path)
    resultados = procesar_segundo_produciendo(**data)

    assert Path(resultados["importador"]).exists()
    assert Path(resultados["produciendo"]).exists()
    assert Path(resultados["especiales"]).exists()
    assert resultados["id_ejecucion"]
    assert "manifiesto" not in resultados


def test_incorporar_nuevos_dtos_pisa_descuento_vigente_y_agrega_historial():
    df_especiales = pd.DataFrame(
        {
            "Codigo": ["2001", "2002"],
            "DESCUENTO ESPECIAL": [5.0, 0.0],
            "APLICA DDE CA:": ["2025/01", "2025/01"],
            "VENCIDO": ["No", "No"],
            "NOTAS": ["", ""],
        }
    )
    df_importador = pd.DataFrame(
        {
            "Codigo": ["2001", "2002", "2003"],
            "DESCUENTO ESPECIAL": [12.0, 8.0, 4.0],
            "APLICA DDE CA:": ["2026/02", "2026/02", "2026/02"],
        }
    )
    df_productos = pd.DataFrame(
        {
            "Codigo": ["2001", "2002", "2003", "2004"],
            "DESCUENTO ESPECIAL": [5.0, 0.0, None, 3.0],
            "APLICA DDE CA:": ["2025/01", "2025/01", None, "2025/01"],
        }
    )

    df_base_actualizada, df_productos_actualizados = incorporar_nuevos_dtos(
        df_especiales,
        df_importador,
        df_productos,
    )

    descuentos_por_codigo = df_productos_actualizados.set_index("Codigo")["DESCUENTO ESPECIAL"]
    aplica_por_codigo = df_productos_actualizados.set_index("Codigo")["APLICA DDE CA:"]
    assert descuentos_por_codigo["2001"] == 12.0
    assert descuentos_por_codigo["2002"] == 8.0
    assert descuentos_por_codigo["2003"] == 4.0
    assert descuentos_por_codigo["2004"] == 3.0
    assert aplica_por_codigo["2001"] == "2026/02"
    assert aplica_por_codigo["2002"] == "2026/02"
    assert aplica_por_codigo["2003"] == "2026/02"
    assert aplica_por_codigo["2004"] == "2025/01"

    anteriores = df_base_actualizada[
        (df_base_actualizada["Codigo"].isin(["2001", "2002"]))
        & (df_base_actualizada["APLICA DDE CA:"] == "2025/01")
    ]
    assert anteriores["VENCIDO"].tolist() == ["Si", "Si"]
    assert anteriores["NOTAS"].tolist() == [
        "Vencido, ingreso un nuevo descuento",
        "Vencido, ingreso un nuevo descuento",
    ]

    nuevos = df_base_actualizada[df_base_actualizada["APLICA DDE CA:"] == "2026/02"]
    assert nuevos["Codigo"].tolist() == ["2001", "2002", "2003"]
    assert nuevos["DESCUENTO ESPECIAL"].tolist() == [12.0, 8.0, 4.0]
