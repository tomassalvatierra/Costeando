import pandas as pd
import logging
from typing import Dict
import os
from datetime import datetime

from costeando.utilidades.auditoria import guardar_manifiesto_ejecucion
from costeando.utilidades.errores_aplicacion import (
    ErrorAplicacion,
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
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
from costeando.utilidades.configuracion_logging import configurar_logging

configurar_logging()
logger = logging.getLogger(__name__)


def _validar_parametros_listado_general(campania: str, anio: str, carpeta_guardado: str):
    if not campania or not anio:
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan campania o anio para Listado General.",
            codigo_error="CST-NEG-030",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania o anio para ejecutar Listado General.",
            accion_sugerida="Complete campania y anio antes de ejecutar.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico carpeta de guardado en Listado General.",
            codigo_error="CST-NEG-031",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio carpeta de salida para Listado General.",
            accion_sugerida="Seleccione una carpeta valida de salida.",
        )
    campania_normalizada = normalizar_campania(campania, "Listado General", "CST-NEG-030")
    anio_normalizado = validar_anio(anio, "Listado General", "CST-NEG-030")
    return campania_normalizada, anio_normalizado


def _validar_archivos_entrada_listado_general(entradas: list[tuple[str, str]]):
    for ruta_archivo, nombre_archivo in entradas:
        logger.debug("Validando archivo: %s (%s)", nombre_archivo, ruta_archivo)
        validar_archivo_excel(ruta_archivo, nombre_archivo)


def _cargar_dataframes_listado_general(
    ruta_produciendo: str,
    ruta_comprando: str,
    ruta_costo_primo: str,
    ruta_base_descuentos: str,
    ruta_listado: str,
    ruta_mdo: str,
    ruta_leader_list: str,
    ruta_compilado_fechas_ult_compra: str,
):
    try:
        logger.info("Leyendo archivos Excel de entrada...")
        return (
            pd.read_excel(ruta_produciendo, engine="openpyxl"),
            pd.read_excel(ruta_comprando, engine="openpyxl"),
            pd.read_excel(ruta_costo_primo, engine="openpyxl"),
            pd.read_excel(ruta_base_descuentos, engine="openpyxl"),
            pd.read_excel(ruta_listado, engine="openpyxl"),
            pd.read_excel(ruta_mdo, engine="openpyxl", skiprows=1),
            pd.read_excel(ruta_leader_list, engine="openpyxl"),
            pd.read_excel(ruta_compilado_fechas_ult_compra, engine="openpyxl"),
        )
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Listado General: {error}",
            codigo_error="CST-IO-003",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise que los archivos no esten abiertos y tengan formato valido.",
        ) from error


def _estandarizar_dataframes_listado_general(
    df_produciendo: pd.DataFrame,
    df_comprando: pd.DataFrame,
    df_costo_primo: pd.DataFrame,
    df_base_descuentos: pd.DataFrame,
    df_listado: pd.DataFrame,
    df_mdo: pd.DataFrame,
    df_leader_list: pd.DataFrame,
    df_compilado_fechas_ult_compra: pd.DataFrame,
):
    lista_df = [
        (df_produciendo, "produciendo"),
        (df_costo_primo, "costo_primo"),
        (df_base_descuentos, "base_descuentos"),
        (df_listado, "listado"),
        (df_comprando, "comprando"),
        (df_mdo, "mdo"),
        (df_leader_list, "leader_list"),
        (df_compilado_fechas_ult_compra, "compilado_fechas_ult_compra"),
    ]
    lista_df = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_df]
    return tuple(lista_df)


