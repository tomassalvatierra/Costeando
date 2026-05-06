import logging
import os
from datetime import datetime
from typing import Dict

import numpy as np
import pandas as pd

from costeando.utilidades.auditoria import guardar_manifiesto_ejecucion
from costeando.utilidades.errores_aplicacion import (
    ErrorAplicacion,
    ErrorEntradaArchivo,
    ErrorInternoInesperado,
    ErrorReglaNegocio,
    generar_id_ejecucion,
)
from costeando.utilidades.validaciones import (
    estandarizar_columna_producto,
    normalizar_campania,
    validar_anio,
    validar_archivo_excel,
    validar_columnas,
)

logger = logging.getLogger(__name__)


def estandarizar_codigo(df: pd.DataFrame) -> pd.DataFrame:
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    return df

def _validar_parametros_valorizacion_dyc(campania: str, anio: str, carpeta_guardado: str) -> tuple[str, str, str]:
    if not all([campania, anio]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan campania/anio en Valorizacion DYC.",
            codigo_error="CST-NEG-070",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania o anio para ejecutar Valorizacion DYC.",
            accion_sugerida="Complete campania y anio antes de ejecutar.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico ruta de salida en Valorizacion DYC.",
            codigo_error="CST-NEG-071",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta de salida valida.",
        )
    anio_normalizado = validar_anio(anio, "Valorizacion DYC", "CST-NEG-073")
    campania_normalizada = normalizar_campania(campania, "Valorizacion DYC", "CST-NEG-072")
    anio_campania = anio_normalizado[-1] + campania_normalizada
    return campania_normalizada, anio_normalizado, anio_campania


