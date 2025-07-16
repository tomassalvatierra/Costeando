import pandas as pd
import numpy as np
import logging
from typing import Dict
import os
from costeando.utilidades.validaciones import validar_archivo_excel

logger = logging.getLogger(__name__)

def estandarizar_codigo(df: pd.DataFrame) -> pd.DataFrame:
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    return df

def procesar_valorizacion_dyc_puro(
    ruta_listado: str,
    ruta_combinadas: str,
    ruta_dobles: str,
    campana: str,
    anio: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    """
    Procesa el módulo Valorización DYC y guarda el archivo generado en la carpeta indicada.
    Devuelve un diccionario con el path del archivo generado.
    """
    try:
        logger.info("Iniciando procesamiento puro de Valorización DYC")
        # Validar archivos de entrada
        validar_archivo_excel(ruta_listado, "listado")
        validar_archivo_excel(ruta_combinadas, "combinadas")
        validar_archivo_excel(ruta_dobles, "dobles")
        if not all([campana, anio]):
            raise ValueError('Debe ingresar todos los datos solicitados.')
        ultimo_digito_anio = anio[-1]
        anio_campana = ultimo_digito_anio + campana
        df_dobles = pd.read_excel(ruta_dobles, engine = 'openpyxl')
        df_combinadas = pd.read_excel(ruta_combinadas, engine = 'openpyxl')
        df_lista_general_costos = pd.read_excel(ruta_listado, engine = 'openpyxl')
        logger.debug(f"Archivos de entrada cargados: dobles({len(df_dobles)}), combinadas({len(df_combinadas)}), listado({len(df_lista_general_costos)})")
        df_combinadas.sort_values(by = 'COMBINADA', inplace = True)
        df_lista_general_costos.rename(columns={'Producto':'Codigo'}, inplace=True)
        df_combinadas.rename(columns = {'CODIGON': 'Codigo'}, inplace =True)
        df_dobles.rename(columns = {'CODIGO_ORI': 'Codigo'}, inplace =True)
        df_lista_general_costos = estandarizar_codigo(df_lista_general_costos)
        df_combinadas=  estandarizar_codigo(df_combinadas)
        df_dobles = estandarizar_codigo(df_dobles)
        df_combinadas = pd.merge(df_combinadas, df_lista_general_costos[['Codigo', 'COSTO LISTA ' + anio_campana]], on = 'Codigo', how = 'left')
        df_combinadas['COSTO LISTA ' + anio_campana] = df_combinadas['COSTO LISTA ' + anio_campana].replace(0, np.nan)
        df_combinadas['COSTO TOTAL'] = df_combinadas['COSTO LISTA ' + anio_campana] * df_combinadas['CANTIDAD']
        df_combinadas_valorizadas = df_combinadas.groupby('COMBINADA')['COSTO TOTAL'].apply(lambda x: np.nan if x.isnull().any() else x.sum()).reset_index()
        df_combinadas_valorizadas = df_combinadas_valorizadas.loc[
            (df_combinadas_valorizadas['COSTO TOTAL'] != 0) & 
            (df_combinadas_valorizadas['COSTO TOTAL'].notna()), :]
        df_combinadas_valorizadas = df_combinadas_valorizadas.rename(columns = {'COSTO TOTAL': 'COSTO LISTA ' + anio_campana, 'COMBINADA': 'Codigo'})
        df_dobles_valorizadas = pd.merge(df_dobles, df_lista_general_costos[['Codigo', 'COSTO LISTA ' + anio_campana]], on = 'Codigo', how = 'left')
        df_dobles_valorizadas = df_dobles_valorizadas.loc[
            (df_dobles_valorizadas['COSTO LISTA ' + anio_campana] != 0) & 
            (df_dobles_valorizadas['COSTO LISTA ' + anio_campana].notna()), :]
        df_dobles_valorizadas = df_dobles_valorizadas.rename(columns = {'DESCR_DOB': 'Descripcion', 'Codigo' : 'COD MADRE', 'CODIGO_DOB': 'Codigo'})
        df_combinadas = df_combinadas.rename(columns = {'DESCR_COMB': 'Descripcion', 'Codigo': 'CODIGON', 'COMBINADA': 'Codigo'})
        df_combinadas_valorizadas = df_combinadas_valorizadas.merge(df_combinadas[['Codigo', 'Descripcion']], on = 'Codigo', how = 'left')
        df_combinadas_valorizadas.drop_duplicates(subset = 'Codigo', keep = 'first', inplace = True)
        path_guardado = os.path.join(carpeta_guardado, "Valorizacion DyC.xlsx")
        if os.path.exists(path_guardado):
            os.remove(path_guardado)
        with pd.ExcelWriter(path_guardado, engine="openpyxl") as writer:
            df_combinadas_valorizadas.to_excel(writer, sheet_name = "MEMO COMBINADAS", index=False)
            df_dobles_valorizadas.to_excel(writer, sheet_name = 'MEMO DOBLES',index=False)
        logger.info(f"Archivo guardado en: {path_guardado}")
        return {"valorizacion_dyc": path_guardado}
    except Exception as e:
        logger.error(f"Error en el procesamiento de Valorización DYC: {e}", exc_info=True)
        raise 