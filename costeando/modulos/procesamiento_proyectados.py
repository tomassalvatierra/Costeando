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
    normalizar_campania,
    validar_anio,
    validar_archivo_excel,
    validar_columnas,
)

logger = logging.getLogger(__name__)


def obtener_coeficiente(df_coef_pivot: pd.DataFrame, campania: str, variable: str) -> float:
    resultado = 1 + df_coef_pivot[
        (df_coef_pivot["CAMPAÑA-AÑO"] == campania) & (df_coef_pivot["VARIABLE"] == variable)
    ]["Coeficiente"]
    if not resultado.empty:
        return resultado.values[0]
    raise ErrorEsquemaArchivo(
        mensaje_tecnico=f"No existe coeficiente para campania={campania}, variable={variable}",
        codigo_error="CST-VAL-006",
        titulo_usuario="Coeficiente faltante",
        mensaje_usuario="La tabla de coeficientes no contiene todos los valores necesarios.",
        accion_sugerida="Revise que existan coeficientes para cada campania proyectada y variable.",
    )


def generar_campanias(campania_inicial: str, anio_inicial: str) -> tuple[list[str], list[str]]:
    campanias = []
    mc_campanias = []
    campania_numero = int(campania_inicial[-2:]) + 1
    anio = int(anio_inicial)
    for _ in range(10):
        if campania_numero > 18:
            campania_numero = 1
            anio += 1
        campanias.append(f"C{str(campania_numero).zfill(2)}-{anio}")
        mc_campanias.append(f"MC{str(campania_numero).zfill(2)}-{anio}")
        campania_numero += 1
    return campanias, mc_campanias


def _validar_parametros_proyectados(campania: str, anio: str, carpeta_guardado: str) -> tuple[str, str]:
    if not all([campania, anio]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan campania/anio en Proyectados.",
            codigo_error="CST-NEG-060",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania o anio para ejecutar Proyectados.",
            accion_sugerida="Complete campania y anio antes de ejecutar.",
        )
    if not carpeta_guardado:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico carpeta de salida en Proyectados.",
            codigo_error="CST-NEG-061",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta de salida valida.",
        )
    anio_normalizado = validar_anio(anio, "Proyectados", "CST-NEG-063")
    campania_normalizada = normalizar_campania(campania, "Proyectados", "CST-NEG-062")
    return campania_normalizada, anio_normalizado


def _cargar_dataframes_proyectados(ruta_lista: str, ruta_coeficientes: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        df_lista = pd.read_excel(ruta_lista, engine="openpyxl")
        df_coeficientes = pd.read_excel(ruta_coeficientes, engine="openpyxl")
    except Exception as error:
        raise ErrorEntradaArchivo(
            mensaje_tecnico=f"No se pudieron leer archivos de Proyectados: {error}",
            codigo_error="CST-IO-005",
            titulo_usuario="Error de lectura de archivos",
            mensaje_usuario="No fue posible leer uno o mas archivos de entrada.",
            accion_sugerida="Revise rutas, formato y que los archivos no esten abiertos.",
        ) from error
    return df_lista, df_coeficientes


def _validar_columnas_minimas_proyectados(
    df_lista: pd.DataFrame,
    df_coeficientes: pd.DataFrame,
    columna_costo_lista: str,
):
    validar_columnas(
        df_lista,
        ["Codigo", "VARIABLE", "LLEVA CF", "Tipo", "Estado", columna_costo_lista],
        "listado de costos",
    )
    validar_columnas(df_coeficientes, ["CAMPAÑA-AÑO"], "tabla de coeficientes")
    if len(df_coeficientes.columns) < 2:
        raise ErrorEsquemaArchivo(
            mensaje_tecnico="La tabla de coeficientes no tiene columnas de variables.",
            codigo_error="CST-VAL-001",
            titulo_usuario="Estructura de archivo invalida",
            mensaje_usuario="La tabla de coeficientes no contiene variables de coeficiente.",
            accion_sugerida="Revise el archivo de coeficientes y sus encabezados.",
        )


def _proyectar_costos(
    df_lista: pd.DataFrame,
    df_coeficientes: pd.DataFrame,
    columna_costo_lista: str,
    campania_inicial: str,
    anio_inicial: str,
) -> pd.DataFrame:
    df_proyectado = df_lista.copy()
    columnas_fijas = list(df_proyectado.columns)
    futuras_campanias, futuras_mc_campanias = generar_campanias(campania_inicial, anio_inicial)

    nuevas_columnas = {columna: [None] * len(df_proyectado) for columna in futuras_campanias}
    df_proyectado = df_proyectado.assign(**nuevas_columnas)
    df_coef_pivot = df_coeficientes.melt(id_vars=["CAMPAÑA-AÑO"], var_name="VARIABLE", value_name="Coeficiente")

    for campania in futuras_campanias:
        df_proyectado[campania] = df_proyectado.apply(
            lambda fila: obtener_coeficiente(df_coef_pivot, campania, fila["VARIABLE"]),
            axis=1,
        )

    for indice, campania in enumerate(futuras_campanias):
        if indice == 0:
            df_proyectado["M" + campania] = round(df_proyectado[columna_costo_lista] * df_proyectado[campania], 2)
        else:
            campania_anterior = futuras_campanias[indice - 1]
            df_proyectado["M" + campania] = round(df_proyectado["M" + campania_anterior] * df_proyectado[campania], 2)

    columnas_intercaladas = []
    for coeficiente, costo in zip(futuras_campanias, futuras_mc_campanias):
        columnas_intercaladas.append(coeficiente)
        columnas_intercaladas.append(costo)

    nueva_orden_columnas = columnas_fijas + columnas_intercaladas
    df_proyectado = df_proyectado.reindex(columns=nueva_orden_columnas)
    df_proyectado["LLEVA CF"] = df_proyectado["LLEVA CF"].replace(0, "No")
    return df_proyectado


def _generar_listado_comercial(df_proyectado: pd.DataFrame, columna_costo_lista: str) -> pd.DataFrame:
    df_comercial = df_proyectado.copy()
    condicion_exclusion = (
        (df_comercial["Tipo"] == "GG")
        | (df_comercial["Tipo"] == "MO")
        | (df_comercial["Tipo"] == "SV")
        | (df_comercial["Estado"] == "INA")
        | (df_comercial[columna_costo_lista] == 0)
    )
    df_comercial = df_comercial[~condicion_exclusion]
    df_comercial = df_comercial[df_comercial["Codigo"].astype(str).str.len() <= 5]
    return df_comercial


def _exportar_resultados_proyectados(
    df_proyectado: pd.DataFrame,
    df_proyectado_comercial: pd.DataFrame,
    campania: str,
    anio: str,
    carpeta_guardado: str,
) -> Dict[str, str]:
    if not os.path.exists(carpeta_guardado):
        os.makedirs(carpeta_guardado)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    path_proyectado = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Costos Proyectados C{campania}-{anio}.xlsx",
    )
    path_proyectado_comercial = os.path.join(
        carpeta_guardado,
        f"{fecha_hoy} Costos Proyectados C{campania}-{anio} PARA COMERCIAL.xlsx",
    )
    df_proyectado.to_excel(path_proyectado, index=False, engine="openpyxl")
    df_proyectado_comercial.to_excel(path_proyectado_comercial, index=False, engine="openpyxl")
    return {
        "proyectado": path_proyectado,
        "proyectado_comercial": path_proyectado_comercial,
    }


