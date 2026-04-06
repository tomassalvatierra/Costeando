from datetime import datetime
from typing import Dict

import logging
import os

import numpy as np
import pandas as pd

from costeando.utilidades.auditoria import guardar_manifiesto_ejecucion
from costeando.utilidades.errores_aplicacion import (
    ErrorAplicacion,
    ErrorEscrituraSalida,
    ErrorInternoInesperado,
    ErrorReglaNegocio,
    generar_id_ejecucion,
)
from costeando.utilidades.validaciones import (
    validar_archivo_excel,
    validar_columna_fecha_parseable,
    validar_columna_numerica,
    validar_columnas,
)

logger = logging.getLogger(__name__)

PALABRAS_EXCLUIDAS_PRODUCTO = ["MAT", "GAS", "BSUSO", "FLE", "HON", "SER"]
TIPOS_COSTO_EXCLUIDOS = ["Excedente - Pesos", "Sufacturacion - Dolar", "Excedente - Dolar"]
COLUMNAS_OBLIGATORIAS_COMPRAS = [
    "Resid. Elim.",
    "Producto",
    "Observacion",
    "Notas",
    "Tipo",
    "MONEDA",
    "Prc.Unitario",
    "Fch Emision",
    "ULTCOS",
    "Costo Estand",
]


def clasificacion_compras(row):
    try:
        tipo = row["Tipo"]
        moneda = row["MONEDA"]
        notas = row["Notas"]
        precio_unitario = row["Prc.Unitario"]
    except KeyError as error:
        return f"Error: Falta la columna {error}"

    if pd.isnull(notas):
        notas = 0
    if tipo == "Normal":
        return "Normal"
    if tipo == "Excedente" and moneda == "Peso":
        if notas == 0:
            return "Excedente - Pesos"
        return "Pesificada"
    if tipo == "Excedente" and moneda == "Dolar":
        if notas == 0:
            return "Excedente - Dolar"
        try:
            resultado = notas / precio_unitario
            if 1.8 <= resultado <= 2.4:
                return "Sufacturacion - Dolar"
            if 0.7 <= resultado <= 1.3:
                return "Excedente - Dolar"
        except ZeroDivisionError:
            return "Error: Precio Unitario es 0"
    return "Otro"


def resolver_duplicados(df_repetidos: pd.DataFrame) -> pd.DataFrame:
    lista_resultados = []
    for _, grupo in df_repetidos.groupby("Producto", sort=False):
        grupo = grupo.copy().reset_index(drop=True)
        if grupo["Prc.Unitario"].nunique() == 1:
            lista_resultados.append(grupo.iloc[[0]])
            continue
        fecha_maxima = grupo["Fch Emision"].max()
        candidatos = grupo[grupo["Fch Emision"] == fecha_maxima].copy()
        if len(candidatos) == 1:
            lista_resultados.append(candidatos)
        else:
            candidatos["Para compras?"] = "SI"
            lista_resultados.append(candidatos)
    if not lista_resultados:
        return pd.DataFrame(columns=df_repetidos.columns)
    return pd.concat(lista_resultados, ignore_index=True)


def _validar_parametros_iniciales(ruta_compras: str, dolar: float, carpeta_guardado: str):
    validar_archivo_excel(ruta_compras, "Compras")
    if dolar <= 0:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Cotizacion dolar invalida: {dolar}",
            codigo_error="CST-NEG-001",
            titulo_usuario="Parametro invalido",
            mensaje_usuario="La cotizacion del dolar debe ser mayor a cero.",
            accion_sugerida="Ingrese una cotizacion valida y vuelva a ejecutar.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se recibio carpeta de guardado.",
            codigo_error="CST-NEG-002",
            titulo_usuario="Falta carpeta de salida",
            mensaje_usuario="No se definio una carpeta para guardar resultados.",
            accion_sugerida="Seleccione una carpeta de salida y vuelva a intentar.",
        )


def _leer_y_validar_compras(ruta_compras: str) -> pd.DataFrame:
    try:
        df_compras = pd.read_excel(ruta_compras, engine="openpyxl")
    except Exception as error:
        raise ErrorInternoInesperado(
            mensaje_tecnico=f"Fallo lectura de compras: {error}",
            codigo_error="CST-IO-003",
            titulo_usuario="No se pudo leer el archivo",
            mensaje_usuario="No fue posible leer el archivo de compras.",
            accion_sugerida="Verifique que el archivo no este daAado ni abierto por otra aplicacion.",
        ) from error

    validar_columnas(df_compras, COLUMNAS_OBLIGATORIAS_COMPRAS, "Compras")
    validar_columna_numerica(df_compras, "Costo Estand", "Compras")
    validar_columna_numerica(df_compras, "Prc.Unitario", "Compras")
    validar_columna_fecha_parseable(df_compras, "Fch Emision", "Compras")
    return df_compras


def _filtrar_y_normalizar_compras(df_compras: pd.DataFrame) -> pd.DataFrame:
    df_resultado = df_compras.copy()
    df_resultado = df_resultado.loc[df_resultado["Resid. Elim."] != "S", :].copy()
    df_resultado["Producto"] = df_resultado["Producto"].astype(str).str.strip()

    for palabra in PALABRAS_EXCLUIDAS_PRODUCTO:
        mascara = df_resultado["Producto"].str.contains(palabra, case=False, na=False)
        df_resultado = df_resultado.loc[~mascara, :].copy()

    mascara_rechazo = df_resultado["Observacion"].apply(lambda x: "RECHAZO" in str(x).upper())
    df_resultado = df_resultado.loc[~mascara_rechazo, :].copy()
    df_resultado["Notas"] = pd.to_numeric(df_resultado["Notas"], errors="coerce")
    return df_resultado


