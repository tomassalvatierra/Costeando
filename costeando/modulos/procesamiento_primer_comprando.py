import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging
from costeando.utilidades.validaciones import validar_archivo_excel

logger = logging.getLogger(__name__)

def asignar_clasificacion(rotacion):
    if rotacion == 0:
        return 'SIN ROTACION'
    elif 0 < rotacion < 0.11:
        return 'BAJA ROTACION'
    elif rotacion <= 75:
        return 'ROTACION NORMAL'
    else:
        return 'BUENA ROTACION'

def procesar_rotacion(df_ficha):
    
    columnas_necesarias = ["Codigo", "Stock Actual", "Pedidos N+1", "Pedidos N+2", "Pedidos N+3", "Pedidos N+4", "Pedidos N+5", "Stock N+6", "Grupo", "Tipo"]
    
    df_ficha = df_ficha[columnas_necesarias]
    
    df_ficha = df_ficha.drop(df_ficha[(df_ficha["Stock Actual"] == 0) & (df_ficha["Pedidos N+1"] == 0) & (df_ficha["Pedidos N+2"] == 0) & (df_ficha["Pedidos N+3"] == 0) & (df_ficha["Pedidos N+4"] == 0) & (df_ficha["Pedidos N+5"] == 0) & (df_ficha["Stock N+6"] == 0)].index)
    df_ficha = df_ficha.drop(df_ficha[(df_ficha["Grupo"] == 7) | (df_ficha["Grupo"] == 0)].index)
    df_ficha = df_ficha.drop(df_ficha[(df_ficha["Tipo"] == "SV")].index)
    
    Prom = ((df_ficha["Pedidos N+1"] + df_ficha["Pedidos N+2"] + df_ficha["Pedidos N+3"] + df_ficha["Pedidos N+4"] + df_ficha["Pedidos N+5"])/5)
    
    df_ficha = df_ficha.assign(Promedio=Prom.values)
    df_ficha["Promedio"].fillna(0, inplace=True)
    df_ficha["Clasificacion"] = ""
    Rota = df_ficha["Promedio"] / df_ficha["Stock N+6"]
    df_ficha = df_ficha.assign(Rotacion=Rota.values)
    df_ficha.rename(columns={"Rotacion": "% Rotación"}, inplace=True)
    df_ficha['Clasificacion'] = df_ficha['% Rotación'].apply(asignar_clasificacion)
    return df_ficha

def campania_a_absoluta(campania, anio):
    return (anio - 2021) * 18 + campania

