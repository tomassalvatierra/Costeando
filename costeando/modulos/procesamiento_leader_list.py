import logging
import os
from datetime import datetime
from typing import Dict

import pandas as pd

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
    validar_archivo_excel,
    validar_columnas,
)

logger = logging.getLogger(__name__)


def asignacion_campanias(campania: str, anio: str) -> tuple[str, str, str]:
    if campania == "01":
        campania_anterior = "18"
        anio_anterior = str(int(anio) - 1)
    else:
        campania_anterior = str(int(campania) - 1).zfill(2)
        anio_anterior = anio
    anio_campania_anterior = anio_anterior[-1] + campania_anterior
    anio_campania_actual = anio[-1] + campania
    return campania_anterior, anio_campania_anterior, anio_campania_actual


def proceso_combinadas(df_combinadas: pd.DataFrame) -> pd.DataFrame:
    df_grouped = (
        df_combinadas.groupby("COMBINADA")["CODIGON"]
        .agg(lambda valores: " - ".join(map(str, valores)))
        .reset_index()
    )
    df_grouped.rename(columns={"CODIGON": "COD COMB", "COMBINADA": "Codigo"}, inplace=True)
    return df_grouped


def _obtener_columna_atiende(df_maestro: pd.DataFrame) -> str:
    for nombre_columna in ["Atiende Ne?", "¿Atiende Ne?", "Atiende Necsdd"]:
        if nombre_columna in df_maestro.columns:
            return nombre_columna
    raise ErrorEsquemaArchivo(
        mensaje_tecnico="No se encontro columna atiende en maestro para Leader List.",
        codigo_error="CST-VAL-001",
        titulo_usuario="Estructura de archivo invalida",
        mensaje_usuario="El archivo maestro no contiene columna de atiende.",
        accion_sugerida="Revise encabezados del maestro y vuelva a intentar.",
    )


def _validar_parametros_leader_list(campania: str, anio: str, carpeta_guardado: str) -> str:
    if not all([campania, anio]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan campania/anio en Leader List.",
            codigo_error="CST-NEG-090",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania o anio para ejecutar Leader List.",
            accion_sugerida="Complete campania y anio antes de ejecutar.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico ruta de salida en Leader List.",
            codigo_error="CST-NEG-091",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta valida para guardar resultados.",
        )
    if not str(campania).isdigit():
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Campania invalida en Leader List: {campania}",
            codigo_error="CST-NEG-092",
            titulo_usuario="Campania invalida",
            mensaje_usuario="La campania informada no es valida.",
            accion_sugerida="Use una campania numerica.",
        )
    if not str(anio).isdigit() or len(str(anio)) != 4:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Anio invalido en Leader List: {anio}",
            codigo_error="CST-NEG-093",
            titulo_usuario="Anio invalido",
            mensaje_usuario="El anio informado no es valido.",
            accion_sugerida="Use un anio con formato AAAA.",
        )
    return str(campania).zfill(2)


def _cargar_dataframes_leader_list(
    ruta_leader_list: str,
    ruta_listado_anterior: str,
    ruta_maestro: str,
    ruta_dobles: str,
    ruta_combinadas: str,
    ruta_stock: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    try:
        df_leader_list = pd.read_excel(ruta_leader_list, engine="openpyxl")
        df_listado_anterior = pd.read_excel(ruta_listado_anterior, engine="openpyxl")
        df_maestro = pd.read_excel(ruta_maestro, engine="openpyxl")
        df_dobles = pd.read_excel(ruta_dobles, engine="openpyxl")
        df_combinadas = pd.read_excel(ruta_combinadas, engine="openpyxl")
        df_stock = pd.read_excel(ruta_stock, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Leader List: {error}",
            codigo_error="CST-IO-009",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_leader_list, df_listado_anterior, df_maestro, df_dobles, df_combinadas, df_stock


def _validar_columnas_minimas_leader_list(
    df_leader_list: pd.DataFrame,
    df_listado_anterior: pd.DataFrame,
    df_maestro: pd.DataFrame,
    df_dobles: pd.DataFrame,
    df_combinadas: pd.DataFrame,
    df_stock: pd.DataFrame,
    anio_campania_anterior: str,
):
    validar_columnas(df_leader_list, ["CODIGON", "UNID_EST"], "leader list")
    if "Codigo" not in df_listado_anterior.columns and "Producto" not in df_listado_anterior.columns:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico="Listado anterior no contiene Codigo ni Producto.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario="El listado anterior no contiene clave de producto.",
            accion_sugerida="Revise encabezado Codigo/Producto en listado anterior.",
        )
    validar_columnas(df_listado_anterior, ["COSTO LISTA " + anio_campania_anterior], "listado anterior")

    if "Codigo" not in df_maestro.columns and "Producto" not in df_maestro.columns:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico="Maestro no contiene Codigo ni Producto.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario="El maestro no contiene clave de producto.",
            accion_sugerida="Revise encabezado Codigo/Producto en maestro.",
        )
    validar_columnas(df_maestro, ["Estado"], "maestro")
    validar_columnas(df_dobles, ["CODIGO_DOB", "CODIGO_ORI"], "dobles")
    validar_columnas(df_combinadas, ["CODIGON", "COMBINADA"], "combinadas")
    if "Codigo" not in df_stock.columns and "Producto" not in df_stock.columns:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico="Stock no contiene Codigo ni Producto.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario="El archivo stock no contiene clave de producto.",
            accion_sugerida="Revise encabezado Codigo/Producto en stock.",
        )
    validar_columnas(df_stock, ["Stock Actual"], "stock")
    _obtener_columna_atiende(df_maestro)


