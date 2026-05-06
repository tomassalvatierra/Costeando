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
    validar_rango_fechas,
)

logger = logging.getLogger(__name__)


def _obtener_columna_atiende(df_productos: pd.DataFrame) -> str:
    for nombre_columna in ["Atiende Ne?", "¿Atiende Ne?", "Atiende Necsdd"]:
        if nombre_columna in df_productos.columns:
            return nombre_columna
    raise ErrorEsquemaArchivo(
        mensaje_tecnico="No se encontro columna de atiende en segundo produciendo.",
        codigo_error="CST-VAL-001",
        titulo_usuario="Estructura de archivo invalida",
        mensaje_usuario="El archivo produciendo no tiene columna de atiende.",
        accion_sugerida="Revise encabezados del archivo produciendo.",
    )


def incorporar_nuevos_dtos(
    df_especiales: pd.DataFrame,
    df_importador: pd.DataFrame,
    df_productos: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    nuevos_codigos = df_importador["Codigo"].tolist()
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "VENCIDO"] = "Si"
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "NOTAS"] = "Vencido, ingreso un nuevo descuento"

    descuentos_por_codigo = dict(
        zip(
            df_importador["Codigo"],
            zip(df_importador["DESCUENTO ESPECIAL"], df_importador["APLICA DDE CA:"]),
        )
    )
    valores_mapeados = df_productos["Codigo"].map(descuentos_por_codigo).apply(
        lambda valor: valor if isinstance(valor, tuple) else (None, None)
    )
    nuevos_valores = valores_mapeados.apply(pd.Series)
    nuevos_valores.columns = ["DESCUENTO ESPECIAL", "APLICA DDE CA:"]
    nuevos_valores = nuevos_valores.set_index(df_productos.index)

    df_productos[["DESCUENTO ESPECIAL", "APLICA DDE CA:"]] = df_productos[
        ["DESCUENTO ESPECIAL", "APLICA DDE CA:"]
    ].combine_first(nuevos_valores)

    return pd.concat([df_especiales, df_importador], ignore_index=True), df_productos


def crear_importador(
    df_produciendo: pd.DataFrame,
    anio_campania: str,
    fecha_compras_inicio: pd.Timestamp,
    fecha_compras_final: pd.Timestamp,
    campania_anio: str,
) -> pd.DataFrame:
    df_importador = df_produciendo[["Codigo", "Costo 2do Importador"]].copy()
    df_importador["Columna3"] = "27251293061"
    df_importador["Columna4"] = anio_campania
    df_importador["Columna5"] = campania_anio
    df_importador["Columna6"] = fecha_compras_inicio
    df_importador["Columna7"] = fecha_compras_final
    df_importador["Columna8"] = "001"
    df_importador["Columna9"] = "001"
    df_importador["Columna10"] = "99999999"
    df_importador["Columna11"] = "31/12/1999"
    df_importador["Costo 2do Importador"] = df_importador["Costo 2do Importador"].round(2).astype(str)
    return df_importador.reset_index(drop=True)


def _validar_parametros_segundo_produciendo(
    campania: str,
    anio: str,
    fecha_compras_inicio: str,
    fecha_compras_final: str,
    carpeta_guardado: str,
) -> tuple[pd.Timestamp, pd.Timestamp, str, str]:
    if not all([campania, anio, fecha_compras_inicio, fecha_compras_final]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan parametros obligatorios en Segundo Produciendo.",
            codigo_error="CST-NEG-050",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania, anio o fechas para ejecutar.",
            accion_sugerida="Complete campania, anio y fechas de compra.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico carpeta de salida en Segundo Produciendo.",
            codigo_error="CST-NEG-051",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio carpeta de salida.",
            accion_sugerida="Seleccione una carpeta valida para guardar resultados.",
        )
    anio_normalizado = validar_anio(anio, "Segundo Produciendo", "CST-NEG-052")
    campania_normalizada = normalizar_campania(campania, "Segundo Produciendo", "CST-NEG-053")
    fecha_inicio, fecha_final = validar_rango_fechas(
        fecha_compras_inicio,
        fecha_compras_final,
        "Segundo Produciendo",
        "CST-NEG-054",
        "CST-NEG-055",
    )
    return fecha_inicio, fecha_final, campania_normalizada, anio_normalizado


