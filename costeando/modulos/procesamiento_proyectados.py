import pandas as pd
import logging
from typing import Dict
import os
from datetime import datetime
from costeando.utilidades.validaciones import validar_archivo_excel, validar_columnas

logger = logging.getLogger(__name__)

def obtener_coeficiente(df_coef_pivot, camp, variable):
    resultado = 1 + df_coef_pivot[(df_coef_pivot['CAMPAÑA-AÑO'] == camp) & (df_coef_pivot['VARIABLE'] == variable)]['Coeficiente']
    if not resultado.empty:
        return resultado.values[0]
    else:
        return 0

def generar_campanas(campana_inicial, anio_inicial):
    campanas = []
    mc_campanas = []
    campana_num = int(campana_inicial[-2:]) + 1
    anio = int(anio_inicial)
    for _ in range(10):
        if campana_num > 18:
            campana_num = 1
            anio += 1
        campanas.append(f'C{str(campana_num).zfill(2)}-{anio}')
        mc_campanas.append(f'MC{str(campana_num).zfill(2)}-{anio}')
        campana_num += 1
    return campanas, mc_campanas

def procesar_proyectados_puro(
    ruta_lista: str,
    ruta_coef: str,
    camp_inicial: str,
    anio_inicial: str,
    carpeta_guardado: str
) -> Dict[str, str]:
    """
    Procesa el módulo Proyectados y guarda los archivos generados en la carpeta indicada.
    Devuelve un diccionario con los paths de los archivos generados.
    """
    try:
        logger.info("Iniciando procesamiento puro de Proyectados")
        df_lista = pd.read_excel(ruta_lista, engine='openpyxl')
        coef_df = pd.read_excel(ruta_coef, engine='openpyxl')
        validar_archivo_excel(ruta_lista, "Listado de costos")
        validar_archivo_excel(ruta_coef, "Tabla de coeficientes")
        validar_columnas(df_lista, ["VARIABLE", "LLEVA CF"], "Listado de costos")
        
        if 'Producto' in df_lista.columns:
            df_lista = df_lista.rename(columns={'Producto': 'Codigo'})
            logger.debug("Columna 'Producto' renombrada a 'Codigo' en listado de costos.")
            
        anio_camp = anio_inicial[3] + camp_inicial
        df_lista['Codigo'] = df_lista['Codigo'].astype(str).str.strip()
        df_listado_proyectado = df_lista.copy()
        
        columnas_fijas = list(df_listado_proyectado.columns)
        futuras_campanas, futuras_mc_campanas = generar_campanas(camp_inicial, anio_inicial)
        nuevas_columnas_data = {columna: [None] * len(df_listado_proyectado) for columna in futuras_campanas}
        df_listado_proyectado = df_listado_proyectado.assign(**nuevas_columnas_data)
        df_coef_pivot = coef_df.melt(id_vars=['CAMPAÑA-AÑO'], var_name='VARIABLE', value_name='Coeficiente')
        campanas_anio_indice = df_listado_proyectado.columns[-10:]
        
        for camp in campanas_anio_indice:
            df_listado_proyectado[camp] = df_listado_proyectado.apply(lambda row: obtener_coeficiente(df_coef_pivot, camp, row['VARIABLE']), axis=1)
        
        for i, camp in enumerate(campanas_anio_indice):
            if i == 0:
                df_listado_proyectado["M" + camp] = round(df_listado_proyectado['COSTO LISTA '+ anio_camp] * (df_listado_proyectado[camp]),2)
            else:
                df_listado_proyectado["M" + camp] = round(df_listado_proyectado['M' + campanas_anio_indice[i-1]] * (df_listado_proyectado[camp]),2)
        
        columnas_intercaladas = []
        for coef, costo in zip(futuras_campanas, futuras_mc_campanas):
            columnas_intercaladas.append(coef)
            columnas_intercaladas.append(costo)
        
        nueva_orden_columnas = columnas_fijas + columnas_intercaladas
        
        df_listado_proyectado = df_listado_proyectado.reindex(columns=nueva_orden_columnas)
        df_listado_proyectado['LLEVA CF'] = df_listado_proyectado['LLEVA CF'].replace(0, 'No')
        df_listado_proyectado_comercial = df_listado_proyectado.copy()
        
        condicion = ((df_listado_proyectado_comercial['Tipo'] == 'GG') | 
                     (df_listado_proyectado_comercial['Tipo'] == 'MO') | 
                     (df_listado_proyectado_comercial['Tipo'] == 'SV') |
                     (df_listado_proyectado_comercial['Estado'] == 'INA') | 
                     (df_listado_proyectado_comercial['COSTO LISTA ' + anio_camp] == 0))
        
        df_listado_proyectado_comercial = df_listado_proyectado_comercial[~condicion]
        df_listado_proyectado_comercial = df_listado_proyectado_comercial[df_listado_proyectado_comercial['Codigo'].astype(str).str.len() <= 5]
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        path_proyectado = os.path.join(carpeta_guardado, f"{fecha_hoy} Costos Proyectados C{camp_inicial}_{anio_inicial}.xlsx")
        path_proyectado_comercial = os.path.join(carpeta_guardado, f"{fecha_hoy} Costos Proyectados C{camp_inicial}_{anio_inicial} PARA COMERCIAL.xlsx")
        df_listado_proyectado.to_excel(path_proyectado, index=False)
        df_listado_proyectado_comercial.to_excel(path_proyectado_comercial, index=False)
        logger.info(f"Archivos guardados en: {carpeta_guardado}")
        return {
            'proyectado': path_proyectado,
            'proyectado_comercial': path_proyectado_comercial
        }
    except Exception as e:
        logger.error(f"Error en el procesamiento de Proyectados: {e}", exc_info=True)
        raise 
