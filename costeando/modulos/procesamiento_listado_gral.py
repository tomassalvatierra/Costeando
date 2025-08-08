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
    campania: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    
    """
    Procesa el módulo Listado general y guarda los archivos generados en la carpeta indicada.
    Devuelve un diccionario con los paths de los archivos generados.
    """
    logger.info("Iniciando procesamiento puro de Leader List")
    campana = campana.zfill(2)
    
    
    lista = [(ruta_produciendo, "produciendo"),
    (ruta_comprando,"comprando"),
    (ruta_costo_primo ,"costo_primo"),
    (ruta_base_descuentos,"base_descuentos"),
    (ruta_listado,"listado"),
    (ruta_mdo,"mdo"),
    (ruta_leader_list,"leader_list")] 

    for df,nombre in lista:
        logger.debug(f"Validando archivo: {nombre} ({df})")
        validar_archivo_excel(df, nombre)

    try:
        logger.info("Leyendo archivos Excel de entrada...")    
        df_produciendo= pd.read_excel(ruta_produciendo ,engine="openpyxl")
        df_comprando= pd.read_excel(ruta_comprando ,engine="openpyxl")
        df_costo_primo= pd.read_excel(ruta_costo_primo ,engine="openpyxl")
        df_base_descuentos= pd.read_excel(ruta_base_descuentos ,engine="openpyxl")
        df_listado= pd.read_excel(ruta_listado ,engine="openpyxl")
        df_mdo= pd.read_excel(ruta_mdo ,engine="openpyxl", skiprows=1)
        df_leader_list = pd.read_excel(ruta_leader_list,engine="openpyxl")
    except Exception as e:
        logger.error(f"Error al leer los archivos de entrada: {e}")
        raise
    
    try:
        df_listado_general = df_listado.copy()

        lista_df = [df_produciendo,df_costo_primo,df_base_descuentos,df_listado, df_comprando,df_mdo,df_leader_list]

        lista_df = [estandarizar_columna_producto(df) for df in lista_df]
        df_produciendo,df_costo_primo,df_base_descuentos,df_listado_general,df_comprando,df_mdo, df_leader_list= lista_df

        df_listado_general.rename(columns={"Costo Estandard":"Costo Lista"}, inplace= True)

        df_mdo_806 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0806"])]
        df_mdo_807 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0807"])]
        df_mdo_808 = df_mdo.loc[df_mdo["Componente"].isin(["MOD0808"])]

        #Merge con Maestro Costo Primo
        logger.debug("Realizando merges de mano de obra")
        df_listado_general = pd.merge(df_listado_general,df_costo_primo[["Codigo","Costo Estand"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Costo Estand":"Costo Primo (materiales)"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_806[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0806 SEGUNDOS MO ELAB. X KILO"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_807[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0807 SEGUNDOS MO ENV. X UNIDAD"}, inplace= True)

        df_listado_general = pd.merge(df_listado_general,df_mdo_808[["Codigo","Cantidad"]], how="left", on="Codigo")
        df_listado_general.rename(columns={"Cantidad":"MOD 0808 SEGUNDOS MO ACOND.X UNIDAD"}, inplace= True)


        #Merge con CALCULO PRODUCIENDO
        logger.debug("Realizando merge costo de producción y carga fabril")
        df_listado_general = pd.merge(df_listado_general,df_produciendo[["Codigo", "Costo Producción"]], how="left", on="Codigo")
        df_listado_general = pd.merge(df_listado_general,df_produciendo[["Codigo", "Lleva CF?"]], how="left", on="Codigo")

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

        #Merge con Base de Descuentos
        logger.debug("Realizando merges con el leader list")
        df_listado_general = pd.merge(df_listado_general,df_leader_list[["Codigo", "TIPO_OF"]], how="left", on="Codigo")
        df_listado_general = pd.merge(df_listado_general,df_leader_list[["Codigo", "LEYEOFE"]], how="left", on="Codigo")

        logger.debug("Sumatoria de descuentos")
        df_listado_general["% Sumatoria de Descuentos"]= df_listado_general["DESCUENTO ESPECIAL"]+df_listado_general["ROYALTY"]+df_listado_general["% de obsolescencia"]

        logger.debug("Inicia fase de calculos")
        df_listado_general["Mano de Obra"] = df_listado_general["Costo Producción"] - df_listado_general["Costo Primo (materiales)"]
        df_listado_general["Costo sin Descuento C"+campania] = df_listado_general["Costo Lista"] / (df_listado_general["% Sumatoria de Descuentos"]/100)
        df_listado_general["Carga Fabril"] = df_listado_general["Costo sin Descuento C"+campania] - df_listado_general["Costo Producción"]
        df_listado_general["Descuento aplicado $"] = df_listado_general["Costo Lista"] - df_listado_general["Costo sin Descuento C"+campania]
        df_listado_general["Costo Total Con Descuento"] = df_listado_general["Stock Actual"] * df_listado_general["Costo Lista"]
        logger.info("termina fase de calculos")


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
    
    
    
    
    