def _aplicar_reglas_costos(df_compras: pd.DataFrame, dolar: float) -> pd.DataFrame:
    df_resultado = df_compras.copy()
    df_resultado["Tipo-Costos"] = df_resultado.apply(clasificacion_compras, axis=1)
    df_resultado = df_resultado.loc[
        ~df_resultado["Tipo-Costos"].isin(TIPOS_COSTO_EXCLUIDOS), :
    ].copy()
    df_resultado.loc[df_resultado["Notas"].notna(), "Prc.Unitario"] = df_resultado["Notas"]
    df_resultado.loc[df_resultado["Notas"].notna(), "MONEDA"] = "Dolar"
    df_resultado = df_resultado.sort_values(
        by=["Producto", "Fch Emision", "ULTCOS"],
        ascending=[True, False, False],
    ).reset_index(drop=True)
    df_resultado.drop_duplicates(subset=["Producto", "ULTCOS", "Fch Emision"], inplace=True)
    df_resultado["Para compras?"] = ""

    mascara_repetidos = df_resultado.duplicated(subset="Producto", keep=False)
    df_repetidos = df_resultado.loc[mascara_repetidos, :].copy()
    df_unicos = df_resultado.loc[~mascara_repetidos, :].copy()
    df_repetidos_resueltos = resolver_duplicados(df_repetidos)

    df_depuradas = pd.concat([df_unicos, df_repetidos_resueltos], ignore_index=True)
    df_depuradas["Tasa Moneda"] = np.where(df_depuradas["MONEDA"] == "Dolar", dolar, 1.0)
    df_depuradas["ULTCOS"] = (df_depuradas["Prc.Unitario"] * df_depuradas["Tasa Moneda"]).round(2)
    df_depuradas["Var"] = (
        (df_depuradas["ULTCOS"] / df_depuradas["Costo Estand"]) - 1
    ).replace({np.inf: "NUEVO"})
    df_depuradas.drop(columns=["Verificacion"], inplace=True, errors="ignore")
    df_depuradas.sort_values(
        by=["Producto", "Fch Emision", "ULTCOS"],
        ascending=[True, False, False],
        inplace=True,
    )
    df_depuradas["OBSERVACIONES COSTOS"] = ""
    df_depuradas["RESPUESTA COMPRAS"] = ""
    return df_depuradas


def _guardar_salida_compras(df_depuradas: pd.DataFrame, carpeta_guardado: str) -> str:
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_guardado = os.path.join(carpeta_guardado, f"{fecha_hoy} Compras depuradas.xlsx")
    try:
        df_depuradas.to_excel(path_guardado, index=False)
    except Exception as error:
        raise ErrorEscrituraSalida(
            mensaje_tecnico=f"No se pudo guardar archivo de salida: {error}",
            codigo_error="CST-IO-004",
            titulo_usuario="Error al guardar salida",
            mensaje_usuario="No se pudo generar el archivo de compras depuradas.",
            accion_sugerida="Verifique permisos en la carpeta de salida y cierre el archivo si estaba abierto.",
        ) from error
    return path_guardado


def procesar_compras_puro(
    ruta_compras: str,
    dolar: float,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    """
    Procesa el archivo de compras y guarda el archivo generado en la carpeta indicada.
    Devuelve un diccionario con los paths de salida (incluye manifiesto de auditoria).
    """
    id_proceso = id_ejecucion or generar_id_ejecucion()
    logger.info("Iniciando procesamiento de compras. ID ejecucion=%s", id_proceso)
    _validar_parametros_iniciales(ruta_compras, dolar, carpeta_guardado)

    try:
        df_compras = _leer_y_validar_compras(ruta_compras)
        total_filas_entrada = len(df_compras)
        df_normalizado = _filtrar_y_normalizar_compras(df_compras)
        total_filas_filtradas = len(df_normalizado)
        df_depuradas = _aplicar_reglas_costos(df_normalizado, dolar)
        total_filas_salida = len(df_depuradas)
        path_compras = _guardar_salida_compras(df_depuradas, carpeta_guardado)

        manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="compras",
            estado="OK",
            entradas={"ruta_compras": ruta_compras},
            parametros={"dolar": dolar},
            metricas={
                "filas_entrada": total_filas_entrada,
                "filas_post_filtro": total_filas_filtradas,
                "filas_salida": total_filas_salida,
            },
            archivos_generados={"compras_depuradas": path_compras},
        )
        logger.info("Proceso compras finalizado. ID=%s", id_proceso)
        return {
            "compras_depuradas": path_compras,
            "manifiesto": manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="compras",
            estado="ERROR",
            entradas={"ruta_compras": ruta_compras},
            parametros={"dolar": dolar},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error("Error controlado en compras. ID=%s Codigo=%s", id_proceso, error.codigo_error, exc_info=True)
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en compras: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado durante el procesamiento de compras.",
            accion_sugerida="Reintente la operacion y contacte soporte si el problema persiste.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="compras",
            estado="ERROR",
            entradas={"ruta_compras": ruta_compras},
            parametros={"dolar": dolar},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en compras. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error
