import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict
from costeando.utilidades.validaciones import validar_archivo_excel, estandarizar_columna_producto

logger = logging.getLogger(__name__)


def _obtener_columna_atiende(df_productos: pd.DataFrame) -> str:
    for nombre_columna in ["AAtiende Ne?", "Atiende Ne?", "¿Atiende Ne?"]:
        if nombre_columna in df_productos.columns:
            return nombre_columna
    raise ValueError("No se encontro columna atiende en produciendo.")


def incorporar_nuevos_dtos(df_especiales, df_importador, df_productos):
    nuevos_codigos = df_importador["Codigo"].tolist()
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "VENCIDO"] = "Si"
    df_especiales.loc[df_especiales["Codigo"].isin(nuevos_codigos), "NOTAS"] = "Vencido, ingreso un nuevo descuento"
    dict_descuentos = dict(zip(df_importador["Codigo"], zip(df_importador["DESCUENTO ESPECIAL"], df_importador["APLICA DDE CA:"])))
    mapeo = df_productos["Codigo"].map(dict_descuentos).apply(lambda x: x if isinstance(x, tuple) else (None, None))
    nuevos_valores = mapeo.apply(pd.Series)
    nuevos_valores.columns = ["DESCUENTO ESPECIAL","APLICA DDE CA:"]
    nuevos_valores = nuevos_valores.set_index(df_productos.index)
    df_productos[["DESCUENTO ESPECIAL","APLICA DDE CA:"]] = df_productos[["DESCUENTO ESPECIAL","APLICA DDE CA:"]].combine_first(nuevos_valores)
    return pd.concat([df_especiales, df_importador], ignore_index=True), df_productos


def crear_importador(df, aAo_campaAa, fecha_compras_inicio, fecha_compras_final, campaAa_aAo):
    df_importador = df[["Codigo","Costo 2do Importador"]].copy()
    df_importador["Columna3"] = "27251293061"
    df_importador["Columna4"] = aAo_campaAa
    df_importador["Columna5"] = campaAa_aAo
    df_importador["Columna6"] = fecha_compras_inicio
    df_importador["Columna7"] = fecha_compras_final
    df_importador[["Columna8","Columna9"]] = "001"
    df_importador["Columna10"] = "99999999"
    df_importador["Columna11"] = "31/12/1999"
    df_importador["Costo 2do Importador"] = df_importador["Costo 2do Importador"].round(2).astype(str)
    return df_importador.reset_index(drop=True)


