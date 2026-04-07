import logging
import os
from datetime import datetime
from typing import Dict

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
    validar_archivo_excel,
    validar_columnas,
    validar_duplicados,
)

logger = logging.getLogger(__name__)

def _validar_parametros_actualizacion_fchs(carpeta_guardado: str):
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico carpeta de guardado en Actualizacion FCHS.",
            codigo_error="CST-NEG-080",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta valida para guardar resultados.",
        )


def _cargar_dataframes_actualizacion_fchs(
    ruta_estructuras: str,
    ruta_compras: str,
    ruta_maestro: str,
    ruta_ordenes_apuntadas: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    try:
        df_estructuras = pd.read_excel(
            ruta_estructuras,
            usecols="A:P",
            engine="openpyxl",
            skiprows=4,
        )
        df_compras = pd.read_excel(ruta_compras, engine="openpyxl")
        df_ordenes_apuntadas = pd.read_excel(ruta_ordenes_apuntadas, engine="openpyxl")
        df_maestro = pd.read_excel(ruta_maestro, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Actualizacion FCHS: {error}",
            codigo_error="CST-IO-008",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_estructuras, df_compras, df_ordenes_apuntadas, df_maestro


def _validar_columnas_minimas_actualizacion_fchs(
    df_estructuras: pd.DataFrame,
    df_compras: pd.DataFrame,
    df_ordenes_apuntadas: pd.DataFrame,
    df_maestro: pd.DataFrame,
):
    validar_columnas(df_estructuras, ["COD_NIVEL0", "CODIGO_PLANO"], "estructuras")
    validar_columnas(df_compras, ["Producto", "Fch Emision", "Descripcion", "Cantidad"], "compras")
    validar_columnas(df_ordenes_apuntadas, ["Producto", "Tipo Orden", "Fch Apunte"], "ordenes apuntadas")
    validar_columnas(df_maestro, ["Codigo", "Descripcion", "Sub Grupo", "Grupo"], "maestro")


def _normalizar_columnas_base(
    df_estructuras: pd.DataFrame,
    df_compras: pd.DataFrame,
    df_ordenes_apuntadas: pd.DataFrame,
    df_maestro: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_estructuras = df_estructuras.copy()
    df_compras = df_compras.copy()
    df_ordenes_apuntadas = df_ordenes_apuntadas.copy()
    df_maestro = df_maestro.copy()

    df_estructuras["COD_NIVEL0"] = df_estructuras["COD_NIVEL0"].astype(str).str.strip()
    df_estructuras["CODIGO_PLANO"] = df_estructuras["CODIGO_PLANO"].astype(str).str.strip()
    df_compras["Producto"] = df_compras["Producto"].astype(str).str.strip()
    df_ordenes_apuntadas["Producto"] = df_ordenes_apuntadas["Producto"].astype(str).str.strip()
    df_maestro["Codigo"] = df_maestro["Codigo"].astype(str).str.strip()
    df_maestro = df_maestro.rename(columns={"Codigo": "Producto"})
    return df_estructuras, df_compras, df_ordenes_apuntadas, df_maestro

def _generar_fechas_servicios(df_compras: pd.DataFrame, df_maestro: pd.DataFrame) -> pd.DataFrame:
    condicion_servicios = df_compras["Producto"].str.startswith("X", na=False)
    df_fch_servicios = df_compras.loc[condicion_servicios, ["Producto", "Fch Emision"]].copy()
    df_fch_servicios["Producto"] = df_fch_servicios["Producto"].str[1:]
    df_fch_servicios = pd.merge(
        df_fch_servicios,
        df_maestro[["Producto", "Descripcion"]],
        how="left",
        on="Producto",
    )
    df_fch_servicios["Tipo Orden"] = "POR OC CON X INICIAL"
    return df_fch_servicios


def _generar_fechas_161(
    df_estructuras: pd.DataFrame,
    df_compras: pd.DataFrame,
    df_maestro: pd.DataFrame,
) -> pd.DataFrame:
    condicion_161 = df_compras["Producto"].str.match(r"^161\d{4}$", na=False)
    df_fch_161 = df_compras.loc[condicion_161, ["Producto", "Fch Emision"]].copy()

    df_estructuras_cod = df_estructuras.rename(columns={"CODIGO_PLANO": "Producto"})
    df_maestro_nivel0 = df_maestro.rename(columns={"Producto": "COD_NIVEL0"})

    df_fch_161 = pd.merge(df_fch_161, df_estructuras_cod[["Producto", "COD_NIVEL0"]], how="left", on="Producto")
    df_fch_161 = df_fch_161.dropna(subset=["COD_NIVEL0"])
    df_fch_161 = pd.merge(df_fch_161, df_maestro[["Producto", "Sub Grupo"]], how="left", on="Producto")
    df_fch_161 = pd.merge(df_fch_161, df_maestro_nivel0[["COD_NIVEL0", "Grupo"]], how="left", on="COD_NIVEL0")

    df_fch_161["Grupo"] = pd.to_numeric(df_fch_161["Grupo"], errors="coerce")
    df_fch_161["Sub Grupo"] = pd.to_numeric(df_fch_161["Sub Grupo"], errors="coerce")
    df_fch_161 = df_fch_161.dropna(subset=["Grupo", "Sub Grupo"])

    df_fch_161 = df_fch_161.loc[~df_fch_161["Grupo"].isin([0, 1, 5, 6])]
    df_fch_161 = df_fch_161.loc[~df_fch_161["Sub Grupo"].isin([25, 901, 925])]

    df_fch_161 = df_fch_161.drop(columns=["Producto", "Sub Grupo", "Grupo"])
    df_fch_161 = df_fch_161.rename(columns={"COD_NIVEL0": "Producto"})
    df_fch_161 = pd.merge(df_fch_161, df_maestro[["Producto", "Descripcion"]], how="left", on="Producto")
    df_fch_161["Tipo Orden"] = "POR OC DEL COMPONENTE 161"
    return df_fch_161


def _generar_fechas_generales(df_compras: pd.DataFrame) -> pd.DataFrame:
    df_fch_generales = df_compras[["Producto", "Descripcion", "Fch Emision", "Cantidad"]].copy()
    df_fch_generales["Tipo Orden"] = "X OC"
    return df_fch_generales


def _generar_fechas_ordenes_apuntadas(df_ordenes_apuntadas: pd.DataFrame) -> pd.DataFrame:
    df_fchs_ordenes = df_ordenes_apuntadas.loc[
        ~df_ordenes_apuntadas["Tipo Orden"].isin(["Servicio", "Acondicionado"])
    ].copy()
    df_fchs_ordenes.sort_values(by=["Fch Apunte"], ascending=False, inplace=True)
    df_fchs_ordenes = df_fchs_ordenes.drop_duplicates(subset="Producto", keep="first")
    if "Grupo" in df_fchs_ordenes.columns:
        df_fchs_ordenes.drop(columns=["Grupo"], inplace=True)
    df_fchs_ordenes.rename(columns={"Fch Apunte": "Fch Emision"}, inplace=True)
    return df_fchs_ordenes


def _unificar_y_formatear_fechas(
    df_fch_generales: pd.DataFrame,
    df_fch_servicios: pd.DataFrame,
    df_fch_161: pd.DataFrame,
    df_fch_ordenes: pd.DataFrame,
    df_maestro: pd.DataFrame,
) -> pd.DataFrame:
    df_concatenado = pd.concat(
        [df_fch_generales, df_fch_servicios, df_fch_161, df_fch_ordenes],
        ignore_index=True,
    )
    df_concatenado = pd.merge(
        df_concatenado,
        df_maestro[["Producto", "Descripcion"]],
        how="left",
        on="Producto",
        suffixes=("", "_maestro"),
    )
    if "Descripcion_maestro" in df_concatenado.columns:
        df_concatenado["Descripcion"] = df_concatenado["Descripcion"].fillna(df_concatenado["Descripcion_maestro"])
        df_concatenado.drop(columns=["Descripcion_maestro"], inplace=True)

    df_concatenado = df_concatenado.drop_duplicates()
    df_concatenado["Fch Emision"] = pd.to_datetime(df_concatenado["Fch Emision"], errors="coerce")
    df_concatenado["FORMATO"] = df_concatenado["Fch Emision"].dt.strftime("%Y%m%d")
    df_concatenado = df_concatenado.dropna(subset=["FORMATO"])

    validar_columnas(df_concatenado, ["Producto", "Fch Emision", "FORMATO"], "compilado de fchs")
    if validar_duplicados(df_concatenado, ["Producto", "FORMATO"], "compilado final"):
        logger.info("Se detectaron duplicados en compilado final, se conserva la fecha mas reciente por producto.")
        df_concatenado.sort_values(by=["Producto", "Fch Emision"], ascending=[True, False], inplace=True)
        df_concatenado = df_concatenado.drop_duplicates(subset="Producto", keep="first")
    return df_concatenado


def _exportar_actualizacion_fchs(df_concatenado: pd.DataFrame, carpeta_guardado: str) -> str:
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_guardado = os.path.join(carpeta_guardado, f"{fecha_hoy} Compilado de fchs ult compra.xlsx")
    df_concatenado.to_excel(path_guardado, index=False, engine="openpyxl")
    return path_guardado


def procesar_actualizacion_fchs_puro(
    ruta_estructuras: str,
    ruta_compras: str,
    ruta_maestro: str,
    ruta_ordenes_apuntadas: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Actualizacion FCHS. ID=%s", id_proceso)
        validar_archivo_excel(ruta_estructuras, "estructuras")
        validar_archivo_excel(ruta_compras, "compras")
        validar_archivo_excel(ruta_maestro, "maestro")
        validar_archivo_excel(ruta_ordenes_apuntadas, "ordenes apuntadas")
        _validar_parametros_actualizacion_fchs(carpeta_guardado)

        df_estructuras, df_compras, df_ordenes_apuntadas, df_maestro = _cargar_dataframes_actualizacion_fchs(
            ruta_estructuras,
            ruta_compras,
            ruta_maestro,
            ruta_ordenes_apuntadas,
        )
        _validar_columnas_minimas_actualizacion_fchs(
            df_estructuras,
            df_compras,
            df_ordenes_apuntadas,
            df_maestro,
        )
        df_estructuras, df_compras, df_ordenes_apuntadas, df_maestro = _normalizar_columnas_base(
            df_estructuras,
            df_compras,
            df_ordenes_apuntadas,
            df_maestro,
        )

        df_fch_servicios = _generar_fechas_servicios(df_compras, df_maestro)
        df_fch_161 = _generar_fechas_161(df_estructuras, df_compras, df_maestro)
        df_fch_generales = _generar_fechas_generales(df_compras)
        df_fch_ordenes = _generar_fechas_ordenes_apuntadas(df_ordenes_apuntadas)

        df_concatenado = _unificar_y_formatear_fechas(
            df_fch_generales,
            df_fch_servicios,
            df_fch_161,
            df_fch_ordenes,
            df_maestro,
        )
        path_guardado = _exportar_actualizacion_fchs(df_concatenado, carpeta_guardado)
        logger.info("Archivo guardado en: %s", path_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="actualizacion_fchs",
            estado="OK",
            entradas={
                "ruta_estructuras": ruta_estructuras,
                "ruta_compras": ruta_compras,
                "ruta_maestro": ruta_maestro,
                "ruta_ordenes_apuntadas": ruta_ordenes_apuntadas,
            },
            parametros={},
            metricas={"filas_salida": len(df_concatenado)},
            archivos_generados={"actualizacion_fchs": path_guardado},
        )
        return {
            "actualizacion_fchs": path_guardado,
            "manifiesto": path_manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="actualizacion_fchs",
            estado="ERROR",
            entradas={
                "ruta_estructuras": ruta_estructuras,
                "ruta_compras": ruta_compras,
                "ruta_maestro": ruta_maestro,
                "ruta_ordenes_apuntadas": ruta_ordenes_apuntadas,
            },
            parametros={},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Actualizacion FCHS. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Actualizacion FCHS: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Actualizacion FCHS.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="actualizacion_fchs",
            estado="ERROR",
            entradas={
                "ruta_estructuras": ruta_estructuras,
                "ruta_compras": ruta_compras,
                "ruta_maestro": ruta_maestro,
                "ruta_ordenes_apuntadas": ruta_ordenes_apuntadas,
            },
            parametros={},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Actualizacion FCHS. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error
