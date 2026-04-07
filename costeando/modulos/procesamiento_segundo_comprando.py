import logging
import os
from datetime import datetime

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
    validar_archivo_excel,
    validar_columnas,
)

logger = logging.getLogger(__name__)


def incorporar_nuevos_dtos(df_especiales, df_importador, df_productos):
    nuevos_codigos = df_importador["Codigo"].tolist()
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "VENCIDO"] = "Si"
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "NOTAS"] = "Vencido, ingreso un nuevo descuento"

    dict_descuentos = dict(
        zip(
            df_importador["Codigo"],
            zip(df_importador["DESCUENTO ESPECIAL"], df_importador["APLICA DDE CA:"]),
        )
    )
    mapeo = df_productos["Codigo"].map(dict_descuentos).apply(
        lambda valor: valor if isinstance(valor, tuple) else (None, None)
    )
    nuevos_valores = mapeo.apply(pd.Series)
    nuevos_valores.columns = ["DESCUENTO ESPECIAL", "APLICA DDE CA:"]
    nuevos_valores = nuevos_valores.set_index(df_productos.index)

    df_productos[["DESCUENTO ESPECIAL", "APLICA DDE CA:"]] = df_productos[
        ["DESCUENTO ESPECIAL", "APLICA DDE CA:"]
    ].combine_first(nuevos_valores)

    df_base_especiales_concatenado = pd.concat([df_especiales, df_importador], ignore_index=True)
    return df_base_especiales_concatenado, df_productos


def _obtener_columna_atiende(df_productos: pd.DataFrame) -> str:
    for nombre_columna in ["AAtiende Ne?", "Atiende Ne?","¿Atiende Ne?"]:
        if nombre_columna in df_productos.columns:
            return nombre_columna
    raise ErrorEsquemaArchivo(
        mensaje_tecnico="No se encontro columna atiende en Segundo Comprando.",
        codigo_error="CST-VAL-001",
        titulo_usuario="Estructura de archivo invalida",
        mensaje_usuario="El archivo comprando no tiene columna de atiende.",
        accion_sugerida="Revise encabezados del archivo comprando.",
    )


def _validar_parametros_segundo_comprando(
    campania: str,
    anio: str,
    fecha_compras_inicio: str,
    fecha_compras_final: str,
    carpeta_guardado: str,
):
    if not all([campania, anio, fecha_compras_inicio, fecha_compras_final]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan parametros obligatorios en Segundo Comprando.",
            codigo_error="CST-NEG-040",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania, anio o fechas para ejecutar.",
            accion_sugerida="Complete campania, anio y fechas de compra.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico carpeta de salida en Segundo Comprando.",
            codigo_error="CST-NEG-041",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio carpeta de salida.",
            accion_sugerida="Seleccione una carpeta valida para guardar resultados.",
        )
    try:
        fecha_inicio = pd.to_datetime(fecha_compras_inicio, format="%d/%m/%Y")
        fecha_final = pd.to_datetime(fecha_compras_final, format="%d/%m/%Y")
    except ValueError as error:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Fechas invalidas en Segundo Comprando: {error}",
            codigo_error="CST-NEG-042",
            titulo_usuario="Formato de fecha invalido",
            mensaje_usuario="Las fechas de compra no tienen formato valido.",
            accion_sugerida="Use formato dd/mm/aaaa para inicio y fin.",
        ) from error
    return fecha_inicio, fecha_final