def estandarizar_columna_producto(df, nombre_df):
    """
    Renombra la columna 'Producto' a 'Codigo' si existe en el DataFrame.
    Parámetros:
        df (pd.DataFrame): DataFrame a estandarizar.
        nombre_df (str): Nombre del DataFrame para el registro de logs.
    Retorna:
        pd.DataFrame: DataFrame con la columna 'Producto' renombrada a 'Codigo'.
    """
    if 'Producto' in df.columns:
        df = df.rename(columns={'Producto': 'Codigo'})
        logger.debug(f"Columna 'Producto' renombrada a 'Codigo' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    else:
        logger.debug(f"No se encontró la columna 'Producto' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    return df


def actualizar_estado_vencido(df_base_dtos, campania_actual, anio_actual, campania_stock):
    # Crear copia del DataFrame original para no modificarlo
    df_resultado = df_base_dtos.copy()
    df_resultado['anio/campania abs'] = df_resultado.apply(
        lambda row: campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento']), 
        axis=1
    )
    absoluta_actual = campania_a_absoluta(campania_actual, anio_actual)
    
    # =================== GENERAL ===========================================
    mascara_general = df_resultado.apply(
        lambda row: (absoluta_actual - campania_a_absoluta(row['Campania_Otorgamiento'], 
        row['Anio_Otorgamiento'])) > 27,
        axis=1
    )
    df_resultado.loc[mascara_general, 'VENCIDO'] = 'Si'
    df_resultado.loc[mascara_general, 'NOTAS'] = 'Pierde descuento por sobrepasar de 27 campañas(año y medio)'

    # Separar vencidos y no vencidos
    df_vencidos = df_resultado[df_resultado['VENCIDO'] == 'Si']
    df_no_vencidos = df_resultado[df_resultado['VENCIDO'] == 'No']

    # ============= AGOTAMIENTO DE PRODUCTOS TERMINADOS ===================
    campania_limite = int(campania_stock)
    if campania_limite < 1:
        campania_limite += 18
        anio_limite = anio_actual - 1
    else:
        anio_limite = anio_actual
        
    absoluta_limite = campania_a_absoluta(campania_limite, anio_limite)
    
    mascara_terminados = (
        (df_no_vencidos['TIPO-DESCUENTO'] == 'AGOTAMIENTO-PRODUCTO TERMINADO') &
        (df_no_vencidos['Stock Actual'] < 500) &
        (df_no_vencidos['anio/campania abs'] < absoluta_limite)
    )
    
    # Actualizar estado de productos terminados
    df_vencidos_terminados = df_no_vencidos[mascara_terminados].copy()
    df_vencidos_terminados['VENCIDO'] = 'Si'
    df_vencidos_terminados['NOTAS'] = 'Pierde el descuento por no tener stock'
    
    # Actualizar no vencidos
    df_no_vencidos = df_no_vencidos[~mascara_terminados]

    # =================== AGOTAMIENTO DE COMPONENTES ===================
    mascara_componentes = (
        (df_no_vencidos['TIPO-DESCUENTO'] == 'AGOTAMIENTO-COMPONENTES') &
        df_no_vencidos.apply(
            lambda row: (absoluta_actual - campania_a_absoluta(
                row['Campania_Otorgamiento'], 
                row['Anio_Otorgamiento']
            )) > 18,
            axis=1
        )
    )
    
    # Actualizar estado de componentes
    df_vencidos_componentes = df_no_vencidos[mascara_componentes].copy()
    df_vencidos_componentes['VENCIDO'] = 'Si'
    df_vencidos_componentes['NOTAS'] = 'Pierde descuento por sobrepasar de 18 campañas'
    
    # Actualizar no vencidos finales
    df_no_vencidos = df_no_vencidos[~mascara_componentes]

    # Concatenar todos los DataFrames
    df_final = pd.concat([
        df_vencidos,
        df_vencidos_terminados,
        df_vencidos_componentes,
        df_no_vencidos
    ], ignore_index=True)

    # Ordenar el DataFrame final para mantener el orden original
    df_final = df_final.sort_index()
    
    # Eliminar columnas auxiliares
    df_final.drop(columns=['Anio_Otorgamiento', 'Campania_Otorgamiento', 'Stock Actual','anio/campania abs'], inplace=True, errors='ignore')
    
    # Crear DataFrame de no vencidos para poder realizar el merge posteriormente.
    df_no_vencidos = df_final[df_final['VENCIDO'] == 'No'].copy()
    
    # Crear DataFrame de cambios para reportar los productos que perdieron el descuento.
    df_cambios = df_final[df_final['VENCIDO'] == 'Si'].copy()
    #df_cambios = df_cambios.drop_duplicates(subset='Codigo', keep='first')
    
    return df_final, df_cambios

def procesar_descuento(df_calculo_comprando, df_costos_especiales, campaña, año, df_compras):
            
    df_sin_vencidos01 = df_costos_especiales.loc[df_costos_especiales['VENCIDO'] == 'No'].copy()
    df_costos_especiales = df_costos_especiales.loc[df_costos_especiales['VENCIDO'] == 'Si']
    
    df_sin_vencidos01[['Anio_Otorgamiento', 'Campania_Otorgamiento']] = df_sin_vencidos01['APLICA DDE CA:'].str.split('/', expand=True)
    df_sin_vencidos01['Anio_Otorgamiento'] = df_sin_vencidos01['Anio_Otorgamiento'].fillna(0).astype(int)
    df_sin_vencidos01['Campania_Otorgamiento'] = df_sin_vencidos01['Campania_Otorgamiento'].fillna(0).astype(int)
    
    # 1. Primero procesar vencimientos por tiempo/stock
    df_base_descuentos, df_cambios = actualizar_estado_vencido(
        df_sin_vencidos01, 
        int(campaña), 
        int(año), 
        int(campaña) - 5
    )
    
    df_no_vencidos = df_base_descuentos.loc[df_base_descuentos['VENCIDO'] == 'No'].copy()
    df_vencidos = df_base_descuentos.loc[df_base_descuentos['VENCIDO'] == 'Si']
    
    #Crear una mascara para los codigos que tienen compras validad(de fecha no nula) del df_compras y actualiazar el df_no_vencidos y el df_calculo_comprando
    
    # Crear máscara para códigos con compras válidas (fecha no nula) en df_compras
    fechas_validas = pd.to_datetime(df_compras['Fch Emision'], errors='coerce').notna()
    codigos_con_compras = df_compras.loc[fechas_validas, 'Codigo'].unique()
    
    mascara = df_no_vencidos['Codigo'].isin(codigos_con_compras)

    # Actualizar campos VENCIDO y NOTAS en df_no_vencidos
    df_no_vencidos.loc[mascara, 'VENCIDO'] = "Si"
    df_no_vencidos.loc[mascara, 'NOTAS'] = "X OC en CAMPAÑA C"+campaña+"-"+año

    # Actualizar campo % de obsolescencia en df_calculo_comprando
    mascara_calculo = df_calculo_comprando['Codigo'].isin(codigos_con_compras)
    df_calculo_comprando.loc[mascara_calculo, '% de obsolescencia'] = 0
    
    df_final = pd.concat([
        df_vencidos,
        df_no_vencidos
    ], ignore_index=True)
    
    df_no_vencidos = df_final.loc[df_final['VENCIDO'] == 'No'].copy()
    df_cambios = df_final.loc[df_final['VENCIDO'] == 'Si'].copy()
    
    return df_calculo_comprando, df_final,df_no_vencidos,df_cambios

        
def asignacion_campañas(campaña, año):
    if campaña == '01':
        campaña_anterior = '18'
        año_anterior = str(int(año) - 1)
    else:
        campaña_anterior = str(int(campaña) - 1).zfill(2)
        año_anterior = año
    ultimo_digito_año_anterior = año_anterior[-1]
    año_campaña_anterior = ultimo_digito_año_anterior + campaña_anterior
    return campaña_anterior, año_campaña_anterior

def asignar_coeficiente(indice_a, indice_b, row):
    codigo_actualizacion = row['Cod Actualiz']
    if codigo_actualizacion == 'A':
        return indice_a
    elif codigo_actualizacion == 'B':
        return indice_b
    else:
        return None

def calcular_obsolescencia(fecha, row):
    dias_antiguedad = (fecha - row['Ult. Compra']).days
    if dias_antiguedad < 365:
        return 0
    elif 365 <= dias_antiguedad <= 730:
        return 10
    elif 731 <= dias_antiguedad <= 1095:
        return 20
    elif 1096 <= dias_antiguedad <= 1460:
        return 30
    elif 1461 <= dias_antiguedad <= 1825:
        return 40
    elif 1826 <= dias_antiguedad <= 2190:
        return 50
    elif 2191 <= dias_antiguedad < 3650:
        return 50
    elif dias_antiguedad >= 3650:
        return 75

def calcular_costo_sin_descuento(campaña_anterior, row):
    if pd.notna(row['Costo Compra']):
        return row['Costo Compra'] * 1
    else:
        return round(row['Costo sin Descuento C' + campaña_anterior] * row['Coef de Actualizacion'], 2)



def rellenar_valores(df, columnas, valor=0):
    df[columnas] = df[columnas].fillna(valor)
    return df

def calcular_variacion(df, numerador, denominador, nueva_columna, reemplazo_inf='NUEVO'):
    variacion = (df[numerador] / df[denominador]) - 1
    df[nueva_columna] = variacion.replace({np.inf: reemplazo_inf})
    return df

def procesar_primer_comprando(
    campaña, año, indice_a, indice_b, mano_de_obra,
    ruta_maestro, ruta_compras, ruta_stock, ruta_dto_especiales,
    ruta_listado, ruta_calculo_comprando_ant, ruta_ficha, ruta_salida
):
    try:
        logger.info("Iniciando procesamiento puro de Primer Comprando")
        # Validar archivos de entrada
        validar_archivo_excel(ruta_maestro, "maestro")
        validar_archivo_excel(ruta_compras, "compras")
        validar_archivo_excel(ruta_stock, "stock")
        validar_archivo_excel(ruta_dto_especiales, "dto especiales")
        validar_archivo_excel(ruta_listado, "listado")
        validar_archivo_excel(ruta_calculo_comprando_ant, "calculo comprando anterior")
        validar_archivo_excel(ruta_ficha, "ficha RMS")
        
        if not all([campaña, año, indice_a, indice_b, mano_de_obra]):
            raise ValueError('Debe ingresar todos los datos solicitados.')
        if not ruta_salida:
            raise ValueError('Debe indicar una ruta de salida.')
        logger.debug(f"Lectura de archivos de entrada completada para Primer Comprando")
        
        df_maestro = pd.read_excel(ruta_maestro, engine='openpyxl')
        df_compras = pd.read_excel(ruta_compras, engine='openpyxl')
        df_stock = pd.read_excel(ruta_stock, engine='openpyxl')
        df_costos_especiales = pd.read_excel(ruta_dto_especiales, engine='openpyxl')
        df_listado_anterior = pd.read_excel(ruta_listado, engine='openpyxl')
        df_calculo_comprando_anterior = pd.read_excel(ruta_calculo_comprando_ant, engine='openpyxl')
        df_ficha_rms = pd.read_excel(ruta_ficha, engine='openpyxl')
        
        campaña_anterior, año_campaña_anterior = asignacion_campañas(campaña, año)
        
        fecha_ingresada = datetime.now()
        lista_dfs = [
                (df_maestro, 'Maestro'),
                (df_compras, 'Compras'),
                (df_stock, 'Stock'),
                (df_costos_especiales, 'Base Especiales'),
                (df_listado_anterior, 'Listado'),
                (df_calculo_comprando_anterior, 'Comprando Anterior'),
                (df_ficha_rms, 'Ficha RMS')]
            
        # Estandarizar todos los DataFrames en la lista
        lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
        
        # Desempaquetar DataFrames nuevamente
        df_maestro, df_compras, df_stock, df_costos_especiales, df_listado_anterior, df_calculo_comprando_anterior, df_ficha_rms = lista_dfs

        df_calculo_comprando = df_maestro.copy()
        
        df_calculo_comprando = df_calculo_comprando.replace('  /  /    ', '')
        
        df_calculo_comprando['Cod Actualiz'] = df_calculo_comprando['Cod Actualiz'].replace('1', 'A')
        df_calculo_comprando['Cod Actualiz'] = df_calculo_comprando['Cod Actualiz'].replace('2', 'B')
        df_calculo_comprando['Cod Actualiz'] = df_calculo_comprando['Cod Actualiz'].replace(1, 'A')
        df_calculo_comprando['Cod Actualiz'] = df_calculo_comprando['Cod Actualiz'].replace(2, 'B')
        
        df_calculo_comprando['Blq. de Pant'] = df_calculo_comprando['Blq. de Pant'].replace(1, 'Si')
        df_calculo_comprando['Blq. de Pant'] = df_calculo_comprando['Blq. de Pant'].replace(2, 'No')
        df_calculo_comprando['Blq. de Pant'] = df_calculo_comprando['Blq. de Pant'].replace('1', 'Si')
        df_calculo_comprando['Blq. de Pant'] = df_calculo_comprando['Blq. de Pant'].replace('2', 'No')
        
        df_calculo_comprando['¿Atiende Ne?'] = df_calculo_comprando['¿Atiende Ne?'].replace('P', 'Produciendo')
        
        df_calculo_comprando = df_calculo_comprando.drop(df_calculo_comprando[(df_calculo_comprando['Tipo'] == 'GG')| (df_calculo_comprando['Tipo'] == 'GN')| (df_calculo_comprando['Tipo'] == 'GI')| (df_calculo_comprando['Blq. de Pant'] == 'Si')| (df_calculo_comprando['¿Atiende Ne?'] == 'Produciendo')].index)
        
        columns_to_merge = ['ULTCOS', 'Fch Emision', 'OBSERVACIONES COSTOS','RESPUESTA COMPRAS' ,'Campaña','MONEDA','Stock Actual', 'COSTO LISTA ' + año_campaña_anterior, 'Costo sin Descuento C' + campaña_anterior]
        
        data_frames_to_merge = [df_compras, df_compras,df_compras,df_compras,df_compras,df_compras, df_stock, df_listado_anterior, df_calculo_comprando_anterior]
        
        for column, data_frame in zip(columns_to_merge, data_frames_to_merge):
            df_calculo_comprando = pd.merge(df_calculo_comprando, data_frame[['Codigo', column]], how='left', on = 'Codigo')
        
        df_calculo_comprando = df_calculo_comprando.drop_duplicates(subset = 'Codigo', keep = 'first')
        
        df_calculo_comprando['Ult. Compra'] = pd.to_datetime(df_calculo_comprando['Ult. Compra'])
        
        df_calculo_comprando['Coef de Actualizacion'] = df_calculo_comprando.apply(lambda row: asignar_coeficiente(indice_a, indice_b, row), axis=1)
        
        df_calculo_comprando.rename(columns = {'ULTCOS' : 'Costo Compra'}, inplace=True)
        
        df_costos_especiales = pd.merge(df_costos_especiales, df_stock[['Codigo', 'Stock Actual']], how='left') 
        df_costos_especiales['Stock Actual'] = df_costos_especiales['Stock Actual'].fillna(0)
        
        df_calculo_comprando['% de obsolescencia'] = df_calculo_comprando.apply(lambda row: calcular_obsolescencia(fecha_ingresada,row) if  (row['Tipo'] == 'PA' or row['Tipo'] == 'PD' or row['Tipo'] == 'PC' ) and (row['Grupo'] == 1 or row['Grupo'] == 2 or row['Grupo'] == 3 or row['Grupo'] == 4 or row['Grupo'] == 6)  else None,axis = 1)
    
        # Reemplazar las llamadas actuales por:
        df_calculo_comprando, df_costos_especiales, df_no_vencidos,df_cambios = procesar_descuento(
            df_calculo_comprando, 
            df_costos_especiales, 
            campaña, 
            año, 
            df_compras
        )     
   
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_no_vencidos[['Codigo', 'DESCUENTO ESPECIAL']], how='left', on='Codigo')   
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_no_vencidos[['Codigo', 'APLICA DDE CA:']], how='left', on='Codigo')   
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_costos_especiales[['Codigo', 'ROYALTY']], how='left', on='Codigo')  
        
        #Ordenar el df_calculo_comprando por Codigo y APLICA DDE CA: desde la Z a la A
        df_calculo_comprando = df_calculo_comprando.sort_values(by=['Codigo', 'APLICA DDE CA:'], ascending=[True, False])
        
        df_calculo_comprando.drop_duplicates(subset = 'Codigo', keep = 'first', inplace=True)
        
        codigos_a_actualizar = ['MOD0806', 'MOD0807', 'MOD0808']
        
        for codigo in codigos_a_actualizar:
            df_calculo_comprando.loc[df_calculo_comprando['Codigo'] == codigo, 'Costo Compra'] = mano_de_obra
        
        df_calculo_comprando = calcular_variacion(
            df_calculo_comprando, 
            numerador='Costo Compra', 
            denominador='Costo sin Descuento C' + campaña_anterior, 
            nueva_columna='% var Compra VS Costo sin dto C' + campaña_anterior)
        
        df_calculo_comprando = calcular_variacion(
            df_calculo_comprando, 
            numerador='Costo Compra', 
            denominador='COSTO LISTA ' + año_campaña_anterior, 
            nueva_columna='%var Compra vs COSTO LISTA C' + campaña_anterior)
        
        df_calculo_comprando.loc[df_calculo_comprando['Costo Compra'].notnull(), 'Coef de Actualizacion'] = 1

        df_calculo_comprando['Costo sin Descuento C' + campaña] = df_calculo_comprando.apply(lambda row: calcular_costo_sin_descuento(campaña_anterior, row), axis=1)
        
        columnas_a_rellenar = [
            'DESCUENTO ESPECIAL',
            '% de obsolescencia', 
            'ROYALTY', 
            'Costo sin Descuento C' + campaña, 
            'Costo sin Descuento C' + campaña_anterior]
        
        df_calculo_comprando = rellenar_valores(df_calculo_comprando, columnas_a_rellenar)
        
        df_calculo_comprando.rename(columns = {'MONEDA' : 'MONEDA/COMPRAS'}, inplace=True)         
        
        df_rotacion = procesar_rotacion(df_ficha_rms)
        
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_rotacion[['Codigo', 'Clasificacion']], how='left', on='Codigo')  
        
        if not os.path.exists(ruta_salida):
            os.makedirs(ruta_salida)
        
        path_rotacion = os.path.join(ruta_salida, f'Rotacion_calculada_C{campaña}_{año}.xlsx')
        path_base_descuentos = os.path.join(ruta_salida, f'Base_Descuentos_Especiales_1era_Etapa_C{campaña}_{año}.xlsx')
        path_cambios = os.path.join(ruta_salida, f'Cambios_realizados_en_la_base_C{campaña}_{año}.xlsx')
        path_calculo_comprando = os.path.join(ruta_salida, f'Calculo_Comprando_{campaña}_{año}.xlsx')
        
        df_rotacion.to_excel(path_rotacion, index=False, engine='openpyxl')
        df_costos_especiales.to_excel(path_base_descuentos, index=False, engine='openpyxl')
        df_cambios.to_excel(path_cambios, index=False, engine='openpyxl')
        df_calculo_comprando.to_excel(path_calculo_comprando, index=False, engine='openpyxl')
        
        logger.info(f"Procesamiento de Primer Comprando finalizado correctamente. Archivos guardados en: {ruta_salida}")
        return {
            'calculo_comprando': path_calculo_comprando,
            'rotacion': path_rotacion,
            'base_descuentos': path_base_descuentos,
            'cambios': path_cambios,
        }
    except Exception as e:
        logger.error(f"Error en el procesamiento de Primer Comprando: {e}", exc_info=True)
        raise 