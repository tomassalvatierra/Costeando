import pandas as pd
import os
from datetime import datetime
import logging
from costeando.utilidades.auditoria import guardar_manifiesto_ejecucion
from costeando.utilidades.errores_aplicacion import (
    ErrorAplicacion,
    ErrorEsquemaArchivo,
    ErrorInternoInesperado,
    ErrorReglaNegocio,
    generar_id_ejecucion,
)
from costeando.utilidades.func_faltante_cotizacion import asignar_faltantes_cotizacion
from costeando.utilidades.validaciones import (
    estandarizar_columna_producto,
    validar_archivo_excel,
    validar_columna_fecha_parseable,
    validar_columnas,
)

logger = logging.getLogger(__name__)

def campania_a_absoluta(campania, anio):
    return (anio - 2021) * 18 + campania

def actualizar_estado_vencido(df_base_dtos, campania_actual, anio_actual, campania_stock):
    logger.info("Actualizando estado vencido")
    df_base_dtos["anio/campania abs"] = df_base_dtos.apply(
        lambda row: campania_a_absoluta(row["Campania_Otorgamiento"], row["Anio_Otorgamiento"]), axis=1)
    absoluta_actual = campania_a_absoluta(campania_actual, anio_actual)
    if campania_stock is not None:
        try:
            campania_limite = int(campania_stock)
            if campania_limite < 1:
                campania_limite += 18
                anio_limite = anio_actual - 1
            else:
                anio_limite = anio_actual
            absoluta_limite = campania_a_absoluta(campania_limite, anio_limite)
            mascara_terminados = (
                (df_base_dtos["TIPO-DESCUENTO"] == "AGOTAMIENTO-PRODUCTO TERMINADO") &
                (df_base_dtos["Stock Actual"] < 500) &
                (df_base_dtos["anio/campania abs"] < absoluta_limite))
            df_base_dtos.loc[mascara_terminados, "VENCIDO"] = "Si"
            df_base_dtos.loc[mascara_terminados, "NOTAS"] = "Pierde el descuento por no tener stock"
        except ValueError:
            logger.info("Error: campania_stock no es un nAmero vAlido.")
    mascara_general = df_base_dtos.apply(
        lambda row: (absoluta_actual - campania_a_absoluta(row["Campania_Otorgamiento"], row["Anio_Otorgamiento"])) > 27, axis=1)
    df_base_dtos.loc[mascara_general, "VENCIDO"] = "Si"
    df_base_dtos.loc[mascara_general, "NOTAS"] = "Pierde descuento por sobrepasar de 27 campaAas(aAo y medio)"
    mascara_componentes = (
        (df_base_dtos["TIPO-DESCUENTO"] == "AGOTAMIENTO-COMPONENTES") &
        df_base_dtos.apply(
            lambda row: (absoluta_actual - campania_a_absoluta(row["Campania_Otorgamiento"], row["Anio_Otorgamiento"])) > 18, axis=1))
    df_base_dtos.loc[mascara_componentes, "VENCIDO"] = "Si"
    df_base_dtos.loc[mascara_componentes, "NOTAS"] = "Pierde descuento por sobrepasar de 18 campaAas"
    df_base_dtos.drop(columns=["Anio_Otorgamiento", "Campania_Otorgamiento", "Stock Actual", "anio/campania abs"], inplace=True, errors="ignore")
    df_no_vencidos = df_base_dtos.loc[df_base_dtos["VENCIDO"] == "No"].copy()
    cambios = (
        (df_base_dtos["NOTAS"] == "Pierde el descuento por no tener stock") |
        (df_base_dtos["NOTAS"] == "Pierde descuento por sobrepasar de 27 campaAas(aAo y medio)") |
        (df_base_dtos["NOTAS"] == "Pierde descuento por sobrepasar de 18 campaAas"))
    df_cambios = df_base_dtos.loc[cambios]
    return df_base_dtos, df_no_vencidos, df_cambios

def calcular_obsolescencia(fecha, row):
    if pd.isna(row["Ult. Compra"]):
        return 0
    dias_antiguedad = (fecha - row["Ult. Compra"]).days
    if dias_antiguedad < 365: return 0
    elif dias_antiguedad <= 730: return 10
    elif dias_antiguedad <= 1095: return 20
    elif dias_antiguedad <= 1460: return 30
    elif dias_antiguedad <= 1825: return 40
    elif dias_antiguedad <= 2190: return 50
    elif dias_antiguedad < 3650: return 50
    else: return 75

