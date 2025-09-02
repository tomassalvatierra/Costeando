import pandas as pd
import logging
from typing import Dict
import os
from costeando.utilidades.validaciones import validar_archivo_excel
from costeando.utilidades.configuracion_logging import configurar_logging

configurar_logging()
logger = logging.getLogger(__name__)

def estandarizar_columna_producto(df: pd.DataFrame, nombre_df: str) -> pd.DataFrame:
    if 'Producto' in df.columns:
        df = df.rename(columns={'Producto': 'Codigo'})
        logger.debug(f"Columna 'Producto' renombrada a 'Codigo' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    else:
        logger.debug(f"No se encontró la columna 'Producto' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    return df


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
        (ruta_compilado_fechas_ult_compra, "compilado_fechas_ult_compra")
    ]

    for df,nombre in lista:
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
            (df_compilado_fechas_ult_compra, 'compilado_fechas_ult_compra')]
        
        lista_df = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_df]
        
        df_produciendo, df_costo_primo, df_base_descuentos, df_listado, df_comprando, df_mdo, df_leader_list, df_compilado_fechas_ult_compra = lista_df
        
        df_listado_general = df_listado.copy()
        
        #Si la columna "Costo Estandard" existe, renombrarla, sino comprobar que COSTO LISTA " + anio[-1] +campania  exista
        if "Costo Estandard" in df_listado_general.columns:
            logger.debug("Renombrando columna 'Costo Estandard' a 'COSTO LISTA ...'")
            df_listado_general.rename(columns={"Costo Estandard":"COSTO LISTA " + anio[-1] +campania}, inplace= True)
        else:
            if "COSTO LISTA " + anio[-1] +campania not in df_listado_general.columns:
                error_msg = f"Ninguna de las columnas 'Costo Estandard' o 'COSTO LISTA {anio[-1]}{campania}' existe en el listado."
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        df_mdo_806 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0806"])]
        df_mdo_807 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0807"])]
        df_mdo_808 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0808"])]
    
        #Merge con Maestro Costo Primo
        logger.debug("Realizando merges de MANO DE OBRA TOTAL")
        df_listado_general = pd.merge(df_listado_general,df_costo_primo[["Codigo","Costo Estand"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Costo Estand":"COSTO PRIMO (MATERIALES)"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_806[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0806 SEGUNDOS MO ELAB. X KILO"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_807[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0807 SEGUNDOS MO ENV. X UNIDAD"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_808[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0808 SEGUNDOS MO ACOND.X UNIDAD"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_compilado_fechas_ult_compra[["Codigo", "Tipo Orden"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Tipo Orden":"TIPO ULT COMPRA"}, inplace=True)
        
        #Merge con CALCULO PRODUCIENDO
        logger.debug("Realizando merge costo de producción y CARGA FABRIL")
        df_listado_general = pd.merge(df_listado_general,df_produciendo[["Codigo", "Costo Producción"]], how="left", on="Codigo")

        # Selecciona las columnas relevantes
        cols = ["Codigo", "Costo sin Descuento C"+campania, "% de obsolescencia", "ROYALTY", "DESCUENTO ESPECIAL", "APLICA DDE CA:"]

        # Unifica los datos de produciendo y comprando
        df_aux = pd.merge(
            df_produciendo[cols], 
            df_comprando[cols], 
            on="Codigo", 
            how="outer", 
            suffixes=('_prod', '_comp')
        )

        # Prioriza produciendo, si no hay, usa comprando
        for campo in cols[1:]:
            df_aux[campo] = df_aux[campo + '_prod'].combine_first(df_aux[campo + '_comp'])

        # Deja solo Codigo y las columnas unificadas
        df_aux = df_aux[["Codigo"] + cols[1:]]

        # Haz un solo merge con el listado general
        df_listado_general = pd.merge(df_listado_general, df_aux, how="left", on="Codigo")

        #Merge con Base de Descuentos
        df_listado_general = pd.merge(df_listado_general,df_base_descuentos[["Codigo", "TIPO-DESCUENTO"]], how="left", on="Codigo")
        print(df_listado_general.info())
        #Si el DESCUENTO ESPECIAL es cero quitar el TIPO-DESCUENTO
        df_listado_general.loc[df_listado_general["DESCUENTO ESPECIAL"].fillna(0) == 0, "TIPO-DESCUENTO"] = None
        
        #Merge con Base de Descuentos
        logger.debug("Realizando merges con el leader list")
        df_listado_general = pd.merge(df_listado_general,df_leader_list[["Codigo", "TIPO_OF"]], how="left", on="Codigo")
        df_listado_general = pd.merge(df_listado_general,df_leader_list[["Codigo", "LEYEOFE"]], how="left", on="Codigo")
        
        df_listado_general.drop_duplicates(subset=["Codigo"], keep="first", inplace=True)
        
        #Convertir columnas de descuentos a numéricas
        df_listado_general["DESCUENTO ESPECIAL"] = pd.to_numeric(df_listado_general["DESCUENTO ESPECIAL"], errors='coerce')
        df_listado_general["ROYALTY"] = pd.to_numeric(df_listado_general["ROYALTY"], errors='coerce')
        df_listado_general["% de obsolescencia"] = pd.to_numeric(df_listado_general["% de obsolescencia"], errors='coerce')
        
        logger.debug("Sumatoria de descuentos")
        df_listado_general["% Sumatoria de Descuentos"] = (
        df_listado_general["DESCUENTO ESPECIAL"].fillna(0) +
        df_listado_general["ROYALTY"].fillna(0) +
        df_listado_general["% de obsolescencia"].fillna(0)).round(2)     
        
        logger.debug("Inicia fase de calculos")
        
        df_listado_general["MANO DE OBRA TOTAL"] = (df_listado_general["Costo Producción"] - df_listado_general["COSTO PRIMO (MATERIALES)"]).round(2)
        df_listado_general["Costo sin Descuento C"+campania] = (df_listado_general["COSTO LISTA " + anio[-1] +campania] / ((100-df_listado_general["% Sumatoria de Descuentos"])/100)).round(2)
        df_listado_general["CARGA FABRIL"] = (df_listado_general["Costo sin Descuento C"+campania] - df_listado_general["Costo Producción"]).round(1)
        df_listado_general["DESCUENTO APLICADO $"] = (df_listado_general["COSTO LISTA " + anio[-1] +campania] - df_listado_general["Costo sin Descuento C"+campania]).round(2)
        df_listado_general["VALOR STOCK CON DESCUENTO"] = (df_listado_general["Stock Actual"] * df_listado_general["COSTO LISTA " + anio[-1] +campania]).round(2)
        logger.info("termina fase de calculos")
        
        #Las columnas COSTO PRIMO (MATERIALES), MANO DE OBRA TOTAL, COSTO DE PRODUCCION Y CARGA FABRIL DEBEN SER CERO SI LA COLUMNA COSTO LISTA ES CERO
        df_listado_general.loc[df_listado_general["COSTO LISTA " + anio[-1] +campania] == 0, ["COSTO PRIMO (MATERIALES)", "MANO DE OBRA TOTAL", "Costo Producción", "CARGA FABRIL"]] = 0
        
        # al costo de prouccion hay qyue sacarle lo que este en cero en el costo final.
        
        df_listado_general["MANO DE OBRA TOTAL"] = df_listado_general["MANO DE OBRA TOTAL"].fillna(0)
        df_listado_general["CARGA FABRIL"] = df_listado_general["CARGA FABRIL"].fillna(0)
        df_listado_general["COD MADRE"] = ""
        df_listado_general["COD COMB"] = ""
        # Reindexar columnas según el orden solicitado
        columnas_ordenadas = [
            "Periodo", "Codigo", "COD MADRE", "COD COMB", "Descripcion", "COSTO PRIMO (MATERIALES)", "MANO DE OBRA TOTAL", "Costo Producción", "CARGA FABRIL", "Costo sin Descuento C" + campania, "% Sumatoria de Descuentos", "COSTO LISTA " + anio[-1] +campania, "TIPO DE COSTO","ADI N°", "Ult. Compra", "TIPO ULT COMPRA", "MOD 0806 SEGUNDOS MO ELAB. X KILO", "MOD 0807 SEGUNDOS MO ENV. X UNIDAD", "MOD 0808 SEGUNDOS MO ACOND.X UNIDAD", "% de obsolescencia", "ROYALTY", "DESCUENTO ESPECIAL", "APLICA DDE CA:", "TIPO-DESCUENTO", "DESCUENTO APLICADO $", "Stock Actual", "VALOR STOCK CON DESCUENTO", "TIPO_OF", "LEYEOFE", "Estado", "Cod Actualiz", "VARIABLE", "LLEVA CF", "Tipo", "Desc.Tipo", "Grupo", "Desc. Grupo", "Sub Grupo", "Desc.Sub Grupo", "Entra MRP", "Atiende Necsdd", "Prov", "Ult P/C", "Razon Social", "Fecha Alta"
        ]
        # Reindex solo si existen las columnas, las que falten se ignoran
        columnas_existentes = [col for col in columnas_ordenadas if col in df_listado_general.columns]
        df_listado_general = df_listado_general.reindex(columns=columnas_existentes)

        path_listado = os.path.join(carpeta_guardado, "Listado General Completo.xlsx")
        logger.info(f"Guardando Listado gral procesado en: {path_listado}")
        df_listado_general.to_excel(path_listado, index=False, engine="openpyxl")

        logger.info(f"Archivos guardados correctamente en: {carpeta_guardado}")
        return {
            'Listado_general_completo': path_listado,
        }
    except Exception as e:
        logger.exception("Error durante el procesamiento de Leader List.")
        raise 
    
    
    
    
    