def _cargar_dataframes_segundo_produciendo(
    ruta_produciendo: str,
    ruta_base_especiales: str,
    ruta_importador_descuentos: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    try:
        df_produciendo = pd.read_excel(ruta_produciendo, engine="openpyxl")
        df_base_especiales = pd.read_excel(ruta_base_especiales, engine="openpyxl")
        df_importador_descuentos = None
        if ruta_importador_descuentos:
            df_importador_descuentos = pd.read_excel(ruta_importador_descuentos, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Segundo Produciendo: {error}",
            codigo_error="CST-IO-004",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_produciendo, df_base_especiales, df_importador_descuentos


def _validar_columnas_minimas_segundo_produciendo(
    df_produciendo: pd.DataFrame,
    df_base_especiales: pd.DataFrame,
    campania: str,
    df_importador_descuentos: pd.DataFrame | None,
) -> tuple[str, str]:
    columna_atiende = _obtener_columna_atiende(df_produciendo)
    columna_costo = f"Costo sin Descuento C{campania}"
    validar_columnas(
        df_produciendo,
        [
            "Codigo",
            "Descripcion",
            columna_atiende,
            "% de obsolescencia",
            "DESCUENTO ESPECIAL",
            "ROYALTY",
            "APLICA DDE CA:",
            columna_costo,
        ],
        "produciendo",
    )
    validar_columnas(
        df_base_especiales,
        ["Codigo", "DESCUENTO ESPECIAL", "APLICA DDE CA:", "VENCIDO", "TIPO-DESCUENTO"],
        "base descuentos",
    )
    if df_importador_descuentos is not None:
        validar_columnas(
            df_importador_descuentos,
            ["Codigo", "DESCUENTO ESPECIAL", "APLICA DDE CA:"],
            "importador descuentos",
        )
    return columna_atiende, columna_costo


def _aplicar_descuentos_y_base_especiales(
    df_produciendo: pd.DataFrame,
    df_base_especiales: pd.DataFrame,
    columna_atiende: str,
    desde_desc_especiales: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_produciendo = df_produciendo.sort_values(by=["Codigo", "APLICA DDE CA:"], ascending=[True, False])
    df_produciendo = df_produciendo.drop_duplicates(subset=["Codigo"], keep="first").reset_index(drop=True)

    df_produciendo["% sumatoria descuentos"] = (
        df_produciendo["% de obsolescencia"].fillna(0)
        + df_produciendo["DESCUENTO ESPECIAL"].fillna(0)
        + df_produciendo["ROYALTY"].fillna(0)
    ).round(2)

    mascara_superado_75 = df_produciendo["% sumatoria descuentos"] > 75
    exceso = df_produciendo.loc[mascara_superado_75, "% sumatoria descuentos"] - 75
    df_produciendo.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] = (
        df_produciendo.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] - exceso
    ).clip(lower=0)

    codigos_ajustados = df_produciendo.loc[mascara_superado_75, "Codigo"].unique()
    df_base_especiales.loc[df_base_especiales["Codigo"].isin(codigos_ajustados), "VENCIDO"] = "Si"

    nuevos_descuentos = df_produciendo.loc[mascara_superado_75, ["Codigo", "DESCUENTO ESPECIAL"]].copy()
    nuevos_descuentos["APLICA DDE CA:"] = desde_desc_especiales
    nuevos_descuentos["VENCIDO"] = "No"
    nuevos_descuentos["NOTAS"] = "Descuento ajustado porque superaba 75%"
    nuevos_descuentos = pd.merge(nuevos_descuentos, df_produciendo[["Codigo", "Descripcion"]], how="left")
    nuevos_descuentos = pd.merge(nuevos_descuentos, df_produciendo[["Codigo", columna_atiende]], how="left")
    nuevos_descuentos = pd.merge(nuevos_descuentos, df_base_especiales[["Codigo", "TIPO-DESCUENTO"]], how="left")
    nuevos_descuentos = nuevos_descuentos.rename(columns={columna_atiende: "ATIENDE NE?"})
    nuevos_descuentos = nuevos_descuentos.drop_duplicates()

    df_base_especiales = pd.concat([df_base_especiales, nuevos_descuentos], ignore_index=True)
    df_produciendo["% sumatoria descuentos"] = (
        df_produciendo["% de obsolescencia"].fillna(0)
        + df_produciendo["DESCUENTO ESPECIAL"].fillna(0)
        + df_produciendo["ROYALTY"].fillna(0)
    ).round(2)
    df_produciendo.loc[df_produciendo["DESCUENTO ESPECIAL"] == 0, "APLICA DDE CA:"] = np.nan

    df_base_especiales["DESCUENTO ESPECIAL"] = df_base_especiales["DESCUENTO ESPECIAL"].round(2)
    df_produciendo["DESCUENTO ESPECIAL"] = df_produciendo["DESCUENTO ESPECIAL"].round(2)
    return df_produciendo, df_base_especiales


def _calcular_costo_importador(
    df_produciendo: pd.DataFrame,
    columna_costo_sin_descuento: str,
) -> pd.DataFrame:
    costo_importador = round(
        df_produciendo[columna_costo_sin_descuento] * (1 - (df_produciendo["% sumatoria descuentos"] / 100)),
        2,
    )
    df_produciendo = df_produciendo.assign(costo_p_importador=costo_importador.values)
    df_produciendo = df_produciendo.rename(columns={"costo_p_importador": "Costo 2do Importador"})
    df_produciendo["Costo 2do Importador"] = df_produciendo["Costo 2do Importador"].fillna(0)
    if "COMPONENTE FALTANTE" in df_produciendo.columns:
        df_produciendo.loc[df_produciendo["COMPONENTE FALTANTE"].notna(), "Costo 2do Importador"] = 0
    return df_produciendo


def _exportar_archivos_segundo_produciendo(
    df_importador: pd.DataFrame,
    df_produciendo: pd.DataFrame,
    df_base_especiales: pd.DataFrame,
    campania: str,
    anio: str,
    carpeta_guardado: str,
) -> Dict[str, str]:
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_importador = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Importador Produciendo C{campania}-{anio}.xlsx",
    )
    path_produciendo = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Calculo Produciendo-Segunda etapa C{campania}-{anio}.xlsx",
    )
    path_especiales = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} BASE DTOS-Segunda etapa produciendo C{campania}-{anio}.xlsx",
    )

    df_importador.to_excel(path_importador, sheet_name="Importador", index=False, engine="openpyxl")
    df_produciendo.to_excel(path_produciendo, sheet_name="Calculo Produciendo 2da", index=False, engine="openpyxl")
    df_base_especiales.to_excel(path_especiales, sheet_name="Base 2do Produciendo", index=False, engine="openpyxl")
    return {"importador": path_importador, "produciendo": path_produciendo, "especiales": path_especiales}