def calcular_costo_sin_descuento(row, df):
    if pd.isna(row["LLEVA CF"]):
        if (row["Grupo"] in (1, 5)) and (row["Tipo"] in ("PA", "PC")):
            lleva_cf = "Si"
            df.at[row.name, "LLEVA CF"] = "Si"
        else:
            lleva_cf = "No"
            df.at[row.name, "LLEVA CF"] = "No"
    else:
        lleva_cf = row["LLEVA CF"]
    if lleva_cf == "Si":
        return round(row["Costo ProducciAn"] / 0.84, 2)
    else:
        return round(row["Costo ProducciAn"], 2)


def _validar_parametros_primer_produciendo(campania_actual, anio_actual, ruta_salida):
    if not all([campania_actual, anio_actual]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan parametros campania/anio en Primer Produciendo.",
            codigo_error="CST-NEG-020",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan campania o anio para ejecutar Primer Produciendo.",
            accion_sugerida="Complete campania y anio antes de ejecutar.",
        )
    if not ruta_salida:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico ruta de salida en Primer Produciendo.",
            codigo_error="CST-NEG-021",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta de salida valida.",
        )


def _obtener_columna_atiende(df_maestro: pd.DataFrame) -> str:
    for nombre_columna in ["AAtiende Ne?", "Atiende Ne?", "¿Atiende Ne?"]:
        if nombre_columna in df_maestro.columns:
            return nombre_columna
    raise ErrorEsquemaArchivo(
        mensaje_tecnico="No se encontro columna de atencion de necesidad en maestro produciendo.",
        codigo_error="CST-VAL-001",
        titulo_usuario="Estructura de archivo invalida",
        mensaje_usuario="El archivo maestro no tiene columna de atencion de necesidad.",
        accion_sugerida="Revise encabezados del maestro y vuelva a intentar.",
    )


def _validar_columnas_minimas_primer_produciendo(
    df_produciendo_anterior: pd.DataFrame,
    df_maestro_produciendo: pd.DataFrame,
    df_stock: pd.DataFrame,
    df_descuentos_especiales: pd.DataFrame,
    df_rotacion: pd.DataFrame,
):
    columna_atiende = _obtener_columna_atiende(df_maestro_produciendo)
    validar_columnas(
        df_maestro_produciendo,
        ["Codigo", "Blq. de Pant", columna_atiende, "Tipo", "Grupo", "Ult. Compra", "Costo Estand"],
        "maestro produciendo",
    )
    validar_columna_fecha_parseable(df_maestro_produciendo, "Ult. Compra", "maestro produciendo")
    validar_columnas(df_produciendo_anterior, ["Codigo"], "produciendo anterior")
    validar_columnas(df_stock, ["Codigo", "Stock Actual"], "stock")
    validar_columnas(df_descuentos_especiales, ["Codigo", "VENCIDO"], "descuentos especiales")
    validar_columnas(df_rotacion, ["Codigo", "Clasificacion"], "rotacion")
    return columna_atiende


