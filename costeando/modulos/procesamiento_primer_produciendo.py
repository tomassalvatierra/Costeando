import pandas as pd
import os
from datetime import datetime
import logging
from costeando.utilidades.func_faltante_cotizacion import asignar_faltantes_cotizacion
from costeando.utilidades.validaciones import validar_archivo_excel
from costeando.utilidades.validaciones import validar_columnas

logger = logging.getLogger(__name__)

def campania_a_absoluta(campania, anio):
    return (anio - 2021) * 18 + campania

def actualizar_estado_vencido(df_base_dtos, campania_actual, anio_actual, campania_stock):
    logger.info('Actualizando estado vencido')
    
    df_base_dtos['anio/campania abs'] = df_base_dtos.apply(lambda row: campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento']), axis=1)
    absoluta_actual = campania_a_absoluta(campania_actual, anio_actual)
    
    if campania_stock is not None:
        try:
            campania_limite = int(campania_stock)
            if campania_limite < 1:
                campania_limite += 18
                anio_limite = anio_actual - 1
            else:
                anio_limite = anio_actual
            absoluta_limite = campania_a_absoluta(campania_limite, anio_limite)
            es_descuento_terminado = df_base_dtos['TIPO-DESCUENTO'] == 'AGOTAMIENTO-PRODUCTO TERMINADO'
            stock_bajo = df_base_dtos['Stock Actual'] < 500
            descuento_vencido = df_base_dtos['anio/campania abs'] < absoluta_limite
            mascara_terminados = es_descuento_terminado & stock_bajo & descuento_vencido
            df_base_dtos.loc[mascara_terminados, 'VENCIDO'] = 'Si'
            df_base_dtos.loc[mascara_terminados, 'NOTAS'] = 'Pierde el descuento por no tener stock'
        except ValueError:
            logger.info("Error: campania_stock no es un número válido.")
    
    mascara_general = df_base_dtos.apply(
        lambda row: (absoluta_actual - campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento'])) > 27,
        axis=1)
    
    df_base_dtos.loc[mascara_general, 'VENCIDO'] = 'Si'
    df_base_dtos.loc[mascara_general, 'NOTAS'] = 'Pierde descuento por sobrepasar de 27 campañas(año y medio)'
    
    mascara_componentes = (df_base_dtos['TIPO-DESCUENTO'] == 'AGOTAMIENTO-COMPONENTES') & \
        df_base_dtos.apply(
        lambda row: (absoluta_actual - campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento'])) > 18,
        axis=1)
    
    df_base_dtos.loc[mascara_componentes, 'VENCIDO'] = 'Si'
    df_base_dtos.loc[mascara_componentes, 'NOTAS'] = 'Pierde descuento por sobrepasar de 18 campañas'
    df_base_dtos.drop(columns=['Anio_Otorgamiento', 'Campania_Otorgamiento', 'Stock Actual','anio/campania abs'], inplace=True, errors='ignore')
    
    df_no_vencidos = df_base_dtos.copy()
    df_no_vencidos = df_no_vencidos.loc[df_no_vencidos['VENCIDO'] == 'No']
    
    cambios = (df_base_dtos["NOTAS"] == "Pierde el descuento por no tener stock") | (df_base_dtos["NOTAS"] == "Pierde descuento por sobrepasar de 27 campañas(año y medio)") | (df_base_dtos["NOTAS"] == "Pierde descuento por sobrepasar de 18 campañas")
    df_cambios = df_base_dtos.loc[cambios]
    return df_base_dtos, df_no_vencidos, df_cambios

def estandarizar_columna_producto(df, nombre_df):
    if 'Producto' in df.columns:
        df = df.rename(columns={'Producto': 'Codigo'})
        logger.debug(f"Columna 'Producto' renombrada a 'Codigo' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    else:
        logger.debug(f"No se encontró la columna 'Producto' en {nombre_df}.")
        df['Codigo'] = df['Codigo'].astype(str).str.strip()
    return df

def calcular_obsolescencia(fecha, row):
    if pd.isna(row['Ult. Compra']):
        return 0
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

def calcular_costo_sin_descuento(row, df):
    if pd.isna(row["LLEVA CF"]):
        if (row["Grupo"] == 1 or row["Grupo"] == 5) and (row["Tipo"] == "PA" or row["Tipo"] == "PC"):
            lleva_cf = "Si"
            df.at[row.name, 'LLEVA CF'] = 'Si'
        else:
            lleva_cf = "No"
            df.at[row.name, 'LLEVA CF'] = 'No'
    else:
        lleva_cf = row["LLEVA CF"]
    if lleva_cf == "Si":
        return round(row["Costo Producción"] / 0.84, 2)
    else:
        return round(row["Costo Producción"], 2)

def procesar_primer_produciendo(
    campaña_actual, año_actual,
    ruta_produciendo_anterior, ruta_maestro_produciendo, ruta_stock,
    ruta_descuentos_especiales, ruta_rotacion, ruta_estructuras, ruta_salida
):
    try:
        logger.info("Iniciando procesamiento puro de Primer Produciendo")
        # Validar archivos de entrada
        validar_archivo_excel(ruta_produciendo_anterior, "produciendo anterior")
        validar_archivo_excel(ruta_maestro_produciendo, "maestro produciendo")
        validar_archivo_excel(ruta_stock, "stock")
        validar_archivo_excel(ruta_descuentos_especiales, "descuentos especiales")
        validar_archivo_excel(ruta_rotacion, "rotacion")
        validar_archivo_excel(ruta_estructuras, "estructuras")
        if ruta_estructuras:
            validar_archivo_excel(ruta_estructuras, "estructuras")
        if not all([campaña_actual, año_actual]):
            raise ValueError('Debe ingresar todos los datos solicitados.')
        if not ruta_salida:
            raise ValueError('Debe indicar una ruta de salida.')
        logger.debug("Archivos de entrada validados correctamente para Primer Produciendo.")
        fecha_actual = datetime.now()
        campaña_stock = int(campaña_actual) - 5
        
        # Cargar archivos
        df_produciendo_anterior = pd.read_excel(ruta_produciendo_anterior, engine='openpyxl')
        df_maestro_produciendo = pd.read_excel(ruta_maestro_produciendo, engine='openpyxl')
        df_stock = pd.read_excel(ruta_stock, engine='openpyxl')
        df_descuentos_especiales = pd.read_excel(ruta_descuentos_especiales, engine='openpyxl')
        df_rotacion = pd.read_excel(ruta_rotacion, engine='openpyxl')
        
        # Estandarizar
        lista_dfs = [
            (df_produciendo_anterior, 'Produciendo anterior'),
            (df_maestro_produciendo, 'Maestro produciendo'),
            (df_stock, 'Stock'),
            (df_descuentos_especiales, 'Base descuentos especiales'),
            (df_rotacion, 'Rotacion')
        ]
        lista_dfs = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
        
        df_produciendo_anterior, df_maestro_produciendo, df_stock, df_descuentos_especiales, df_rotacion = lista_dfs
        validar_columnas(df_stock, ['Codigo','Stock Actual'], 'Stock')
        
        df_maestro_produciendo.rename(columns={"Costo Estand": "Costo Producción"}, inplace=True)

        df_produciendo = df_maestro_produciendo.copy()
        
        df_produciendo = df_produciendo.replace("  /  /    ", "")
        
        df_produciendo['Ult. Compra'] = pd.to_datetime(df_produciendo['Ult. Compra'], errors='coerce')
        
        df_produciendo["Blq. de Pant"] = df_produciendo["Blq. de Pant"].replace(1, 'Si')
        df_produciendo["Blq. de Pant"] = df_produciendo["Blq. de Pant"].replace(2, 'No')
        df_produciendo["Blq. de Pant"] = df_produciendo["Blq. de Pant"].replace('1', 'Si')
        df_produciendo["Blq. de Pant"] = df_produciendo["Blq. de Pant"].replace('2', 'No')
        df_produciendo["¿Atiende Ne?"] = df_produciendo["¿Atiende Ne?"].replace('C', 'Comprando')
        
        eliminaciones = (df_produciendo["Tipo"].isin(["GG", "GN", "GI"])) | \
               (df_produciendo["Blq. de Pant"] == "Si") | \
               (df_produciendo["¿Atiende Ne?"] == "Comprando")
        
        df_produciendo = df_produciendo[~eliminaciones]
        columnas_a_agregar = ['LLEVA CF', 'Revision de tipo',"Stock Actual", "Clasificacion"]
        df_para_agregar_col = [df_produciendo_anterior, df_produciendo_anterior, df_stock, df_rotacion]
        
        for column, data_frame in zip(columnas_a_agregar, df_para_agregar_col):
            if data_frame is not None and column in data_frame.columns:
                df_produciendo = pd.merge(df_produciendo, data_frame[["Codigo", column]], how="left", on="Codigo")
        
        df_produciendo = df_produciendo.drop_duplicates(subset="Codigo", keep="first")
        df_produciendo["Costo sin Descuento C" + str(campaña_actual)] = df_produciendo.apply(lambda row: calcular_costo_sin_descuento(row, df_produciendo), axis=1)
        df_produciendo['% de obsolescencia'] = df_produciendo.apply(lambda row: calcular_obsolescencia(fecha_actual, row) if (row['Tipo'] == "PA" or row['Tipo'] == "PD" or row['Tipo'] == 'PC' ) and (row['Grupo'] == 1 or row['Grupo'] == 2 or row['Grupo'] == 3 or row['Grupo'] == 4 or row['Grupo'] == 6)  else None,axis = 1)            
        
        #Analisis de descuentos
        df_sin_vencidos = df_descuentos_especiales.copy()
        if 'VENCIDO' in df_sin_vencidos.columns:
            df_sin_vencidos = df_sin_vencidos[df_sin_vencidos['VENCIDO'] != 'Si']
        if 'VENCIDO' in df_descuentos_especiales.columns:
            df_descuentos_especiales = df_descuentos_especiales[df_descuentos_especiales['VENCIDO'] != 'No']
        if "APLICA DDE CA:" in df_sin_vencidos.columns:
            split_aplica = df_sin_vencidos["APLICA DDE CA:"].str.split("/", expand=True)
            df_sin_vencidos["Anio_Otorgamiento"] = split_aplica[0].fillna(0).astype(int)
            df_sin_vencidos["Campania_Otorgamiento"] = split_aplica[1].fillna(0).astype(int)
        if 'Stock Actual' in df_stock.columns:
            df_sin_vencidos = pd.merge(df_sin_vencidos, df_stock[['Codigo', 'Stock Actual']], how='left', on='Codigo') 
            df_sin_vencidos['Stock Actual'] = df_sin_vencidos['Stock Actual'].fillna(0)
        
        df_sin_vencidos, df_no_vencidos, df_cambios = actualizar_estado_vencido(
            df_sin_vencidos, 
            int(campaña_actual), 
            int(año_actual), 
            campaña_stock)
        
        df_descuentos_especiales = pd.concat([df_descuentos_especiales, df_sin_vencidos], ignore_index=True)
        
        if df_no_vencidos is not None and 'DESCUENTO ESPECIAL' in df_no_vencidos.columns:
            df_produciendo = pd.merge(df_produciendo, df_no_vencidos[["Codigo", "DESCUENTO ESPECIAL"]], how="left", on="Codigo")
        
        if df_no_vencidos is not None and 'APLICA DDE CA:' in df_no_vencidos.columns:
            df_produciendo = pd.merge(df_produciendo, df_no_vencidos[["Codigo", "APLICA DDE CA:"]], how="left", on="Codigo")
        
        if 'ROYALTY' in df_descuentos_especiales.columns:
            df_produciendo = pd.merge(df_produciendo, df_descuentos_especiales[["Codigo", "ROYALTY"]], how="left", on="Codigo")
        df_produciendo = df_produciendo.drop_duplicates(subset="Codigo", keep='first')
        
        if ruta_estructuras is not None:
            df_produciendo = asignar_faltantes_cotizacion(df_produciendo, df_maestro_produciendo, ruta_estructuras)
            if 'Descripcion' in df_maestro_produciendo.columns:
                df_maestro_produciendo.rename(columns = {'Descripcion': 'DESCRIPCION COMP', 'Codigo' : 'COMPONENTE FALTANTE'}, inplace = True)
                if 'COMPONENTE FALTANTE' in df_produciendo.columns:
                    df_produciendo["COMPONENTE FALTANTE"] = df_produciendo["COMPONENTE FALTANTE"].astype(str).str.strip()
                    df_produciendo = pd.merge(df_produciendo, df_maestro_produciendo[['COMPONENTE FALTANTE', 'DESCRIPCION COMP']], how='left', on='COMPONENTE FALTANTE')
        
        # Guardar archivos
        if not os.path.exists(ruta_salida):
            os.makedirs(ruta_salida)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        path_produciendo = os.path.join(ruta_salida, f'{fecha_hoy} Produciendo-Primera Etapa C{campaña_actual}_{año_actual}.xlsx')
        path_base_descuentos = os.path.join(ruta_salida, f'{fecha_hoy} Base Descuentos Especiales-Primera Etapa C{campaña_actual}_{año_actual}.xlsx')
        path_cambios = os.path.join(ruta_salida, f'{fecha_hoy} Cambios realizado en la base-Primera Etapa C{campaña_actual}_{año_actual}.xlsx')
        df_produciendo.to_excel(path_produciendo, index=False, engine='openpyxl')
        df_descuentos_especiales.to_excel(path_base_descuentos, index=False, engine='openpyxl')
        df_cambios.to_excel(path_cambios, index=False, engine='openpyxl')
        logger.info(f"Procesamiento de Primer Produciendo finalizado correctamente. Archivos guardados en: {ruta_salida}")
        return {
            'produciendo': path_produciendo,
            'base_descuentos': path_base_descuentos,
            'cambios': path_cambios
        }
    except Exception as e:
        logger.error(f"Error en el procesamiento de Primer Produciendo: {e}", exc_info=True)
        raise 