def _normalizar_dataframes_leader_list(
    df_leader_list: pd.DataFrame,
    df_listado_anterior: pd.DataFrame,
    df_maestro: pd.DataFrame,
    df_dobles: pd.DataFrame,
    df_combinadas: pd.DataFrame,
    df_stock: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df_combinadas_agrupadas = proceso_combinadas(df_combinadas.copy())

    df_dobles = df_dobles.rename(columns={"CODIGO_DOB": "Codigo", "CODIGO_ORI": "COD MADRE"})
    df_leader_list = df_leader_list.rename(columns={"CODIGON": "Codigo"})
    df_combinadas = df_combinadas.rename(columns={"CODIGON": "Codigo"})

    lista_dfs = [
        (df_listado_anterior, "Listado de costos n-1"),
        (df_maestro, "Maestro"),
        (df_stock, "Stock"),
        (df_leader_list, "Leader list"),
        (df_dobles, "Dobles"),
        (df_combinadas_agrupadas, "Combinadas agrupadas"),
        (df_combinadas, "Combinadas"),
    ]
    lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
    (
        df_listado_anterior,
        df_maestro,
        df_stock,
        df_leader_list,
        df_dobles,
        df_combinadas_agrupadas,
        df_combinadas,
    ) = lista_dfs
    return (
        df_leader_list,
        df_listado_anterior,
        df_maestro,
        df_dobles,
        df_combinadas,
        df_stock,
        df_combinadas_agrupadas,
    )


def _procesar_leader_list(
    df_leader_list: pd.DataFrame,
    df_listado_anterior: pd.DataFrame,
    df_maestro: pd.DataFrame,
    df_dobles: pd.DataFrame,
    df_combinadas_agrupadas: pd.DataFrame,
    df_stock: pd.DataFrame,
    campania: str,
    campania_anterior: str,
    anio_campania: str,
    anio_campania_anterior: str,
) -> pd.DataFrame:
    columna_atiende = _obtener_columna_atiende(df_maestro)
    df_leader_list = df_leader_list.query("Codigo not in [99000, 99001, 99002, 99003, 99004, 99005]")

    columnas_iniciales = [
        "COSTO LISTA " + anio_campania,
        "TIPO COSTO",
        "%VAR C" + campania + " VS C" + campania_anterior,
        "VAR C" + campania + " VS CESTIM",
        "OBSERVACIONES",
    ]
    nuevas_columnas = {columna: [None] * len(df_leader_list) for columna in columnas_iniciales}
    df_leader_list = df_leader_list.assign(**nuevas_columnas)

    df_leader_list = pd.merge(
        df_leader_list,
        df_listado_anterior[["Codigo", "COSTO LISTA " + anio_campania_anterior]],
        how="left",
        on="Codigo",
    )

    if {"DESCUENTO ESPECIAL", "APLICA DDE CA:", "TIPO-DESCUENTO"}.issubset(df_listado_anterior.columns):
        df_leader_list = pd.merge(
            df_leader_list,
            df_listado_anterior[["Codigo", "DESCUENTO ESPECIAL", "APLICA DDE CA:", "TIPO-DESCUENTO"]],
            how="left",
            on="Codigo",
        )
        df_leader_list = df_leader_list.rename(
            columns={
                "DESCUENTO ESPECIAL": "DESCUENTO ESPECIAL (N-1)",
                "TIPO-DESCUENTO": "TIPO-DESCUENTO (N-1)",
            }
        )

    df_leader_list = pd.merge(
        df_leader_list,
        df_maestro[["Codigo", columna_atiende, "Estado"]],
        how="left",
        on="Codigo",
    )
    df_leader_list = pd.merge(df_leader_list, df_dobles[["Codigo", "COD MADRE"]], how="left", on="Codigo")
    df_leader_list = pd.merge(
        df_leader_list,
        df_combinadas_agrupadas[["Codigo", "COD COMB"]],
        how="left",
        on="Codigo",
    )
    df_leader_list = df_leader_list.rename(columns={"Estado": "ESTADO TOTVS", columna_atiende: "Atiende Ne?"})
    df_leader_list = pd.merge(df_leader_list, df_stock[["Codigo", "Stock Actual"]], how="left", on="Codigo")

    df_leader_list["UNIDADES REALES ESTIMADAS"] = pd.to_numeric(df_leader_list["UNID_EST"], errors="coerce") * 2
    df_leader_list["STOCK VS UNID_TOTALES ESTIM"] = (
        pd.to_numeric(df_leader_list["Stock Actual"], errors="coerce")
        - pd.to_numeric(df_leader_list["UNIDADES REALES ESTIMADAS"], errors="coerce")
    )

    df_leader_list.loc[df_leader_list["COD MADRE"].notna(), "TIPO COSTO"] = "CODIGO DOBLE"
    df_leader_list.loc[df_leader_list["COD COMB"].notna(), "TIPO COSTO"] = "CODIGO COMBINADA"
    df_leader_list = df_leader_list.drop_duplicates(subset="Codigo", keep="first")
    return df_leader_list


def _ordenar_columnas_salida(
    df_leader_list: pd.DataFrame,
    campania: str,
    campania_anterior: str,
    anio_campania: str,
    anio_campania_anterior: str,
) -> pd.DataFrame:
    columnas_finales = [
        "CAMP",
        "ANO",
        "Codigo",
        "COD MADRE",
        "COD COMB",
        "DESCRIP",
        "COSTO LISTA " + anio_campania,
        "TIPO COSTO",
        "Atiende Ne?",
        "DIVISION",
        "UXP",
        "TIPO_OF",
        "LEYEOFE",
        "PR_OFERTA",
        "PR_NORMAL",
        "MAR_EST",
        "COSTO_EST",
        "TIPO_EST",
        "FACT_EST",
        "PAGINA",
        "CATEGORIA",
        "LEYENDA",
        "SEGMENTO",
        "LEY_SEG",
        "SUB_LINEA",
        "LEYESUBL",
        "LINEA",
        "LEY_LIN",
        "PROC",
        "LEYEPRO",
        "UNID_EST",
        "CONSIG",
        "CABECERA",
        "COEFICIE",
        "EMPRESA",
        "ESTADO",
        "CMP_ESTA",
        "CUOTAS",
        "OM_EST",
        "PED_EST",
        "COS_ESTOT",
        "COSTO LISTA " + anio_campania_anterior,
        "%VAR C" + campania + " VS C" + campania_anterior,
        "VAR C" + campania + " VS CESTIM",
        "OBSERVACIONES",
        "DESCUENTO ESPECIAL (N-1)",
        "TIPO-DESCUENTO (N-1)",
        "APLICA DDE CA:",
        "ESTADO TOTVS",
        "Stock Actual",
        "UNIDADES REALES ESTIMADAS",
        "STOCK VS UNID_TOTALES ESTIM",
    ]
    return df_leader_list.reindex(columns=columnas_finales)


def _exportar_resultados_leader_list(
    df_leader_list: pd.DataFrame,
    df_combinadas_agrupadas: pd.DataFrame,
    campania: str,
    anio: str,
    carpeta_guardado: str,
) -> Dict[str, str]:
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_leader_list = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Leader List procesado C{campania}-{anio}.xlsx",
    )
    path_combinadas_agrupadas = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Combinadas agrupadas C{campania}-{anio}.xlsx",
    )
    df_leader_list.to_excel(path_leader_list, index=False, engine="openpyxl")
    df_combinadas_agrupadas.to_excel(path_combinadas_agrupadas, index=False, engine="openpyxl")
    return {
        "leader_list": path_leader_list,
        "combinadas_agrupadas": path_combinadas_agrupadas,
    }