def _validar_columnas_minimas_listado_general(
    df_produciendo: pd.DataFrame,
    df_comprando: pd.DataFrame,
    df_costo_primo: pd.DataFrame,
    df_base_descuentos: pd.DataFrame,
    df_listado: pd.DataFrame,
    df_mdo: pd.DataFrame,
    df_leader_list: pd.DataFrame,
    df_compilado_fechas_ult_compra: pd.DataFrame,
    campania: str,
    anio: str,
):
    campos_costos = [
        "Costo sin Descuento C" + campania,
        "% de obsolescencia",
        "ROYALTY",
        "DESCUENTO ESPECIAL",
        "APLICA DDE CA:",
    ]
    validar_columnas(df_produciendo, ["Codigo", "Costo Producción"] + campos_costos, "produciendo")
    validar_columnas(df_comprando, ["Codigo"] + campos_costos, "comprando")
    validar_columnas(df_costo_primo, ["Codigo", "Costo Estand"], "costo_primo")
    validar_columnas(df_base_descuentos, ["Codigo", "TIPO-DESCUENTO"], "base_descuentos")
    validar_columnas(df_mdo, ["Codigo", "Componente", "Cantidad"], "mdo")
    validar_columnas(df_leader_list, ["Codigo", "TIPO_OF", "LEYEOFE"], "leader_list")
    validar_columnas(df_compilado_fechas_ult_compra, ["Codigo", "Tipo Orden"], "compilado_fechas_ult_compra")
    if "Costo Estandard" not in df_listado.columns and ("COSTO LISTA " + anio[-1] + campania) not in df_listado.columns:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"El listado no tiene Costo Estandard ni COSTO LISTA {anio[-1]}{campania}.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario="El listado no contiene columna de costo lista esperada.",
            accion_sugerida="Revise encabezados de listado y vuelva a intentar.",
        )
    validar_columnas(df_listado, ["Codigo", "Stock Actual"], "listado")


