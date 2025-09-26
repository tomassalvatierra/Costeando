import pandas as pd
import numpy as np
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime

from costeando.utilidades.validaciones import validar_archivo_excel

logger = logging.getLogger(__name__)

def estandarizar_columna_producto(df: pd.DataFrame, nombre_df: str) -> pd.DataFrame:
    if 'Producto' in df.columns:
        df = df.rename(columns={'Producto': 'Codigo'})
        logger.debug(f"Columna 'Producto' renombrada a 'Codigo' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    else:
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    return df

def incorporar_nuevos_dtos(df_especiales: pd.DataFrame, df_importador: pd.DataFrame, df_productos: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    nuevos_codigos = df_importador['Codigo'].tolist()
    
    df_especiales.loc[df_especiales['Codigo'].isin(nuevos_codigos), 'VENCIDO'] = 'Si'
    df_especiales.loc[df_especiales['Codigo'].isin(nuevos_codigos), 'NOTAS'] = 'Vencido, ingreso un nuevo descuento'
    
    dict_descuentos = dict(zip(
        df_importador['Codigo'], 
        zip(df_importador['DESCUENTO ESPECIAL'], df_importador['APLICA DDE CA:'])
    ))
    
    mapeo = df_productos['Codigo'].map(dict_descuentos).apply(lambda x: x if isinstance(x, tuple) else (None, None))
    
    nuevos_valores = mapeo.apply(pd.Series)
    nuevos_valores.columns = ['DESCUENTO ESPECIAL', 'APLICA DDE CA:']
    
    # Asegurarse de que nuevos_valores sea DataFrame y tenga el mismo índice
    nuevos_valores = nuevos_valores.set_index(df_productos.index)
    df_productos[['DESCUENTO ESPECIAL', 'APLICA DDE CA:']] = df_productos[['DESCUENTO ESPECIAL', 'APLICA DDE CA:']].combine_first(nuevos_valores)
    df_base_especiales_concatenado = pd.concat([df_especiales, df_importador], ignore_index=True)
    return df_base_especiales_concatenado, df_productos

def procesar_segundo_comprando(
    ruta_comprando: str,
    ruta_costos_especiales: str,
    ruta_importador_descuentos: Optional[str],
    campaña: str,
    año: str,
    fecha_compras_inicio: str,
    fecha_compras_final: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    try:
        logger.info("Iniciando procesamiento puro de segundo comprando")
        campaña = campaña.zfill(2)
        año_campaña = año[-1] + campaña
        desde_desc_especiales = f"{año}/{campaña.zfill(2)}"
        campaña_año = f'CAMP-{campaña}/{str(int(año) % 100)}'
        fecha_inicio = pd.to_datetime(fecha_compras_inicio, format='%d/%m/%Y')
        fecha_final = pd.to_datetime(fecha_compras_final, format='%d/%m/%Y')

        validar_archivo_excel(ruta_comprando, "Comprando")
        validar_archivo_excel(ruta_costos_especiales, "Base Especiales")

        df_costos_especiales = pd.read_excel(ruta_costos_especiales, engine='openpyxl')
        df_calculo_comprando = pd.read_excel(ruta_comprando, engine='openpyxl')
        logger.debug(f"Archivos de entrada cargados: Comprando({len(df_calculo_comprando)}), Base Especiales({len(df_costos_especiales)})")

        if ruta_importador_descuentos:
            df_importador_descuentos = pd.read_excel(ruta_importador_descuentos, engine='openpyxl')
            lista_dfs = [
                (df_calculo_comprando, 'Comprando'),
                (df_costos_especiales, 'Base Descuentos Especiales'),
                (df_importador_descuentos, 'Importador Descuentos Especiales')]
            
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]       
            df_calculo_comprando, df_costos_especiales, df_importador_descuentos = lista_dfs
            df_costos_especiales, df_calculo_comprando = incorporar_nuevos_dtos(df_costos_especiales, df_importador_descuentos, df_calculo_comprando)
        else:
            lista_dfs = [
                (df_calculo_comprando, 'Comprando'),
                (df_costos_especiales, 'Base Descuentos Especiales')]
            lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
            df_calculo_comprando, df_costos_especiales = lista_dfs

        df_calculo_comprando.sort_values(by=['Codigo', 'APLICA DDE CA:'], ascending=[True,False], inplace=True)
        df_calculo_comprando.drop_duplicates(subset=['Codigo'], keep='first', inplace=True)
        df_calculo_comprando.reset_index(drop=True, inplace=True)

        df_calculo_comprando['% sumatoria descuentos'] = (
            df_calculo_comprando['% de obsolescencia'].fillna(0) +
            df_calculo_comprando['DESCUENTO ESPECIAL'].fillna(0) +
            df_calculo_comprando['ROYALTY'].fillna(0)
        ).round(2)

        mascara_superado_75 = df_calculo_comprando['% sumatoria descuentos'] > 75
        exceso = df_calculo_comprando.loc[mascara_superado_75, '% sumatoria descuentos'] - 75
        
        df_calculo_comprando.loc[mascara_superado_75, 'DESCUENTO ESPECIAL'] = (
            df_calculo_comprando.loc[mascara_superado_75, 'DESCUENTO ESPECIAL'] - exceso
        ).clip(lower=0)
        
        codigos_ajustados = df_calculo_comprando.loc[mascara_superado_75, 'Codigo'].unique()
        df_costos_especiales.loc[df_costos_especiales['Codigo'].isin(codigos_ajustados), 'VENCIDO'] = "Si"
        
        nuevos_descuentos = df_calculo_comprando.loc[mascara_superado_75, ['Codigo', 'DESCUENTO ESPECIAL']].copy()
        nuevos_descuentos['APLICA DDE CA:'] = desde_desc_especiales
        nuevos_descuentos['VENCIDO'] = "No"
        nuevos_descuentos['NOTAS'] = "Descuento ajustado, el anterior superaba el 75%"
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_calculo_comprando[["Codigo","Descripcion"]], how='left')
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_calculo_comprando[["Codigo","¿Atiende Ne?"]], how='left')
        nuevos_descuentos = pd.merge(nuevos_descuentos, df_costos_especiales[["Codigo","TIPO-DESCUENTO"]], how='left')
        nuevos_descuentos = nuevos_descuentos.rename(columns={'¿Atiende Ne?': 'ATIENDE NE?'})
        nuevos_descuentos.drop_duplicates(inplace=True)
        
        df_costos_especiales = pd.concat([df_costos_especiales, nuevos_descuentos], ignore_index=True)
        
        df_calculo_comprando['% sumatoria descuentos'] = (
           df_calculo_comprando['% de obsolescencia'].fillna(0) +
           df_calculo_comprando['DESCUENTO ESPECIAL'].fillna(0) +
           df_calculo_comprando['ROYALTY'].fillna(0)).round(2)
        
        df_calculo_comprando.loc[df_calculo_comprando['DESCUENTO ESPECIAL'] == 0, 'APLICA DDE CA:'] = np.nan
        df_costos_especiales['DESCUENTO ESPECIAL'] = df_costos_especiales['DESCUENTO ESPECIAL'].round(2)
        df_calculo_comprando['DESCUENTO ESPECIAL'] = df_calculo_comprando['DESCUENTO ESPECIAL'].round(2)
        
        costo_importador = round(df_calculo_comprando['Costo sin Descuento C' + campaña] * (1 - (df_calculo_comprando['% sumatoria descuentos']/100)), 2)
        
        df_calculo_comprando = df_calculo_comprando.assign(costo_p_importador = costo_importador.values)
        df_calculo_comprando.rename(columns = {'costo_p_importador' : 'Costo 1er Importador'}, inplace = True)
        df_calculo_comprando['Costo 1er Importador'].fillna(0, inplace=True)
        
        df_importador = df_calculo_comprando.loc[:,['Codigo','Costo 1er Importador']].copy()
        df_importador['Columna3'] = '27251293061'
        df_importador['Columna4'] = año_campaña
        df_importador['Columna5'] = campaña_año
        df_importador['Columna6'] = fecha_inicio
        df_importador['Columna7'] = fecha_final
        df_importador[['Columna8', 'Columna9']] = '001'
        df_importador['Columna10'] = '99999999'
        df_importador['Columna11'] = '31/12/1999'
        df_importador['Costo 1er Importador'] = df_importador['Costo 1er Importador'].round(2).astype(str)
        
        df_importador = df_importador.reset_index(drop=True)

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        # Guardar archivos
        path_comprando = f'{carpeta_guardado}/{fecha_hoy} Calculo de Comprando {año} C{campaña} 2da Etapa.xlsx'
        path_especiales = f'{carpeta_guardado}/{fecha_hoy} Descuentos Especiales - Base de Datos - 2da Etapa C{campaña} {año}.xlsx'
        path_importador = f'{carpeta_guardado}/{fecha_hoy} Importador C{campaña} {año}.xlsx'
        
        df_calculo_comprando.to_excel(path_comprando, sheet_name='Calculo Comprando', index=False)
        df_costos_especiales.to_excel(path_especiales, sheet_name='Descuentos Proce', index=False)
        df_importador.to_excel(path_importador, sheet_name='Importador', index=False)
        
        logger.info(f"Archivos guardados en: {carpeta_guardado}")
        return {
            'comprando': path_comprando,
            'especiales': path_especiales,
            'importador': path_importador
        }
    except Exception as e:
        logger.error(f"Error en el procesamiento de Segundo Comprando: {e}", exc_info=True)
        raise 