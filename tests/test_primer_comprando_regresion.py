from datetime import datetime, timedelta
import json
from pathlib import Path

import pandas as pd

from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando


def _crear_fixture_regresion_primer_comprando(tmp_path: Path):
    campania = "02"
    anio = "2026"
    campania_anterior = "01"
    anio_campania_anterior = "601"
    fecha_compra_reciente = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

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
            "AAtiende Ne?": ["C", "C"],
            "Tipo": ["PA", "PA"],
            "Grupo": [1, 1],
            "Ult. Compra": [fecha_compra_reciente, fecha_compra_reciente],
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

    pd.DataFrame(
        {"Producto": ["1001", "MOD0806"], "COSTO LISTA " + anio_campania_anterior: [90.0, 10.0]}
    ).to_excel(path_listado, index=False)
    pd.DataFrame(
        {"Producto": ["1001", "MOD0806"], "Costo sin Descuento C" + campania_anterior: [95.0, 10.0]}
    ).to_excel(path_comprando_anterior, index=False)

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
        "id_ejecucion": "REGRESIONPC001",
    }


def test_regresion_valores_clave_calculo_comprando(tmp_path: Path):
    data = _crear_fixture_regresion_primer_comprando(tmp_path)
    resultados = procesar_primer_comprando(**data)

    df_resultado = pd.read_excel(resultados["calculo_comprando"], engine="openpyxl")
    df_resultado["Codigo"] = df_resultado["Codigo"].astype(str).str.strip()

    fila_1001 = df_resultado.loc[df_resultado["Codigo"] == "1001"].iloc[0]
    fila_mod0806 = df_resultado.loc[df_resultado["Codigo"] == "MOD0806"].iloc[0]

    assert fila_1001["Costo Compra"] == 100.0
    assert fila_1001["Costo sin Descuento C02"] == 100.0
    assert fila_1001["Coef de Actualizacion"] == 1.0
    assert fila_1001["% de obsolescencia"] == 0.0
    assert fila_1001["Clasificacion"] == "BAJA ROTACION"

    assert fila_mod0806["Costo Compra"] == 12.5
    assert fila_mod0806["Costo sin Descuento C02"] == 12.5
    assert fila_mod0806["Coef de Actualizacion"] == 1.0
    assert fila_mod0806["% de obsolescencia"] == 0.0
    assert fila_mod0806["Clasificacion"] == "BAJA ROTACION"


def test_regresion_descuentos_y_manifiesto(tmp_path: Path):
    data = _crear_fixture_regresion_primer_comprando(tmp_path)
    resultados = procesar_primer_comprando(**data)

    df_base_descuentos = pd.read_excel(resultados["base_descuentos"], engine="openpyxl")
    df_cambios = pd.read_excel(resultados["cambios"], engine="openpyxl")

    assert len(df_base_descuentos) == 2
    assert len(df_cambios) == 2
    assert set(df_base_descuentos["VENCIDO"]) == {"Si"}
    assert set(df_cambios["VENCIDO"]) == {"Si"}

    with open(resultados["manifiesto"], "r", encoding="utf-8") as archivo:
        manifiesto = json.load(archivo)

    assert manifiesto["id_ejecucion"] == "REGRESIONPC001"
    assert manifiesto["estado"] == "OK"
    assert manifiesto["metricas"]["filas_salida"] == 2