def _cargar_dataframes_segundo_comprando(
    ruta_comprando: str,
    ruta_costos_especiales: str,
    ruta_importador_descuentos: str | None,
):
    try:
        df_costos_especiales = pd.read_excel(ruta_costos_especiales, engine="openpyxl")
        df_calculo_comprando = pd.read_excel(ruta_comprando, engine="openpyxl")
        df_importador_descuentos = None
        if ruta_importador_descuentos:
            df_importador_descuentos = pd.read_excel(ruta_importador_descuentos, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Segundo Comprando: {error}",
            codigo_error="CST-IO-003",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_calculo_comprando, df_costos_especiales, df_importador_descuentos


def _validar_columnas_minimas_segundo_comprando(
    df_calculo_comprando: pd.DataFrame,
    df_costos_especiales: pd.DataFrame,
    campania: str,
    df_importador_descuentos: pd.DataFrame | None,
):
    columna_costo = "Costo sin Descuento C" + campania
    columna_atiende = _obtener_columna_atiende(df_calculo_comprando)
    validar_columnas(
        df_calculo_comprando,
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
        "comprando",
    )
    validar_columnas(
        df_costos_especiales,
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


def procesar_segundo_comprando(
    ruta_comprando,
    ruta_costos_especiales,
    ruta_importador_descuentos,
    campania,
    anio,
    fecha_compras_inicio,
    fecha_compras_final,
    carpeta_guardado,
    id_ejecucion: str | None = None,
):
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Segundo Comprando. ID=%s", id_proceso)
        validar_archivo_excel(ruta_comprando, "comprando")
        validar_archivo_excel(ruta_costos_especiales, "base descuentos")
        if ruta_importador_descuentos:
            validar_archivo_excel(ruta_importador_descuentos, "importador descuentos")

        fecha_inicio, fecha_final = _validar_parametros_segundo_comprando(
            campania,
            anio,
            fecha_compras_inicio,
            fecha_compras_final,
            carpeta_guardado,
        )
        campania = campania.zfill(2)
        anio_campania = anio[-1] + campania
        desde_desc_especiales = f"{anio}/{campania}"
        campania_anio = f"CAMP-{campania}/{str(int(anio) % 100)}"

        (
            df_calculo_comprando,
            df_costos_especiales,
            df_importador_descuentos,
        ) = _cargar_dataframes_segundo_comprando(
            ruta_comprando,
            ruta_costos_especiales,
            ruta_importador_descuentos,
        )

        if df_importador_descuentos is not None:
            lista_dfs = [
                (df_calculo_comprando, "comprando"),
                (df_costos_especiales, "base descuentos"),
                (df_importador_descuentos, "importador"),
            ]
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
            df_calculo_comprando, df_costos_especiales, df_importador_descuentos = lista_dfs
            _validar_columnas_minimas_segundo_comprando(
                df_calculo_comprando,
                df_costos_especiales,
                campania,
                df_importador_descuentos,
            )
            df_costos_especiales, df_calculo_comprando = incorporar_nuevos_dtos(
                df_costos_especiales,
                df_importador_descuentos,
                df_calculo_comprando,
            )
        else:
            lista_dfs = [
                (df_calculo_comprando, "comprando"),
                (df_costos_especiales, "base descuentos"),
            ]
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
            df_calculo_comprando, df_costos_especiales = lista_dfs
            _validar_columnas_minimas_segundo_comprando(
                df_calculo_comprando,
                df_costos_especiales,
                campania,
                None,
            )

        columna_atiende = _obtener_columna_atiende(df_calculo_comprando)
        columna_costo_sin_descuento = "Costo sin Descuento C" + campania

        df_calculo_comprando.sort_values(by=["Codigo", "APLICA DDE CA:"], ascending=[True, False], inplace=True)
        df_calculo_comprando.drop_duplicates(subset=["Codigo"], keep="first", inplace=True)
        df_calculo_comprando.reset_index(drop=True, inplace=True)

        df_calculo_comprando["% sumatoria descuentos"] = (
            df_calculo_comprando["% de obsolescencia"].fillna(0)
            + df_calculo_comprando["DESCUENTO ESPECIAL"].fillna(0)
            + df_calculo_comprando["ROYALTY"].fillna(0)
        ).round(2)

        mascara_superado_75 = df_calculo_comprando["% sumatoria descuentos"] > 75
        exceso = df_calculo_comprando.loc[mascara_superado_75, "% sumatoria descuentos"] - 75
        df_calculo_comprando.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] = (
            df_calculo_comprando.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] - exceso
        ).clip(lower=0)

        codigos_ajustados = df_calculo_comprando.loc[mascara_superado_75, "Codigo"].unique()
        df_costos_especiales.loc[df_costos_especiales["Codigo"].isin(codigos_ajustados), "VENCIDO"] = "Si"

        nuevos_descuentos = df_calculo_comprando.loc[
            mascara_superado_75,
            ["Codigo", "DESCUENTO ESPECIAL"],
        ].copy()
        nuevos_descuentos["APLICA DDE CA:"] = desde_desc_especiales
        nuevos_descuentos["VENCIDO"] = "No"
        nuevos_descuentos["NOTAS"] = "Descuento ajustado, el anterior superaba el 75%"
        nuevos_descuentos = pd.merge(
            nuevos_descuentos,
            df_calculo_comprando[["Codigo", "Descripcion"]],
            how="left",
        )
        nuevos_descuentos = pd.merge(
            nuevos_descuentos,
            df_calculo_comprando[["Codigo", columna_atiende]],
            how="left",
        )
        nuevos_descuentos = pd.merge(
            nuevos_descuentos,
            df_costos_especiales[["Codigo", "TIPO-DESCUENTO"]],
            how="left",
        )
        nuevos_descuentos = nuevos_descuentos.rename(columns={columna_atiende: "ATIENDE NE?"})
        nuevos_descuentos.drop_duplicates(inplace=True)
        df_costos_especiales = pd.concat([df_costos_especiales, nuevos_descuentos], ignore_index=True)

        df_calculo_comprando["% sumatoria descuentos"] = (
            df_calculo_comprando["% de obsolescencia"].fillna(0)
            + df_calculo_comprando["DESCUENTO ESPECIAL"].fillna(0)
            + df_calculo_comprando["ROYALTY"].fillna(0)
        ).round(2)
        df_calculo_comprando.loc[
            df_calculo_comprando["DESCUENTO ESPECIAL"] == 0,
            "APLICA DDE CA:",
        ] = np.nan

        df_costos_especiales["DESCUENTO ESPECIAL"] = df_costos_especiales["DESCUENTO ESPECIAL"].round(2)
        df_calculo_comprando["DESCUENTO ESPECIAL"] = df_calculo_comprando["DESCUENTO ESPECIAL"].round(2)

        costo_importador = round(
            df_calculo_comprando[columna_costo_sin_descuento]
            * (1 - (df_calculo_comprando["% sumatoria descuentos"] / 100)),
            2,
        )
        df_calculo_comprando = df_calculo_comprando.assign(costo_p_importador=costo_importador.values)
        df_calculo_comprando.rename(columns={"costo_p_importador": "Costo 1er Importador"}, inplace=True)
        df_calculo_comprando["Costo 1er Importador"] = df_calculo_comprando["Costo 1er Importador"].fillna(0)

        df_importador = df_calculo_comprando[["Codigo", "Costo 1er Importador"]].copy()
        df_importador["Columna3"] = "27251293061"
        df_importador["Columna4"] = anio_campania
        df_importador["Columna5"] = campania_anio
        df_importador["Columna6"] = fecha_inicio
        df_importador["Columna7"] = fecha_final
        df_importador["Columna8"] = "001"
        df_importador["Columna9"] = "001"
        df_importador["Columna10"] = "99999999"
        df_importador["Columna11"] = "31/12/1999"
        df_importador["Costo 1er Importador"] = df_importador["Costo 1er Importador"].round(2).astype(str)
        df_importador = df_importador.reset_index(drop=True)

        if not os.path.exists(carpeta_guardado):
            os.makedirs(carpeta_guardado)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        path_comprando = os.path.join(
            carpeta_guardado,
            f"{fecha_hoy} Calculo Comprando-Segunda etapa C{campania}-{anio}.xlsx",
        )
        path_especiales = os.path.join(
            carpeta_guardado,
            f"{fecha_hoy} BASE DTOS-Segunda etapa comprando C{campania}-{anio}.xlsx",
        )
        path_importador = os.path.join(
            carpeta_guardado,
            f"{fecha_hoy} Importador Comprando C{campania}-{anio}.xlsx",
        )
        df_calculo_comprando.to_excel(path_comprando, sheet_name="Calculo Comprando 2da", index=False)
        df_costos_especiales.to_excel(path_especiales, sheet_name="Base 2do Comprando", index=False)
        df_importador.to_excel(path_importador, sheet_name="Importador", index=False)
        logger.info("Archivos guardados en: %s", carpeta_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="segundo_comprando",
            estado="OK",
            entradas={
                "ruta_comprando": ruta_comprando,
                "ruta_costos_especiales": ruta_costos_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={
                "campania": campania,
                "anio": anio,
                "fecha_compras_inicio": fecha_compras_inicio,
                "fecha_compras_final": fecha_compras_final,
            },
            metricas={"filas_salida": len(df_calculo_comprando)},
            archivos_generados={
                "comprando": path_comprando,
                "especiales": path_especiales,
                "importador": path_importador,
            },
        )
        return {
            "comprando": path_comprando,
            "especiales": path_especiales,
            "importador": path_importador,
            "manifiesto": path_manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="segundo_comprando",
            estado="ERROR",
            entradas={
                "ruta_comprando": ruta_comprando,
                "ruta_costos_especiales": ruta_costos_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Segundo Comprando. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Segundo Comprando: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Segundo Comprando.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="segundo_comprando",
            estado="ERROR",
            entradas={
                "ruta_comprando": ruta_comprando,
                "ruta_costos_especiales": ruta_costos_especiales,
                "ruta_importador_descuentos": ruta_importador_descuentos,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Segundo Comprando. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error
