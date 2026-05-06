import logging
import os
import pandas as pd

from costeando.utilidades.errores_aplicacion import (
    ErrorEntradaArchivo,
    ErrorEsquemaArchivo,
    ErrorReglaNegocio,
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
                accion_sugerida="Complete los valores faltantes y vuelva a ejecutar.")


def validar_duplicados(df: pd.DataFrame, columnas: list, nombre_df: str = "DataFrame"):
    if df.duplicated(subset=columnas).any():
        return True
    return False


def validar_columna_numerica(df: pd.DataFrame, columna: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna], nombre_df)
    valores = pd.to_numeric(df[columna], errors="coerce")
    invalidos = valores.isna()
    if invalidos.any():
        filas_invalidas = [posicion + 2 for posicion, invalido in enumerate(invalidos) if invalido]
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=(
                f"Valores numericos invalidos en {columna} de {nombre_df}. "
                f"Filas Excel: {filas_invalidas}"
            ),
            codigo_error="CST-VAL-003",
            titulo_usuario="Tipo de dato invalido",
            mensaje_usuario=f"La columna {columna} del archivo {nombre_df} contiene valores no numericos.",
            accion_sugerida=f"Revise el formato numerico de la columna {columna} en las filas indicadas en el log.")


def validar_columna_fecha_parseable(df: pd.DataFrame, columna: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna], nombre_df)
    fechas = pd.to_datetime(df[columna], errors="coerce", format="mixed")
    invalidas = fechas.isna()
    if invalidas.any():
        filas_invalidas = [posicion + 2 for posicion, invalida in enumerate(invalidas) if invalida]
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=(
                f"Fechas invalidas en {columna} de {nombre_df}. "
                f"Filas Excel: {filas_invalidas}"
            ),
            codigo_error="CST-VAL-004",
            titulo_usuario="Formato de fecha invalido",
            mensaje_usuario=f"La columna {columna} del archivo {nombre_df} contiene fechas invalidas.",
            accion_sugerida="Corrija el formato de fecha en las filas indicadas en el log y reintente.")


def normalizar_campania(
    campania: str,
    nombre_proceso: str,
    codigo_error: str,
) -> str:
    valor = str(campania).strip()
    if not valor.isdigit():
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Campania invalida en {nombre_proceso}: {campania}",
            codigo_error=codigo_error,
            titulo_usuario="Campania invalida",
            mensaje_usuario="La campania informada no es valida.",
            accion_sugerida="Use una campania numerica entre 1 y 18.",
        )
    numero = int(valor)
    if not 1 <= numero <= 18:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Campania fuera de rango en {nombre_proceso}: {campania}",
            codigo_error=codigo_error,
            titulo_usuario="Campania invalida",
            mensaje_usuario="La campania informada esta fuera del rango permitido.",
            accion_sugerida="Use una campania entre 1 y 18.",
        )
    return str(numero).zfill(2)


def validar_anio(anio: str, nombre_proceso: str, codigo_error: str) -> str:
    valor = str(anio).strip()
    if not valor.isdigit() or len(valor) != 4:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Anio invalido en {nombre_proceso}: {anio}",
            codigo_error=codigo_error,
            titulo_usuario="Anio invalido",
            mensaje_usuario="El anio informado no es valido.",
            accion_sugerida="Use un anio con formato AAAA.",
        )
    return valor


def validar_rango_fechas(
    fecha_inicio: str,
    fecha_final: str,
    nombre_proceso: str,
    codigo_error_formato: str,
    codigo_error_orden: str | None = None,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    try:
        inicio = pd.to_datetime(fecha_inicio, format="%d/%m/%Y")
        final = pd.to_datetime(fecha_final, format="%d/%m/%Y")
    except ValueError as error:
        raise ErrorReglaNegocio(
            mensaje_tecnico=f"Fechas invalidas en {nombre_proceso}: {error}",
            codigo_error=codigo_error_formato,
            titulo_usuario="Formato de fecha invalido",
            mensaje_usuario="Las fechas informadas no tienen formato valido.",
            accion_sugerida="Use formato dd/mm/aaaa para inicio y fin.",
        ) from error
    if inicio > final:
        raise ErrorReglaNegocio(
            mensaje_tecnico=(
                f"Rango de fechas invalido en {nombre_proceso}: "
                f"inicio={fecha_inicio}, final={fecha_final}"
            ),
            codigo_error=codigo_error_orden or codigo_error_formato,
            titulo_usuario="Rango de fechas invalido",
            mensaje_usuario="La fecha de inicio no puede ser posterior a la fecha final.",
            accion_sugerida="Corrija el rango de fechas y vuelva a ejecutar.",
        )
    return inicio, final


def validar_clave_unica(df: pd.DataFrame, columna_clave: str, nombre_df: str = "DataFrame"):
    validar_columnas(df, [columna_clave], nombre_df)
    if df[columna_clave].duplicated().any():
        raise ErrorEsquemaArchivo(
            mensaje_tecnico=f"Se detectaron claves duplicadas en {columna_clave} para {nombre_df}",
            codigo_error="CST-VAL-005",
            titulo_usuario="Clave duplicada",
            mensaje_usuario=f"El archivo {nombre_df} contiene valores repetidos en {columna_clave}.",
            accion_sugerida=f"Elimine duplicados en {columna_clave} y vuelva a procesar.")


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
            accion_sugerida="Verifique el encabezado de la clave de producto.")
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    
    return df
