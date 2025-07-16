import os
import pandas as pd

def validar_archivo_excel(path: str, nombre: str = "archivo"):
    if not path or not os.path.isfile(path):
        raise ValueError(f"No se encontró el {nombre} o la ruta es inválida: {path}")
    if not path.lower().endswith(('.xlsx', '.xls')):
        raise ValueError(f"El {nombre} no es un archivo Excel válido: {path}")

def validar_columnas(df: pd.DataFrame, columnas_obligatorias: list, nombre_df: str = "DataFrame"):
    faltantes = [col for col in columnas_obligatorias if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas en {nombre_df}: {faltantes}")

def validar_no_nulos(df: pd.DataFrame, columnas: list, nombre_df: str = "DataFrame"):
    for col in columnas:
        if col in df.columns and df[col].isnull().any():
            raise ValueError(f"Hay valores nulos en la columna '{col}' de {nombre_df}")

def validar_duplicados(df: pd.DataFrame, columnas: list, nombre_df: str = "DataFrame"):
    if df.duplicated(subset=columnas).any():
        raise ValueError(f"Hay duplicados en las columnas {columnas} de {nombre_df}") 