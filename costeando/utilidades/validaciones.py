import logging
import os

import pandas as pd

from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
)

logger = logging.getLogger(__name__)


def validar_archivo_excel(path: str, nombre: str = "archivo"):
    if not path or not os.path.isfile(path):
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se encontro el {nombre} o la ruta es invalida: {path}",
            codigo_error="CST-IO-001",
            titulo_usuario="Archivo no encontrado",
            mensaje_usuario=f"No se encontro el archivo requerido: {nombre}.",
            accion_sugerida="Verifique la ruta del archivo y vuelva a intentar.",
        )
    if not path.lower().endswith((".xlsx", ".xls")):
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"El {nombre} no es un archivo Excel valido: {path}",
            codigo_error="CST-IO-002",
            titulo_usuario="Formato de archivo invalido",
            mensaje_usuario=f"El archivo seleccionado para {nombre} no es un Excel valido.",
            accion_sugerida="Seleccione un archivo con extension .xlsx o .xls.",
        )


def validar_columnas(df: pd.DataFrame, columnas_obligatorias: list, nombre_df: str = "DataFrame"):
    faltantes = [col for col in columnas_obligatorias if col not in df.columns]
    if faltantes:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"Faltan columnas en {nombre_df}: {faltantes}",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario=f"El archivo {nombre_df} no contiene todas las columnas requeridas.",
            accion_sugerida=f"Revise columnas obligatorias: {', '.join(columnas_obligatorias)}.",
        )


def validar_no_nulos(df: pd.DataFrame, columnas: list, nombre_df: str = "DataFrame"):
    for col in columnas:
        if col in df.columns and df[col].isnull().any():
            raise ErrorEsquemaArchivo(
                mensaje_tecnico=f"Hay valores nulos en la columna {col} de {nombre_df}",
                codigo_error="CST-VAL-002",
                titulo_usuario="Datos incompletos",
                mensaje_usuario=f"La columna {col} del archivo {nombre_df} contiene valores faltantes.",
                accion_sugerida="Complete los valores faltantes y vuelva a ejecutar.",
            )


def validar_duplicados(df: pd.DataFrame, columnas: list, nombre_df: str = "DataFrame"):
    if df.duplicated(subset=columnas).any():
        return True
    return False


def validar_columna_numerica(df: pd.DataFrame, columna: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna], nombre_df)
    valores = pd.to_numeric(df[columna], errors="coerce")
    if valores.isna().all():
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"Todos los valores de {columna} son invalidos en {nombre_df}",
            codigo_error="CST-VAL-003",
            titulo_usuario="Tipo de dato invalido",
            mensaje_usuario=f"La columna {columna} del archivo {nombre_df} no contiene valores numericos validos.",
            accion_sugerida=f"Revise el formato numerico de la columna {columna}.",
        )


def validar_columna_fecha_parseable(df: pd.DataFrame, columna: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna], nombre_df)
    fechas = pd.to_datetime(df[columna], errors="coerce", format="mixed")
    if fechas.isna().all():
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"No se pudieron interpretar fechas en {columna} de {nombre_df}",
            codigo_error="CST-VAL-004",
            titulo_usuario="Formato de fecha invalido",
            mensaje_usuario=f"La columna {columna} del archivo {nombre_df} no tiene fechas validas.",
            accion_sugerida="Corrija el formato de fecha (ejemplo: dd/mm/aaaa) y reintente.",
        )


def validar_clave_unica(df: pd.DataFrame, columna_clave: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna_clave], nombre_df)
    if df[columna_clave].duplicated().any():
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"Se detectaron claves duplicadas en {columna_clave} para {nombre_df}",
            codigo_error="CST-VAL-005",
            titulo_usuario="Clave duplicada",
            mensaje_usuario=f"El archivo {nombre_df} contiene valores repetidos en {columna_clave}.",
            accion_sugerida=f"Elimine duplicados en {columna_clave} y vuelva a procesar.",
        )


def estandarizar_columna_producto(df: pd.DataFrame, nombre_df: str) -> pd.DataFrame:
    """
    Renombra la columna 'Producto' a 'Codigo' si existe, y normaliza su contenido.
    Si ya existe 'Codigo', solo normaliza. Registra el cambio en el log.
    """
    if "Producto" in df.columns:
        df = df.rename(columns={"Producto": "Codigo"})
        logger.debug("Columna 'Producto' renombrada a 'Codigo' en %s.", nombre_df)
    else:
        logger.debug("No se encontro la columna 'Producto' en %s.", nombre_df)
    if "Codigo" not in df.columns:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"No existe columna Codigo en {nombre_df} tras normalizacion.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario=f"El archivo {nombre_df} no contiene Codigo ni Producto.",
            accion_sugerida="Verifique el encabezado de la clave de producto.",
        )
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    return df