def procesar_listado_gral_puro(
    ruta_produciendo: str,
    ruta_comprando: str,
    ruta_costo_primo: str,
    ruta_base_descuentos: str,
    ruta_listado: str,
    ruta_mdo: str,
    ruta_leader_list: str,
    ruta_compilado_fechas_ult_compra: str,
    campania: str,
    anio: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Listado General. ID=%s", id_proceso)
        campania, anio = _validar_parametros_listado_general(campania, anio, carpeta_guardado)
        entradas = [
            (ruta_produciendo, "produciendo"),
            (ruta_comprando, "comprando"),
            (ruta_costo_primo, "costo_primo"),
            (ruta_base_descuentos, "base_descuentos"),
            (ruta_listado, "listado"),
            (ruta_mdo, "mdo"),
            (ruta_leader_list, "leader_list"),
            (ruta_compilado_fechas_ult_compra, "compilado_fechas_ult_compra"),
        ]
        _validar_archivos_entrada_listado_general(entradas)
        (
            df_produciendo,
            df_comprando,
            df_costo_primo,
            df_base_descuentos,
            df_listado,
            df_mdo,
            df_leader_list,
            df_compilado_fechas_ult_compra,
        ) = _cargar_dataframes_listado_general(
            ruta_produciendo,
            ruta_comprando,
            ruta_costo_primo,
            ruta_base_descuentos,
            ruta_listado,
            ruta_mdo,
            ruta_leader_list,
            ruta_compilado_fechas_ult_compra,
        )
        (
            df_produciendo,
            df_costo_primo,
            df_base_descuentos,
            df_listado,
            df_comprando,
            df_mdo,
            df_leader_list,
            df_compilado_fechas_ult_compra,
        ) = _estandarizar_dataframes_listado_general(
            df_produciendo,
            df_comprando,
            df_costo_primo,
            df_base_descuentos,
            df_listado,
            df_mdo,
            df_leader_list,
            df_compilado_fechas_ult_compra,
        )
        _validar_columnas_minimas_listado_general(
            df_produciendo,
            df_comprando,
            df_costo_primo,
            df_base_descuentos,
            df_listado,
            df_mdo,
            df_leader_list,
            df_compilado_fechas_ult_compra,
            campania,
            anio,
        )

        df_listado_general = df_listado.copy()

        if "Costo Estandard" in df_listado_general.columns:
            logger.debug("Renombrando columna 'Costo Estandard' a 'COSTO LISTA ...'")
            df_listado_general.rename(
                columns={"Costo Estandard": "COSTO LISTA " + anio[-1] + campania}, inplace=True
            )
        else:
            if "COSTO LISTA " + anio[-1] + campania not in df_listado_general.columns:
                error_msg = (
                    f"Ninguna de las columnas 'Costo Estandard' o "
                    f"'COSTO LISTA {anio[-1]}{campania}' existe en el listado."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

        df_mdo_806 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0806"])]
        df_mdo_807 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0807"])]
        df_mdo_808 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0808"])]

        logger.debug("Realizando merges de MANO DE OBRA TOTAL")
        df_listado_general = pd.merge(
            df_listado_general, df_costo_primo[["Codigo", "Costo Estand"]], how="left", on="Codigo"
        )
        df_listado_general.rename(columns={"Costo Estand": "COSTO PRIMO (MATERIALES)"}, inplace=True)

        for df_mdo_x, col_nombre in [
            (df_mdo_806, "MOD 0806 SEGUNDOS MO ELAB. X KILO"),
            (df_mdo_807, "MOD 0807 SEGUNDOS MO ENV. X UNIDAD"),
            (df_mdo_808, "MOD 0808 SEGUNDOS MO ACOND.X UNIDAD"),
        ]:
            df_listado_general = pd.merge(
                df_listado_general, df_mdo_x[["Codigo", "Cantidad"]], how="left", on="Codigo"
            )
            df_listado_general.rename(columns={"Cantidad": col_nombre}, inplace=True)

        df_listado_general = pd.merge(
            df_listado_general,
            df_compilado_fechas_ult_compra[["Codigo", "Tipo Orden"]],
            how="left", on="Codigo"
        )
        df_listado_general.rename(columns={"Tipo Orden": "TIPO ULT COMPRA"}, inplace=True)

        logger.debug("Realizando merge costo de Produccion y CARGA FABRIL")
        df_listado_general = pd.merge(
            df_listado_general, df_produciendo[["Codigo", "Costo Producción"]], how="left", on="Codigo"
        )

        cols = [
            "Codigo", "Costo sin Descuento C" + campania,
            "% de obsolescencia", "ROYALTY", "DESCUENTO ESPECIAL", "APLICA DDE CA:",
        ]
        df_aux = pd.merge(
            df_produciendo[cols], df_comprando[cols],
            on="Codigo", how="outer", suffixes=('_prod', '_comp')
        )
        for campo in cols[1:]:
            df_aux[campo] = df_aux[campo + '_prod'].combine_first(df_aux[campo + '_comp'])
        df_aux = df_aux[["Codigo"] + cols[1:]]
        df_listado_general = pd.merge(df_listado_general, df_aux, how="left", on="Codigo")

        df_listado_general = pd.merge(
            df_listado_general, df_base_descuentos[["Codigo", "TIPO-DESCUENTO"]], how="left", on="Codigo"
        )
        df_listado_general.loc[
            df_listado_general["DESCUENTO ESPECIAL"].fillna(0) == 0, "TIPO-DESCUENTO"
        ] = None

        logger.debug("Realizando merges con el leader list")
        df_listado_general = pd.merge(
            df_listado_general, df_leader_list[["Codigo", "TIPO_OF"]], how="left", on="Codigo"
        )
        df_listado_general = pd.merge(
            df_listado_general, df_leader_list[["Codigo", "LEYEOFE"]], how="left", on="Codigo"
        )
        df_listado_general.drop_duplicates(subset=["Codigo"], keep="first", inplace=True)

        for col in ["DESCUENTO ESPECIAL", "ROYALTY", "% de obsolescencia"]:
            df_listado_general[col] = pd.to_numeric(df_listado_general[col], errors='coerce')

        logger.debug("Sumatoria de descuentos")
        df_listado_general["% Sumatoria de Descuentos"] = (
            df_listado_general["DESCUENTO ESPECIAL"].fillna(0) +
            df_listado_general["ROYALTY"].fillna(0) +
            df_listado_general["% de obsolescencia"].fillna(0)
        ).round(2)

        logger.debug("Inicia fase de calculos")
        df_listado_general["MANO DE OBRA TOTAL"] = (
            df_listado_general["Costo Producción"] - df_listado_general["COSTO PRIMO (MATERIALES)"]
        ).round(2)
        df_listado_general["Costo sin Descuento C" + campania] = (
            df_listado_general["COSTO LISTA " + anio[-1] + campania] /
            ((100 - df_listado_general["% Sumatoria de Descuentos"]) / 100)
        ).round(2)
        df_listado_general["CARGA FABRIL"] = (
            df_listado_general["Costo sin Descuento C" + campania] -
            df_listado_general["Costo Producción"]
        ).round(1)
        df_listado_general["DESCUENTO APLICADO $"] = (
            df_listado_general["COSTO LISTA " + anio[-1] + campania] -
            df_listado_general["Costo sin Descuento C" + campania]
        ).round(2)
        df_listado_general["VALOR STOCK CON DESCUENTO"] = (
            df_listado_general["Stock Actual"] *
            df_listado_general["COSTO LISTA " + anio[-1] + campania]
        ).round(2)
        logger.info("Termina fase de calculos")

        df_listado_general.loc[
            df_listado_general["COSTO LISTA " + anio[-1] + campania] == 0,
            ["COSTO PRIMO (MATERIALES)", "MANO DE OBRA TOTAL", "Costo Producción", "CARGA FABRIL"]
        ] = 0

        df_listado_general["MANO DE OBRA TOTAL"] = df_listado_general["MANO DE OBRA TOTAL"].fillna(0)
        df_listado_general["CARGA FABRIL"] = df_listado_general["CARGA FABRIL"].fillna(0)
        df_listado_general["COD MADRE"] = ""
        df_listado_general["COD COMB"] = ""

        columnas_ordenadas = [
            "Periodo", "Codigo", "COD MADRE", "COD COMB", "Descripcion",
            "COSTO PRIMO (MATERIALES)", "MANO DE OBRA TOTAL", "Costo Producción",
            "CARGA FABRIL", "Costo sin Descuento C" + campania,
            "% Sumatoria de Descuentos", "COSTO LISTA " + anio[-1] + campania,
            "TIPO DE COSTO", "ADI NÂ°", "Ult. Compra", "TIPO ULT COMPRA",
            "MOD 0806 SEGUNDOS MO ELAB. X KILO", "MOD 0807 SEGUNDOS MO ENV. X UNIDAD",
            "MOD 0808 SEGUNDOS MO ACOND.X UNIDAD",
            "% de obsolescencia", "ROYALTY", "DESCUENTO ESPECIAL", "APLICA DDE CA:",
            "TIPO-DESCUENTO", "DESCUENTO APLICADO $", "Stock Actual",
            "VALOR STOCK CON DESCUENTO", "TIPO_OF", "LEYEOFE", "Estado",
            "Cod Actualiz", "VARIABLE", "LLEVA CF", "Tipo", "Desc.Tipo",
            "Grupo", "Desc. Grupo", "Sub Grupo", "Desc.Sub Grupo",
            "Entra MRP", "Atiende Necsdd", "Prov", "Ult P/C",
            "Razon Social", "Fecha Alta",
        ]
        columnas_existentes = [col for col in columnas_ordenadas if col in df_listado_general.columns]
        df_listado_general = df_listado_general.reindex(columns=columnas_existentes)

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        path_listado = os.path.join(
            carpeta_guardado,
            f"{fecha_hoy} Listado General Completo C{campania}-{anio}.xlsx"
        )
        if not os.path.exists(carpeta_guardado):
            os.makedirs(carpeta_guardado)
        logger.info(f"Guardando Listado gral procesado en: {path_listado}")
        df_listado_general.to_excel(path_listado, index=False, engine="openpyxl")

        logger.info(f"Archivos guardados correctamente en: {carpeta_guardado}")
        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="listado_general",
            estado="OK",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_comprando": ruta_comprando,
                "ruta_costo_primo": ruta_costo_primo,
                "ruta_base_descuentos": ruta_base_descuentos,
                "ruta_listado": ruta_listado,
                "ruta_mdo": ruta_mdo,
                "ruta_leader_list": ruta_leader_list,
                "ruta_compilado_fechas_ult_compra": ruta_compilado_fechas_ult_compra,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={"filas_salida": len(df_listado_general)},
            archivos_generados={"Listado_general_completo": path_listado},
        )
        return {
            "Listado_general_completo": path_listado,
            "manifiesto": path_manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="listado_general",
            estado="ERROR",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_comprando": ruta_comprando,
                "ruta_costo_primo": ruta_costo_primo,
                "ruta_base_descuentos": ruta_base_descuentos,
                "ruta_listado": ruta_listado,
                "ruta_mdo": ruta_mdo,
                "ruta_leader_list": ruta_leader_list,
                "ruta_compilado_fechas_ult_compra": ruta_compilado_fechas_ult_compra,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error("Error controlado en Listado General. ID=%s Codigo=%s", id_proceso, error.codigo_error, exc_info=True)
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Listado General: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Listado General.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="listado_general",
            estado="ERROR",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_comprando": ruta_comprando,
                "ruta_costo_primo": ruta_costo_primo,
                "ruta_base_descuentos": ruta_base_descuentos,
                "ruta_listado": ruta_listado,
                "ruta_mdo": ruta_mdo,
                "ruta_leader_list": ruta_leader_list,
                "ruta_compilado_fechas_ult_compra": ruta_compilado_fechas_ult_compra,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Listado General. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error

