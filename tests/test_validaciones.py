import pandas as pd
import pytest

from costeando.utilidades.errores_aplicacion import ErrorEsquemaArchivo
from costeando.utilidades.validaciones import (
    estandarizar_columna_producto,
    validar_columna_fecha_parseable,
    validar_columna_numerica,
)


def test_estandarizar_columna_producto():
    df= pd.DataFrame({
        'Producto':['10001', '10001', '10002']
        })
    resultado = estandarizar_columna_producto(df, 'df_prueba')
    assert ("Codigo" in resultado.columns)
    
    
def test_estandarizar_columna_espacios():
    df=pd.DataFrame({
        'Producto':['1000 ', '1253  ', '15556']
    })
    df=estandarizar_columna_producto(df, 'df_prueba')
    resultado = (df["Codigo"].str.contains(' ')).any()
    assert resultado == False
    
def test_estandarizar_columna_enteros():
    df=pd.DataFrame({
        'Producto': [153,'123',2,4,'X4589']
    })
    df=estandarizar_columna_producto(df,'df_prueba')
    resultado = (df['Codigo'].apply(type)).all()
    assert resultado==True


def test_validar_columna_numerica_falla_si_hay_un_valor_invalido():
    df = pd.DataFrame({"Costo": [10, "sin_numero", 30]})

    with pytest.raises(ErrorEsquemaArchivo) as error:
        validar_columna_numerica(df, "Costo", "costos")

    assert error.value.codigo_error == "CST-VAL-003"


def test_validar_columna_fecha_falla_si_hay_un_valor_invalido():
    df = pd.DataFrame({"Fecha": ["2026-01-01", "sin_fecha", "2026-01-03"]})

    with pytest.raises(ErrorEsquemaArchivo) as error:
        validar_columna_fecha_parseable(df, "Fecha", "fechas")

    assert error.value.codigo_error == "CST-VAL-004"