def _cargar_dataframes_valorizacion_dyc(
    ruta_listado: str,
    ruta_combinadas: str,
    ruta_dobles: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    try:
        df_dobles = pd.read_excel(ruta_dobles, engine="openpyxl")
        df_combinadas = pd.read_excel(ruta_combinadas, engine="openpyxl")
        df_listado = pd.read_excel(ruta_listado, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Valorizacion DYC: {error}",
            codigo_error="CST-IO-007",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_listado, df_combinadas, df_dobles


def _normalizar_columnas_entrada(
    df_listado: pd.DataFrame,
    df_combinadas: pd.DataFrame,
    df_dobles: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_listado = estandarizar_columna_producto(df_listado, "listado")
    validar_columnas(df_combinadas, ["CODIGON", "COMBINADA", "CANTIDAD", "DESCR_COMB"], "combinadas")
    validar_columnas(df_dobles, ["CODIGO_ORI", "CODIGO_DOB", "DESCR_DOB"], "dobles")

    df_combinadas = df_combinadas.rename(columns={"CODIGON": "Codigo"})
    df_dobles = df_dobles.rename(columns={"CODIGO_ORI": "Codigo"})

    df_listado = estandarizar_codigo(df_listado)
    df_combinadas = estandarizar_codigo(df_combinadas)
    df_dobles = estandarizar_codigo(df_dobles)
    return df_listado, df_combinadas, df_dobles


def _calcular_combinadas_valorizadas(
    df_listado: pd.DataFrame,
    df_combinadas: pd.DataFrame,
    columna_costo: str,
) -> pd.DataFrame:
    validar_columnas(df_listado, ["Codigo", columna_costo], "listado")
    df_combinadas = pd.merge(df_combinadas, df_listado[["Codigo", columna_costo]], on="Codigo", how="left")
    df_combinadas[columna_costo] = df_combinadas[columna_costo].replace(0, np.nan)
    df_combinadas["COSTO TOTAL"] = df_combinadas[columna_costo] * df_combinadas["CANTIDAD"]

    df_combinadas_valorizadas = (
        df_combinadas.groupby("COMBINADA")["COSTO TOTAL"]
        .apply(lambda valores: np.nan if valores.isnull().any() else valores.sum())
        .reset_index()
    )
    df_combinadas_valorizadas = df_combinadas_valorizadas.loc[
        (df_combinadas_valorizadas["COSTO TOTAL"] != 0)
        & (df_combinadas_valorizadas["COSTO TOTAL"].notna()),
        :,
    ]
    df_combinadas_valorizadas = df_combinadas_valorizadas.rename(
        columns={"COSTO TOTAL": columna_costo, "COMBINADA": "Codigo"}
    )

    df_combinadas = df_combinadas.rename(
        columns={"DESCR_COMB": "Descripcion", "Codigo": "CODIGON", "COMBINADA": "Codigo"}
    )
    df_combinadas_valorizadas = df_combinadas_valorizadas.merge(
        df_combinadas[["Codigo", "Descripcion"]],
        on="Codigo",
        how="left",
    )
    df_combinadas_valorizadas.drop_duplicates(subset="Codigo", keep="first", inplace=True)
    return df_combinadas_valorizadas


def _calcular_dobles_valorizados(
    df_listado: pd.DataFrame,
    df_dobles: pd.DataFrame,
    columna_costo: str,
) -> pd.DataFrame:
    validar_columnas(df_listado, ["Codigo", columna_costo], "listado")
    df_dobles_valorizados = pd.merge(df_dobles, df_listado[["Codigo", columna_costo]], on="Codigo", how="left")
    df_dobles_valorizados = df_dobles_valorizados.loc[
        (df_dobles_valorizados[columna_costo] != 0)
        & (df_dobles_valorizados[columna_costo].notna()),
        :,
    ]
    df_dobles_valorizados = df_dobles_valorizados.rename(
        columns={"DESCR_DOB": "Descripcion", "Codigo": "COD MADRE", "CODIGO_DOB": "Codigo"}
    )
    return df_dobles_valorizados


def _exportar_valorizacion_dyc(
    df_combinadas_valorizadas: pd.DataFrame,
    df_dobles_valorizados: pd.DataFrame,
    campania: str,
    anio: str,
    carpeta_guardado: str,
) -> str:
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_guardado = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Valorizacion DyC C{campania}-{anio}.xlsx",
    )
    with pd.ExcelWriter(path_guardado, engine="openpyxl") as writer:
        df_combinadas_valorizadas.to_excel(writer, sheet_name="MEMO COMBINADAS", index=False)
        df_dobles_valorizados.to_excel(writer, sheet_name="MEMO DOBLES", index=False)
    return path_guardado


def procesar_valorizacion_dyc_puro(
    ruta_listado: str,
    ruta_combinadas: str,
    ruta_dobles: str,
    campana: str,
    anio: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Valorizacion DYC. ID=%s", id_proceso)
        validar_archivo_excel(ruta_listado, "listado")
        validar_archivo_excel(ruta_combinadas, "combinadas")
        validar_archivo_excel(ruta_dobles, "dobles")
        campania_normalizada, anio, anio_campania = _validar_parametros_valorizacion_dyc(
            campana,
            anio,
            carpeta_guardado,
        )

        df_listado, df_combinadas, df_dobles = _cargar_dataframes_valorizacion_dyc(
            ruta_listado,
            ruta_combinadas,
            ruta_dobles,
        )
        df_listado, df_combinadas, df_dobles = _normalizar_columnas_entrada(
            df_listado,
            df_combinadas,
            df_dobles,
        )
        columna_costo = "COSTO LISTA " + anio_campania

        df_combinadas_valorizadas = _calcular_combinadas_valorizadas(
            df_listado,
            df_combinadas,
            columna_costo,
        )
        df_dobles_valorizados = _calcular_dobles_valorizados(
            df_listado,
            df_dobles,
            columna_costo,
        )
        path_guardado = _exportar_valorizacion_dyc(
            df_combinadas_valorizadas,
            df_dobles_valorizados,
            campania_normalizada,
            anio,
            carpeta_guardado,
        )
        logger.info("Archivo de Valorizacion DYC guardado en: %s", path_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="valorizacion_dyc",
            estado="OK",
            entradas={
                "ruta_listado": ruta_listado,
                "ruta_combinadas": ruta_combinadas,
                "ruta_dobles": ruta_dobles,
            },
            parametros={"campania": campania_normalizada, "anio": anio},
            metricas={
                "filas_combinadas": len(df_combinadas_valorizadas),
                "filas_dobles": len(df_dobles_valorizados),
            },
            archivos_generados={"valorizacion_dyc": path_guardado},
        )
        return {
            "valorizacion_dyc": path_guardado,
            "manifiesto": path_manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="valorizacion_dyc",
            estado="ERROR",
            entradas={
                "ruta_listado": ruta_listado,
                "ruta_combinadas": ruta_combinadas,
                "ruta_dobles": ruta_dobles,
            },
            parametros={"campania": campana, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Valorizacion DYC. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Valorizacion DYC: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Valorizacion DYC.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="valorizacion_dyc",
            estado="ERROR",
            entradas={
                "ruta_listado": ruta_listado,
                "ruta_combinadas": ruta_combinadas,
                "ruta_dobles": ruta_dobles,
            },
            parametros={"campania": campana, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Valorizacion DYC. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error
