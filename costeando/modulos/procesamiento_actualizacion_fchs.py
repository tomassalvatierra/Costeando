import pandas as pd
import numpy as np
import logging
import os
from typing import Dict
from costeando.utilidades.validaciones import validar_archivo_excel, validar_columnas, validar_duplicados

logger = logging.getLogger(__name__)

def procesar_actualizacion_fchs_puro(
    ruta_estructuras: str,
    ruta_compras: str,
    ruta_maestro: str,
    ruta_ordenes_apuntadas: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    try:
        logger.info("Iniciando procesamiento puro de Actualización FCHS")
        # Validar archivos de entrada
        validar_archivo_excel(ruta_estructuras, "estructuras")
        validar_archivo_excel(ruta_compras, "compras")
        validar_archivo_excel(ruta_maestro, "maestro")
        validar_archivo_excel(ruta_ordenes_apuntadas, "ordenes apuntadas")

        if not carpeta_guardado:
            raise ValueError('Debe indicar una carpeta de guardado.')
        
        logger.debug("Archivos de entrada validados correctamente.")
        df_estructuras = pd.read_excel(ruta_estructuras, usecols="A:P", engine='openpyxl', skiprows=4)
        df_compras = pd.read_excel(ruta_compras, engine='openpyxl')
        df_ordenes_apuntadas = pd.read_excel(ruta_ordenes_apuntadas, usecols="B,C,F,I,J", engine='openpyxl')
        df_maestro = pd.read_excel(ruta_maestro, engine='openpyxl')
        logger.debug(f"Filas cargadas: estructuras({len(df_estructuras)}), compras({len(df_compras)}), ordenes_apuntadas({len(df_ordenes_apuntadas)}), maestro({len(df_maestro)})")
    
        # 2. Preprocesamiento
        df_estructuras["COD_NIVEL0"] = df_estructuras["COD_NIVEL0"].astype(str)
        df_estructuras["CODIGO_PLANO"] = df_estructuras["CODIGO_PLANO"].astype(str)
        df_compras["Producto"] = df_compras["Producto"].astype(str)
        df_ordenes_apuntadas["Producto"] = df_ordenes_apuntadas["Producto"].astype(str)
        df_maestro["Codigo"] = df_maestro["Codigo"].astype(str)
        df_maestro.rename(columns={'Codigo': 'Producto'}, inplace=True)
        
        
        # 3. Fechas servicios
        condicion_servicios = df_compras['Producto'].notna() & df_compras['Producto'].str.startswith('X')
        df_fch_servicios = df_compras[condicion_servicios][['Producto', 'Fch Emision']].copy()
        df_fch_servicios["Producto"] = df_fch_servicios['Producto'].str[1:]
        df_fch_servicios = pd.merge(df_fch_servicios, df_maestro[['Producto', 'Descripcion']], how='left')
        df_fch_servicios['Tipo Orden'] = 'POR OC CON X INICIAL'
        
        # 4. Fechas 161
        condicion_161 = df_compras['Producto'].str.match(r'^161\d{4}$')
        df_fch_161 = df_compras[condicion_161][['Producto', 'Fch Emision']].copy()
        
        df_estructuras = df_estructuras.rename(columns={"CODIGO_PLANO": "Producto"})
        df_maestro_nivel0 = df_maestro.rename(columns={'Producto': 'COD_NIVEL0'})
        
        df_fch_161 = pd.merge(df_fch_161, df_estructuras[["Producto", "COD_NIVEL0"]], how='left')
        df_fch_161 = df_fch_161.dropna(subset=['COD_NIVEL0'])
        df_fch_161 = pd.merge(df_fch_161, df_maestro[['Producto', 'Sub Grupo']], how='left')
        df_fch_161 = pd.merge(df_fch_161, df_maestro_nivel0[['COD_NIVEL0', 'Grupo']], how='left')
        
        df_fch_161['Grupo'] = df_fch_161['Grupo'].astype(int)
        df_fch_161['Sub Grupo'] = df_fch_161['Sub Grupo'].astype(int)
        
        df_fch_161 = df_fch_161.loc[~df_fch_161['Grupo'].isin([0, 1, 5, 6])]
        df_fch_161 = df_fch_161.loc[~df_fch_161['Sub Grupo'].isin([25, 901, 925])]
        
        df_fch_161 = df_fch_161.drop(columns=['Producto', 'Sub Grupo', 'Grupo'])
        df_fch_161 = df_fch_161.rename(columns={"COD_NIVEL0": "Producto"})
        
        df_fch_161 = pd.merge(df_fch_161, df_maestro[['Producto', 'Descripcion']], how='left')
        df_fch_161['Tipo Orden'] = 'POR OC DEL COMPONENTE 161'
        
        # 5. Fechas generales
        df_fch_gral = df_compras[['Producto', 'Descripcion', 'Fch Emision', 'Cantidad']].copy()
        df_fch_gral['Tipo Orden'] = 'X OC'
        # 6. Ordenes apuntadas
        
        df_fchs_ordenes = df_ordenes_apuntadas.loc[
            ((df_ordenes_apuntadas['Tipo Orden'] != "Servicio") &
             (df_ordenes_apuntadas["Tipo Orden"] != "Acondicionado"))
        ].copy()
        
        df_fchs_ordenes.sort_values(by=["Fch Apunte"], ascending=False, inplace=True)
        df_fchs_ordenes = df_fchs_ordenes.drop_duplicates(subset='Producto', keep='first')
        
        if 'Grupo' in df_fchs_ordenes.columns:
            df_fchs_ordenes.drop(columns=['Grupo'], inplace=True)
        df_fchs_ordenes.rename(columns={'Fch Apunte': 'Fch Emision'}, inplace=True)
        
        # 7. Unificar y exportar
        df_concatenado = pd.concat([df_fch_gral, df_fch_servicios, df_fch_161,df_fchs_ordenes], ignore_index=True)
        df_concatenado = pd.merge(df_concatenado, df_maestro[['Producto', 'Descripcion']], how='left')
        df_concatenado['Fch Emision'] = pd.to_datetime(df_concatenado['Fch Emision'], errors='coerce')
        df_concatenado['FORMATO'] = df_concatenado['Fch Emision'].dt.strftime('%Y%m%d')
  
        df_concatenado = df_concatenado.dropna(subset=["FORMATO"])
        
        # Validar columnas clave tras la carga
        validar_columnas(df_concatenado, ["Producto", "FORMATO","Fch Emision"], "Compilado de fchs")

        
        # Validar duplicados en claves principales
        validar_duplicados(df_concatenado, ["Producto", "FORMATO"], "concatenado final")
        
        path_guardado = os.path.join(carpeta_guardado, "Compilado de fchs ult compra.xlsx")
        
        if os.path.exists(path_guardado):
            os.remove(path_guardado)
        df_concatenado.to_excel(path_guardado, index=False)
        logger.info(f'Archivo guardado en: {path_guardado}')
        return {"actualizacion_fchs": path_guardado}
    except Exception as e:
        logger.error(f"Error en el procesamiento de Actualización FCHS: {e}", exc_info=True)
        raise 