def procesar_leader_list_puro(
    ruta_leader_list: str,
    ruta_listado_anterior: str,
    ruta_maestro: str,
    ruta_dobles: str,
    ruta_combinadas: str,
    ruta_stock: str,
    campana: str,
    anio: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Leader List. ID=%s", id_proceso)
        validar_archivo_excel(ruta_leader_list, "leader list")
        validar_archivo_excel(ruta_listado_anterior, "listado anterior")
        validar_archivo_excel(ruta_maestro, "maestro")
        validar_archivo_excel(ruta_dobles, "dobles")
        validar_archivo_excel(ruta_combinadas, "combinadas")
        validar_archivo_excel(ruta_stock, "stock")

        campania = _validar_parametros_leader_list(campana, anio, carpeta_guardado)
        campania_anterior, anio_campania_anterior, anio_campania = asignacion_campanias(campania, anio)

        (
            df_leader_list,
            df_listado_anterior,
            df_maestro,
            df_dobles,
            df_combinadas,
            df_stock,
        ) = _cargar_dataframes_leader_list(
            ruta_leader_list,
            ruta_listado_anterior,
            ruta_maestro,
            ruta_dobles,
            ruta_combinadas,
            ruta_stock,
        )
        _validar_columnas_minimas_leader_list(
            df_leader_list,
            df_listado_anterior,
            df_maestro,
            df_dobles,
            df_combinadas,
            df_stock,
            anio_campania_anterior,
        )

        (
            df_leader_list,
            df_listado_anterior,
            df_maestro,
            df_dobles,
            _df_combinadas,
            df_stock,
            df_combinadas_agrupadas,
        ) = _normalizar_dataframes_leader_list(
            df_leader_list,
            df_listado_anterior,
            df_maestro,
            df_dobles,
            df_combinadas,
            df_stock,
        )

        df_leader_list = _procesar_leader_list(
            df_leader_list,
            df_listado_anterior,
            df_maestro,
            df_dobles,
            df_combinadas_agrupadas,
            df_stock,
            campania,
            campania_anterior,
            anio_campania,
            anio_campania_anterior,
        )
        df_leader_list = _ordenar_columnas_salida(
            df_leader_list,
            campania,
            campania_anterior,
            anio_campania,
            anio_campania_anterior,
        )

        salidas = _exportar_resultados_leader_list(
            df_leader_list,
            df_combinadas_agrupadas,
            campania,
            anio,
            carpeta_guardado,
        )
        logger.info("Leader List finalizado. Archivos en: %s", carpeta_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="leader_list",
            estado="OK",
            entradas={
                "ruta_leader_list": ruta_leader_list,
                "ruta_listado_anterior": ruta_listado_anterior,
                "ruta_maestro": ruta_maestro,
                "ruta_dobles": ruta_dobles,
                "ruta_combinadas": ruta_combinadas,
                "ruta_stock": ruta_stock,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={
                "filas_leader_list": len(df_leader_list),
                "filas_combinadas_agrupadas": len(df_combinadas_agrupadas),
            },
            archivos_generados=salidas,
        )
        return {**salidas, "manifiesto": path_manifiesto, "id_ejecucion": id_proceso}
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="leader_list",
            estado="ERROR",
            entradas={
                "ruta_leader_list": ruta_leader_list,
                "ruta_listado_anterior": ruta_listado_anterior,
                "ruta_maestro": ruta_maestro,
                "ruta_dobles": ruta_dobles,
                "ruta_combinadas": ruta_combinadas,
                "ruta_stock": ruta_stock,
            },
            parametros={"campania": campana, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Leader List. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Leader List: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Leader List.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="leader_list",
            estado="ERROR",
            entradas={
                "ruta_leader_list": ruta_leader_list,
                "ruta_listado_anterior": ruta_listado_anterior,
                "ruta_maestro": ruta_maestro,
                "ruta_dobles": ruta_dobles,
                "ruta_combinadas": ruta_combinadas,
                "ruta_stock": ruta_stock,
            },
            parametros={"campania": campana, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Leader List. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error