def procesar_segundo_produciendo(
    ruta_produciendo: str,
    ruta_base_especiales: str,
    ruta_importador_descuentos: str | None,
    campania: str,
    anio: str,
    fecha_compras_inicio: str,
    fecha_compras_final: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Segundo Produciendo. ID=%s", id_proceso)
        validar_archivo_excel(ruta_produciendo, "produciendo")
        validar_archivo_excel(ruta_base_especiales, "base descuentos")
        if ruta_importador_descuentos:
            validar_archivo_excel(ruta_importador_descuentos, "importador descuentos")

        fecha_inicio, fecha_final, campania_normalizada, anio = _validar_parametros_segundo_produciendo(
            campania,
            anio,
            fecha_compras_inicio,
            fecha_compras_final,
            carpeta_guardado,
        )
        anio_campania = anio[-1] + campania_normalizada
        campania_anio = f"CAMP-{campania_normalizada}/{str(int(anio) % 100)}"
        desde_desc_especiales = f"{anio}/{campania_normalizada}"

        df_produciendo, df_base_especiales, df_importador_descuentos = _cargar_dataframes_segundo_produciendo(
            ruta_produciendo,
            ruta_base_especiales,
            ruta_importador_descuentos,
        )

        if df_importador_descuentos is not None:
            lista_dfs = [
                (df_produciendo, "produciendo"),
                (df_base_especiales, "base descuentos"),
                (df_importador_descuentos, "importador"),
            ]
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
            df_produciendo, df_base_especiales, df_importador_descuentos = lista_dfs
        else:
            lista_dfs = [(df_produciendo, "produciendo"), (df_base_especiales, "base descuentos")]
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
            df_produciendo, df_base_especiales = lista_dfs

        columna_atiende, columna_costo_sin_descuento = _validar_columnas_minimas_segundo_produciendo(
            df_produciendo,
            df_base_especiales,
            campania_normalizada,
            df_importador_descuentos,
        )

        if df_importador_descuentos is not None:
            df_base_especiales, df_produciendo = incorporar_nuevos_dtos(
                df_base_especiales,
                df_importador_descuentos,
                df_produciendo,
            )

        df_produciendo, df_base_especiales = _aplicar_descuentos_y_base_especiales(
            df_produciendo,
            df_base_especiales,
            columna_atiende,
            desde_desc_especiales,
        )
        df_produciendo = _calcular_costo_importador(df_produciendo, columna_costo_sin_descuento)
        df_importador = crear_importador(
            df_produciendo,
            anio_campania,
            fecha_inicio,
            fecha_final,
            campania_anio,
        )
        paths_salidas = _exportar_archivos_segundo_produciendo(
            df_importador,
            df_produciendo,
            df_base_especiales,
            campania_normalizada,
            anio,
            carpeta_guardado,
        )
        logger.info("Segundo Produciendo finalizado. Archivos en: %s", carpeta_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="segundo_produciendo",
            estado="OK",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_base_especiales": ruta_base_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={
                "campania": campania_normalizada,
                "anio": anio,
                "fecha_compras_inicio": fecha_compras_inicio,
                "fecha_compras_final": fecha_compras_final,
            },
            metricas={"filas_salida": len(df_produciendo)},
            archivos_generados=paths_salidas,
        )
        return {**paths_salidas, "manifiesto": path_manifiesto, "id_ejecucion": id_proceso}
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="segundo_produciendo",
            estado="ERROR",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_base_especiales": ruta_base_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Segundo Produciendo. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Segundo Produciendo: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Segundo Produciendo.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="segundo_produciendo",
            estado="ERROR",
            entradas={
                "ruta_produciendo": ruta_produciendo,
                "ruta_base_especiales": ruta_base_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Segundo Produciendo. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error

