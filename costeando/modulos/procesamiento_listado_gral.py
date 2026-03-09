import pandas as pd
import logging
from typing import Dict
import os
from datetime import datetime

from costeando.utilidades.validaciones import validar_archivo_excel, estandarizar_columna_producto
from costeando.utilidades.configuracion_logging import configurar_logging

configurar_logging()
logger = logging.getLogger(__name__)


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
    carpeta_guardado: str
) -> Dict[str, str]:

    logger.info("Iniciando procesamiento puro de Listado General")
    campania = campania.zfill(2)

    lista = [
        (ruta_produciendo, "produciendo"),
        (ruta_comprando, "comprando"),
        (ruta_costo_primo, "costo_primo"),
        (ruta_base_descuentos, "base_descuentos"),
        (ruta_listado, "listado"),
        (ruta_mdo, "mdo"),
        (ruta_leader_list, "leader_list"),
        (ruta_compilado_fechas_ult_compra, "compilado_fechas_ult_compra"),
    ]
    for df, nombre in lista:
        logger.debug(f"Validando archivo: {nombre} ({df})")
        validar_archivo_excel(df, nombre)

    try:
        logger.info("Leyendo archivos Excel de entrada...")
        df_produciendo = pd.read_excel(ruta_produciendo, engine="openpyxl")
        df_comprando = pd.read_excel(ruta_comprando, engine="openpyxl")
        df_costo_primo = pd.read_excel(ruta_costo_primo, engine="openpyxl")
        df_base_descuentos = pd.read_excel(ruta_base_descuentos, engine="openpyxl")
        df_listado = pd.read_excel(ruta_listado, engine="openpyxl")
        df_mdo = pd.read_excel(ruta_mdo, engine="openpyxl", skiprows=1)
        df_leader_list = pd.read_excel(ruta_leader_list, engine="openpyxl")
        df_compilado_fechas_ult_compra = pd.read_excel(ruta_compilado_fechas_ult_compra, engine="openpyxl")
    except Exception as e:
        logger.error(f"Error al leer los archivos de entrada: {e}")
        raise

    try:
        lista_df = [
            (df_produciendo, 'produciendo'),
            (df_costo_primo, 'costo_primo'),
            (df_base_descuentos, 'base_descuentos'),
            (df_listado, 'listado'),
            (df_comprando, 'comprando'),
            (df_mdo, 'mdo'),
            (df_leader_list, 'leader_list'),
            (df_compilado_fechas_ult_compra, 'compilado_fechas_ult_compra'),
        ]
        lista_df = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_df]
        (df_produciendo, df_costo_primo, df_base_descuentos, df_listado,
         df_comprando, df_mdo, df_leader_list, df_compilado_fechas_ult_compra) = lista_df

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

        logger.debug("Realizando merge costo de producción y CARGA FABRIL")
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
            "TIPO DE COSTO", "ADI N°", "Ult. Compra", "TIPO ULT COMPRA",
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
        logger.info(f"Guardando Listado gral procesado en: {path_listado}")
        df_listado_general.to_excel(path_listado, index=False, engine="openpyxl")

        logger.info(f"Archivos guardados correctamente en: {carpeta_guardado}")
        return {'Listado_general_completo': path_listado}

    except Exception:
        logger.exception("Error durante el procesamiento de Listado General.")
        raise