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

def asignacion_campanas(campana: str, anio: str):
    if campana == "01":
        campana_anterior = "18"
        anio_anterior = str(int(anio) - 1)
    else:
        campana_anterior = str(int(campana) - 1).zfill(2)
        anio_anterior = anio
    ultimo_digito_anio_anterior = anio_anterior[-1]
    anio_campana = ultimo_digito_anio_anterior + campana
    anio_campana_anterior = ultimo_digito_anio_anterior + campana_anterior
    return campana_anterior, anio_campana_anterior, anio_campana

def proceso_combinadas(df_combinadas: pd.DataFrame) -> pd.DataFrame:
    df_grouped = df_combinadas.groupby('COMBINADA')['CODIGON'].agg(lambda x: ' - '.join(map(str, x))).reset_index()
    df_grouped.rename(columns={'CODIGON': 'COD COMB'}, inplace=True)
    df_grouped.rename(columns={'COMBINADA': 'Codigo'}, inplace=True)
    return df_grouped

def estandarizar_codigo(df: pd.DataFrame) -> pd.DataFrame:
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    return df

def procesar_leader_list_puro(
    ruta_leader_list: str,
    ruta_listado_anterior: str,
    ruta_maestro: str,
    ruta_dobles: str,
    ruta_combinadas: str,
    ruta_stock: str,
    campana: str,
    anio: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    
    """
    Procesa el módulo Leader List y guarda los archivos generados en la carpeta indicada.
    Devuelve un diccionario con los paths de los archivos generados.
    """
    logger.info("Iniciando procesamiento puro de Leader List")
    campana = campana.zfill(2)
    
    campana_anterior, anio_campana_anterior, anio_campana = asignacion_campanas(campana, anio)

    lista =[
        (ruta_leader_list,"leader list"),
        (ruta_listado_anterior,"Listado anterior"),
        (ruta_maestro,"Maestro"),
        (ruta_dobles,"Dobles"),
        (ruta_combinadas,"Combinadas"),
        (ruta_stock, "Stock")]

    for df,nombre in lista:
        logger.debug(f"Validando archivo: {nombre} ({df})")
        validar_archivo_excel(df, nombre)

    try:
        logger.info("Leyendo archivos Excel de entrada...")
        df_leader_list = pd.read_excel(ruta_leader_list, engine = "openpyxl")
        df_costo_anterior = pd.read_excel(ruta_listado_anterior, engine = "openpyxl")
        df_maestro = pd.read_excel(ruta_maestro, engine = "openpyxl")
        df_dobles = pd.read_excel(ruta_dobles, engine = "openpyxl")
        df_combinadas = pd.read_excel(ruta_combinadas, engine = "openpyxl")
        df_stock = pd.read_excel(ruta_stock, engine = "openpyxl")
        logger.info("Archivos Excel leídos correctamente.")
    except Exception as e:
        logger.exception("Error leyendo archivos Excel de entrada.")
        raise

    try:
        logger.debug("Procesando combinadas agrupadas...")
        df_combinadas_agrupadas = proceso_combinadas(df_combinadas)

        # Renombro la columna del listado de costos para poder realizar el merge
        df_dobles.rename(columns={"CODIGO_DOB": "Codigo", "CODIGO_ORI": "COD MADRE"}, inplace=True)
        df_leader_list.rename(columns = {"CODIGON" : "Codigo"}, inplace = True)
        df_combinadas.rename(columns = {"CODIGON" : "Codigo"} , inplace = True)
        
        lista_dfs = [
            (df_costo_anterior, 'Listado de Costos N-1'),
            (df_maestro, 'Maestro'),
            (df_stock, 'Stock'),
            (df_leader_list,"Leader List"),
            (df_dobles,"Dobles"),
            (df_combinadas_agrupadas,"Combinadas agrupadas"),
            (df_combinadas,"Combinadas")
            ]

        lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
        
        df_costo_anterior, df_maestro, df_stock, df_leader_list, df_dobles, df_combinadas_agrupadas, df_combinadas = lista_dfs

        df_leader_list = df_leader_list.query("Codigo not in [99000, 99001, 99002, 99003, 99004, 99005]")

        columnas_a_incluir = [
            "COSTO LISTA " + anio_campana, "TIPO COSTO", "%VAR C" + campana + "VS C" + campana_anterior,
            "VAR C" + campana + "VS C-ESTIM", "OBSERVACIONES"
        ]
        nuevas_columnas_data = {columna: [None] * len(df_leader_list) for columna in columnas_a_incluir}
        
        df_leader_list = df_leader_list.assign(**nuevas_columnas_data)

        logger.debug("Realizando merges de información...")
        df_leader_list = pd.merge(df_leader_list,df_costo_anterior[["Codigo", "COSTO LISTA " + anio_campana_anterior,"DESCUENTO ESPECIAL","APLICA DDE CA:"]], how = "left", on="Codigo")
        df_leader_list = pd.merge(df_leader_list,df_costo_anterior[["Codigo", "TIPO-DESCUENTO"]], how = "left", on="Codigo")
        df_leader_list = pd.merge(df_leader_list,df_maestro[["Codigo", "¿Atiende Ne?","Estado"]], how = "left")
        df_leader_list = pd.merge(df_leader_list,df_dobles[["Codigo", "COD MADRE"]], how = "left")
        df_leader_list = pd.merge(df_leader_list,df_combinadas_agrupadas[["Codigo", "COD COMB"]], how = "left")
        
        df_leader_list.rename(columns = {"Estado": "ESTADO TOTVS"}, inplace=True)
        
        df_leader_list = pd.merge(df_leader_list,df_stock[["Codigo", "Stock Actual"]], how = "left")
        df_leader_list['UNIDADES REALES ESTIMADAS']=df_leader_list['UNID_EST']*2
        df_leader_list['STOCK VS UNID_TOTALES ESTIM']=df_leader_list['Stock Actual'] - df_leader_list['UNIDADES REALES ESTIMADAS']
        
        df_leader_list.rename(columns = {"DESCUENTO ESPECIAL": "DESCUENTO ESPECIAL (N-1)"}, inplace=True)
        df_leader_list.rename(columns = {"TIPO-DESCUENTO": "TIPO-DESCUENTO (N-1)"}, inplace=True)
        
        df_leader_list.loc[df_leader_list["COD MADRE"].notnull(), "TIPO COSTO"] = "CÓDIGO DOBLE"
        df_leader_list.loc[df_leader_list["COD COMB"].notnull(), "TIPO COSTO"] = "CÓDIGO COMBINADA"
        
        df_leader_list.drop_duplicates(subset = "Codigo", keep = "first", inplace = True)
        
        columnas_finales = [
            "CAMP", "ANO", "Codigo", "COD MADRE", "COD COMB", "DESCRIP", "COSTO LISTA " + anio_campana, "TIPO COSTO", "¿Atiende Ne?",
            "DIVISION", "UXP", "TIPO_OF", "LEYEOFE", "PR_OFERTA", "PR_NORMAL", "MAR_EST", "COSTO_EST", "TIPO_EST", "FACT_EST", "PAGINA",
            "CATEGORIA", "LEYENDA","SEGMENTO", "LEY_SEG", "SUB_LINEA", "LEYESUBL", "LINEA", "LEY_LIN" , "PROC", "LEYEPRO", "UNID_EST", "CONSIG", "CABECERA",
            "COEFICIE", "EMPRESA", "ESTADO", "CMP_ESTA", "CUOTAS", "OM_EST", "PED_EST", "COS_ESTOT", "COSTO LISTA " + anio_campana_anterior,
            "%VAR C" + campana + " VS C" + campana_anterior, "VAR C" + campana + " VS CESTIM", "OBSERVACIONES", "DESCUENTO ESPECIAL (N-1)","TIPO-DESCUENTO (N-1)",
            "APLICA DDE CA:","ESTADO TOTVS", 'Stock Actual', 'UNIDADES REALES ESTIMADAS', "STOCK VS UNID_TOTALES ESTIM",
        ]
        
        df_leader_list = df_leader_list.reindex(columns = columnas_finales)
        
        path_leader_list = os.path.join(carpeta_guardado, "Leader List procesado.xlsx")
        path_combinadas_agrupadas = os.path.join(carpeta_guardado, "Combinadas agrupadas.xlsx")

        logger.info(f"Guardando Leader List procesado en: {path_leader_list}")
        df_leader_list.to_excel(path_leader_list, index=False, engine="openpyxl")
        logger.info(f"Guardando Combinadas agrupadas en: {path_combinadas_agrupadas}")
        df_combinadas_agrupadas.to_excel(path_combinadas_agrupadas, index=False, engine="openpyxl")
        
        logger.info(f"Archivos guardados correctamente en: {carpeta_guardado}")
        return {
            'leader_list': path_leader_list,
            'combinadas_agrupadas': path_combinadas_agrupadas
        }
    except Exception as e:
        logger.exception("Error durante el procesamiento de Leader List.")
        raise 