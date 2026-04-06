import pandas as pd
from costeando.utilidades.validaciones import estandarizar_columna_producto


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