def procesar_segundo_produciendo(
    ruta_produciendo, ruta_base_especiales, ruta_importador_descuentos,
    campaAa, aAo, fecha_compras_inicio, fecha_compras_final, carpeta_guardado
):
    try:
        logger.info("Iniciando procesamiento puro de segundo produciendo")
        campaAa = campaAa.zfill(2)
        aAo_campaAa = aAo[-1] + campaAa
        campaAa_aAo = f"CAMP-{campaAa}/{str(int(aAo) % 100)}"
        fecha_inicio = pd.to_datetime(fecha_compras_inicio, format="%d/%m/%Y")
        fecha_final = pd.to_datetime(fecha_compras_final, format="%d/%m/%Y")
        desde_desc_especiales = f"{aAo}/{campaAa.zfill(2)}"
        validar_archivo_excel(ruta_produciendo, "Produciendo")
        validar_archivo_excel(ruta_base_especiales, "Base especiales")
        df_produciendo = pd.read_excel(ruta_produciendo, engine="openpyxl")
        df_base_especiales = pd.read_excel(ruta_base_especiales, engine="openpyxl")
        if ruta_importador_descuentos:
            df_importador_descuentos = pd.read_excel(ruta_importador_descuentos, engine="openpyxl")
            lista_dfs = [(df_produciendo,"Produciendo"),(df_base_especiales,"Base Desc."),(df_importador_descuentos,"Importador")]
            lista_dfs = [estandarizar_columna_producto(df, n) for df, n in lista_dfs]
            df_produciendo, df_base_especiales, df_importador_descuentos = lista_dfs
            df_base_especiales, df_produciendo = incorporar_nuevos_dtos(df_base_especiales, df_importador_descuentos, df_produciendo)
        else:
            lista_dfs = [(df_produciendo,"Produciendo"),(df_base_especiales,"Base Desc.")]
            lista_dfs = [estandarizar_columna_producto(df, n) for df, n in lista_dfs]
            df_produciendo, df_base_especiales = lista_dfs
        df_produciendo.sort_values(by=["Codigo","APLICA DDE CA:"], ascending=[True,False], inplace=True)
        df_produciendo.drop_duplicates(subset=["Codigo"], keep="first", inplace=True)
        df_produciendo.reset_index(drop=True, inplace=True)
        df_produciendo["% sumatoria descuentos"] = (
            df_produciendo["% de obsolescencia"].fillna(0) +
            df_produciendo["DESCUENTO ESPECIAL"].fillna(0) +
            df_produciendo["ROYALTY"].fillna(0)).round(2)
        mascara_superado_75 = df_produciendo["% sumatoria descuentos"] > 75
        exceso = df_produciendo.loc[mascara_superado_75, "% sumatoria descuentos"] - 75
        df_produciendo.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] = (
            df_produciendo.loc[mascara_superado_75, "DESCUENTO ESPECIAL"] - exceso).clip(lower=0)
        codigos_ajustados = df_produciendo.loc[mascara_superado_75, "Codigo"].unique()
        df_base_especiales.loc[df_base_especiales["Codigo"].isin(codigos_ajustados), "VENCIDO"] = "Si"
        nuevos_descuentos = df_produciendo.loc[mascara_superado_75, ["Codigo","DESCUENTO ESPECIAL"]].copy()
        nuevos_descuentos["APLICA DDE CA:"] = desde_desc_especiales
        nuevos_descuentos["VENCIDO"] = "No"
        nuevos_descuentos["NOTAS"] = "Descuento ajustado porque superaba 75%"
        columna_atiende = _obtener_columna_atiende(df_produciendo)
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_produciendo[["Codigo","Descripcion"]], how="left")
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_produciendo[["Codigo", columna_atiende]], how="left")
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_base_especiales[["Codigo","TIPO-DESCUENTO"]], how="left")
        nuevos_descuentos = nuevos_descuentos.rename(columns={columna_atiende: "ATIENDE NE?"})
        nuevos_descuentos.drop_duplicates(inplace=True)
        df_base_especiales = pd.concat([df_base_especiales, nuevos_descuentos], ignore_index=True)
        df_produciendo["% sumatoria descuentos"] = (
            df_produciendo["% de obsolescencia"].fillna(0) +
            df_produciendo["DESCUENTO ESPECIAL"].fillna(0) +
            df_produciendo["ROYALTY"].fillna(0)).round(2)
        df_produciendo.loc[df_produciendo["DESCUENTO ESPECIAL"] == 0, "APLICA DDE CA:"] = np.nan
        costo_importador = round(df_produciendo["Costo sin Descuento C"+campaAa] * (1 - (df_produciendo["% sumatoria descuentos"]/100)), 2)
        df_produciendo = df_produciendo.assign(costo_p_importador=costo_importador.values)
        df_produciendo.rename(columns={"costo_p_importador": "Costo 2do Importador"}, inplace=True)
        df_produciendo["Costo 2do Importador"].fillna(0, inplace=True)
        df_base_especiales["DESCUENTO ESPECIAL"] = df_base_especiales["DESCUENTO ESPECIAL"].round(2)
        df_produciendo["DESCUENTO ESPECIAL"] = df_produciendo["DESCUENTO ESPECIAL"].round(2)
        if "COMPONENTE FALTANTE" in df_produciendo.columns:
            df_produciendo.loc[df_produciendo["COMPONENTE FALTANTE"].notna(), "Costo 2do Importador"] = 0
        df_importador = crear_importador(df_produciendo, aAo_campaAa, fecha_inicio, fecha_final, campaAa_aAo)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        path_importador = f"{carpeta_guardado}/{fecha_hoy} Importador Produciendo C{campaAa}-{aAo}.xlsx"
        path_produciendo = f"{carpeta_guardado}/{fecha_hoy} Calculo Produciendo-Segunda etapa C{campaAa}-{aAo}.xlsx"
        path_especiales = f"{carpeta_guardado}/{fecha_hoy} BASE DTOS-Segunda etapa produciendo C{campaAa}-{aAo}.xlsx"
        df_importador.to_excel(path_importador, sheet_name="Importador", index=False)
        df_produciendo.to_excel(path_produciendo, sheet_name="Calculo Produciendo 2da", index=False)
        df_base_especiales.to_excel(path_especiales, sheet_name="Base 2do Produciendo", index=False)
        logger.info(f"Archivos guardados en: {carpeta_guardado}")
        return {"importador": path_importador, "produciendo": path_produciendo, "especiales": path_especiales}
    except Exception as e:
        logger.error(f"Error en Segundo Produciendo: {e}", exc_info=True)
        raise