def procesar_proyectados_puro(
    ruta_lista: str,
    ruta_coef: str,
    camp_inicial: str,
    anio_inicial: str,
    carpeta_guardado: str,
    id_ejecucion: str | None = None,
) -> Dict[str, str]:
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Proyectados. ID=%s", id_proceso)
        validar_archivo_excel(ruta_lista, "listado de costos")
        validar_archivo_excel(ruta_coef, "tabla de coeficientes")
        campania_normalizada, anio_inicial = _validar_parametros_proyectados(
            camp_inicial,
            anio_inicial,
            carpeta_guardado,
        )

        df_lista, df_coeficientes = _cargar_dataframes_proyectados(ruta_lista, ruta_coef)
        df_lista = estandarizar_columna_producto(df_lista, "listado de costos")

        anio_campania = anio_inicial[3] + campania_normalizada
        columna_costo_lista = "COSTO LISTA " + anio_campania
        _validar_columnas_minimas_proyectados(df_lista, df_coeficientes, columna_costo_lista)
        df_lista["Codigo"] = df_lista["Codigo"].astype(str).str.strip()

        df_proyectado = _proyectar_costos(
            df_lista,
            df_coeficientes,
            columna_costo_lista,
            campania_normalizada,
            anio_inicial,
        )
        df_proyectado_comercial = _generar_listado_comercial(df_proyectado, columna_costo_lista)
        salidas = _exportar_resultados_proyectados(
            df_proyectado,
            df_proyectado_comercial,
            campania_normalizada,
            anio_inicial,
            carpeta_guardado,
        )
        logger.info("Proyectados finalizado. Archivos en: %s", carpeta_guardado)

        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado,
            id_ejecucion=id_proceso,
            proceso="proyectados",
            estado="OK",
            entradas={"ruta_lista": ruta_lista, "ruta_coef": ruta_coef},
            parametros={"campania": campania_normalizada, "anio": anio_inicial},
            metricas={
                "filas_proyectado": len(df_proyectado),
                "filas_proyectado_comercial": len(df_proyectado_comercial),
            },
            archivos_generados=salidas,
        )
        return {**salidas, "manifiesto": path_manifiesto, "id_ejecucion": id_proceso}
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="proyectados",
            estado="ERROR",
            entradas={"ruta_lista": ruta_lista, "ruta_coef": ruta_coef},
            parametros={"campania": camp_inicial, "anio": anio_inicial},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error(
            "Error controlado en Proyectados. ID=%s Codigo=%s",
            id_proceso,
            error.codigo_error,
            exc_info=True,
        )
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Proyectados: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Proyectados.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=carpeta_guardado or ".",
            id_ejecucion=id_proceso,
            proceso="proyectados",
            estado="ERROR",
            entradas={"ruta_lista": ruta_lista, "ruta_coef": ruta_coef},
            parametros={"campania": camp_inicial, "anio": anio_inicial},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Proyectados. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error