def procesar_primer_produciendo(
    campania_actual, anio_actual,
    ruta_produciendo_anterior, ruta_maestro_produciendo, ruta_stock,
    ruta_descuentos_especiales, ruta_rotacion, ruta_estructuras, ruta_salida,
    id_ejecucion: str | None = None,
):
    id_proceso = id_ejecucion or generar_id_ejecucion()
    try:
        logger.info("Iniciando procesamiento puro de Primer Produciendo. ID=%s", id_proceso)
        validar_archivo_excel(ruta_produciendo_anterior, "produciendo anterior")
        validar_archivo_excel(ruta_maestro_produciendo, "maestro produciendo")
        validar_archivo_excel(ruta_stock, "stock")
        validar_archivo_excel(ruta_descuentos_especiales, "descuentos especiales")
        validar_archivo_excel(ruta_rotacion, "rotacion")
        validar_archivo_excel(ruta_estructuras, "estructuras")
        _validar_parametros_primer_produciendo(campania_actual, anio_actual, ruta_salida)
        fecha_actual = datetime.now()
        campania_stock = int(campania_actual) - 5
        df_produciendo_anterior = pd.read_excel(ruta_produciendo_anterior, engine="openpyxl")
        df_maestro_produciendo = pd.read_excel(ruta_maestro_produciendo, engine="openpyxl")
        df_stock = pd.read_excel(ruta_stock, engine="openpyxl")
        df_descuentos_especiales = pd.read_excel(ruta_descuentos_especiales, engine="openpyxl")
        df_rotacion = pd.read_excel(ruta_rotacion, engine="openpyxl")
        lista_dfs = [
            (df_produciendo_anterior, "Produciendo anterior"),
            (df_maestro_produciendo, "Maestro produciendo"),
            (df_stock, "Stock"),
            (df_descuentos_especiales, "Base descuentos especiales"),
            (df_rotacion, "Rotacion"),
        ]
        lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
        df_produciendo_anterior, df_maestro_produciendo, df_stock, df_descuentos_especiales, df_rotacion = lista_dfs
        columna_atiende = _validar_columnas_minimas_primer_produciendo(
            df_produciendo_anterior,
            df_maestro_produciendo,
            df_stock,
            df_descuentos_especiales,
            df_rotacion,
        )
        df_maestro_produciendo.rename(columns={"Costo Estand": "Costo ProducciAn"}, inplace=True)
        df_produciendo = df_maestro_produciendo.copy()
        df_produciendo = df_produciendo.replace("  /  /    ", "")
        df_produciendo["Ult. Compra"] = pd.to_datetime(df_produciendo["Ult. Compra"], errors="coerce")
        for old, new in [(1,"Si"),(2,"No"),("1","Si"),("2","No")]:
            df_produciendo["Blq. de Pant"] = df_produciendo["Blq. de Pant"].replace(old, new)
        df_produciendo[columna_atiende] = df_produciendo[columna_atiende].replace("C", "Comprando")
        eliminaciones = (
            df_produciendo["Tipo"].isin(["GG","GN","GI"]) |
            (df_produciendo["Blq. de Pant"] == "Si") |
            (df_produciendo[columna_atiende] == "Comprando"))
        df_produciendo = df_produciendo[~eliminaciones]
        for column, data_frame in zip(
            ["LLEVA CF","Revision de tipo","Stock Actual","Clasificacion"],
            [df_produciendo_anterior, df_produciendo_anterior, df_stock, df_rotacion]
        ):
            if data_frame is not None and column in data_frame.columns:
                df_produciendo = pd.merge(df_produciendo, data_frame[["Codigo", column]], how="left", on="Codigo")
        df_produciendo = df_produciendo.drop_duplicates(subset="Codigo", keep="first")
        df_produciendo["Costo sin Descuento C"+str(campania_actual)] = df_produciendo.apply(
            lambda row: calcular_costo_sin_descuento(row, df_produciendo), axis=1)
        df_produciendo["% de obsolescencia"] = df_produciendo.apply(
            lambda row: calcular_obsolescencia(fecha_actual, row)
            if (row["Tipo"] in ("PA","PD","PC")) and (row["Grupo"] in (1,2,3,4,6)) else None, axis=1)
        df_sin_vencidos = df_descuentos_especiales.copy()
        if "VENCIDO" in df_sin_vencidos.columns:
            df_sin_vencidos = df_sin_vencidos[df_sin_vencidos["VENCIDO"] != "Si"]
        if "VENCIDO" in df_descuentos_especiales.columns:
            df_descuentos_especiales = df_descuentos_especiales[df_descuentos_especiales["VENCIDO"] != "No"]
        if "APLICA DDE CA:" in df_sin_vencidos.columns:
            split_aplica = df_sin_vencidos["APLICA DDE CA:"].str.split("/", expand=True)
            df_sin_vencidos["Anio_Otorgamiento"] = split_aplica[0].fillna(0).astype(int)
            df_sin_vencidos["Campania_Otorgamiento"] = split_aplica[1].fillna(0).astype(int)
        if "Stock Actual" in df_stock.columns:
            df_sin_vencidos = pd.merge(df_sin_vencidos, df_stock[["Codigo","Stock Actual"]], how="left", on="Codigo")
            df_sin_vencidos["Stock Actual"] = df_sin_vencidos["Stock Actual"].fillna(0)
        df_sin_vencidos, df_no_vencidos, df_cambios = actualizar_estado_vencido(
            df_sin_vencidos, int(campania_actual), int(anio_actual), campania_stock)
        df_descuentos_especiales = pd.concat([df_descuentos_especiales, df_sin_vencidos], ignore_index=True)
        if df_no_vencidos is not None and "DESCUENTO ESPECIAL" in df_no_vencidos.columns:
            df_produciendo = pd.merge(df_produciendo, df_no_vencidos[["Codigo","DESCUENTO ESPECIAL"]], how="left", on="Codigo")
        if df_no_vencidos is not None and "APLICA DDE CA:" in df_no_vencidos.columns:
            df_produciendo = pd.merge(df_produciendo, df_no_vencidos[["Codigo","APLICA DDE CA:"]], how="left", on="Codigo")
        if "ROYALTY" in df_descuentos_especiales.columns:
            df_produciendo = pd.merge(df_produciendo, df_descuentos_especiales[["Codigo","ROYALTY"]], how="left", on="Codigo")
        df_produciendo = df_produciendo.drop_duplicates(subset="Codigo", keep="first")
        if ruta_estructuras is not None:
            df_produciendo = asignar_faltantes_cotizacion(df_produciendo, df_maestro_produciendo, ruta_estructuras)
            if "Descripcion" in df_maestro_produciendo.columns:
                df_maestro_produciendo.rename(columns={"Descripcion":"DESCRIPCION COMP","Codigo":"COMPONENTE FALTANTE"}, inplace=True)
                if "COMPONENTE FALTANTE" in df_produciendo.columns:
                    df_produciendo["COMPONENTE FALTANTE"] = df_produciendo["COMPONENTE FALTANTE"].astype(str).str.strip()
                    df_produciendo = pd.merge(df_produciendo, df_maestro_produciendo[["COMPONENTE FALTANTE","DESCRIPCION COMP"]], how="left", on="COMPONENTE FALTANTE")
        if not os.path.exists(ruta_salida):
            os.makedirs(ruta_salida)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        path_produciendo = os.path.join(ruta_salida, f"{fecha_hoy} Calculo Produciendo-Primera etapa C{campania_actual}-{anio_actual}.xlsx")
        path_base_descuentos = os.path.join(ruta_salida, f"{fecha_hoy} BASE DTOS-Primer etapa produciendo C{campania_actual}-{anio_actual}.xlsx")
        path_cambios = os.path.join(ruta_salida, f"{fecha_hoy} Cambios realizado en la base-Primera Etapa C{campania_actual}-{anio_actual}.xlsx")
        df_produciendo.to_excel(path_produciendo, index=False, engine="openpyxl")
        df_descuentos_especiales.to_excel(path_base_descuentos, index=False, engine="openpyxl")
        df_cambios.to_excel(path_cambios, index=False, engine="openpyxl")
        logger.info(f"Primer Produciendo finalizado. Archivos en: {ruta_salida}")
        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida,
            id_ejecucion=id_proceso,
            proceso="primer_produciendo",
            estado="OK",
            entradas={
                "ruta_produciendo_anterior": ruta_produciendo_anterior,
                "ruta_maestro_produciendo": ruta_maestro_produciendo,
                "ruta_stock": ruta_stock,
                "ruta_descuentos_especiales": ruta_descuentos_especiales,
                "ruta_rotacion": ruta_rotacion,
                "ruta_estructuras": ruta_estructuras,
            },
            parametros={"campania_actual": campania_actual, "anio_actual": anio_actual},
            metricas={"filas_salida": len(df_produciendo)},
            archivos_generados={
                "produciendo": path_produciendo,
                "base_descuentos": path_base_descuentos,
                "cambios": path_cambios,
            },
        )
        return {
            "produciendo": path_produciendo,
            "base_descuentos": path_base_descuentos,
            "cambios": path_cambios,
            "manifiesto": path_manifiesto,
            "id_ejecucion": id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida or ".",
            id_ejecucion=id_proceso,
            proceso="primer_produciendo",
            estado="ERROR",
            entradas={
                "ruta_produciendo_anterior": ruta_produciendo_anterior,
                "ruta_maestro_produciendo": ruta_maestro_produciendo,
                "ruta_stock": ruta_stock,
                "ruta_descuentos_especiales": ruta_descuentos_especiales,
                "ruta_rotacion": ruta_rotacion,
                "ruta_estructuras": ruta_estructuras,
            },
            parametros={"campania_actual": campania_actual, "anio_actual": anio_actual},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error("Error controlado en Primer Produciendo. ID=%s Codigo=%s", id_proceso, error.codigo_error, exc_info=True)
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Primer Produciendo: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Primer Produciendo.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida or ".",
            id_ejecucion=id_proceso,
            proceso="primer_produciendo",
            estado="ERROR",
            entradas={
                "ruta_produciendo_anterior": ruta_produciendo_anterior,
                "ruta_maestro_produciendo": ruta_maestro_produciendo,
                "ruta_stock": ruta_stock,
                "ruta_descuentos_especiales": ruta_descuentos_especiales,
                "ruta_rotacion": ruta_rotacion,
                "ruta_estructuras": ruta_estructuras,
            },
            parametros={"campania_actual": campania_actual, "anio_actual": anio_actual},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Primer Produciendo. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error
