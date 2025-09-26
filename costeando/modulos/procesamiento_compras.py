import pandas as pd
import numpy as np
import logging
from typing import Dict
from datetime import datetime

from costeando.utilidades.validaciones import validar_archivo_excel

logger = logging.getLogger(__name__)

def clasificacion_compras(row):
    try:
        tipo = row['Tipo']
        moneda = row['MONEDA']
        notas = row['Notas']
        precio_unitario = row['Prc.Unitario']
    except KeyError as e:
        return f"Error: Falta la columna {e}"
    if pd.isnull(notas):
        notas = 0
    if tipo == "Normal":
        return "Normal"
    elif tipo == "Excedente" and moneda == "Peso":
        if notas == 0:
            return "Excedente - Pesos"
        else:
            return "Pesificada"
    elif tipo == "Excedente" and moneda == "Dolar":
        if notas == 0:
            return "Excedente - Dolar"
        else:
            try:
                resultado = notas / precio_unitario
                if 1.8 <= resultado <= 2.4:
                    return "Sufacturacion - Dolar"
                elif 0.7 <= resultado <= 1.3:
                    return "Excedente - Dolar"
            except ZeroDivisionError:
                return "Error: Precio Unitario es 0"
    return "Otro"

def eliminar_productos_no_deseados(df, columnas, palabras_clave):
    for col in columnas:
        for palabra in palabras_clave:
            df = df[~df[col].str.contains(palabra, case=False, na=False)]
    return df

def contador_duplicados(df, indice, finalizador_de_bucle):
    cant_duplicados_funcion = 1
    while True:
        if indice != finalizador_de_bucle-1:
            if df["Producto"][indice] == df["Producto"][indice + 1]:
                cant_duplicados_funcion = cant_duplicados_funcion + 1
                indice = indice + 1
            else:
                variable_duplicada = cant_duplicados_funcion
                break
        else:
            variable_duplicada = cant_duplicados_funcion
            break
    return variable_duplicada

def procesar_compras_puro(ruta_compras: str, dolar: float, carpeta_guardado: str) -> Dict[str, str]:
    """
    Procesa el archivo de compras y guarda el archivo generado en la carpeta indicada.
    Devuelve un diccionario con el path del archivo generado.
    """
    try:
        validar_archivo_excel(ruta_compras,"Compras")
        logger.info("Iniciando procesamiento puro de compras")
        compras_originales = pd.read_excel(ruta_compras, engine = "openpyxl")
        df_compras = compras_originales.copy()
        logger.debug(f"Filas originales: {len(df_compras)}")
        df_compras = df_compras.loc[df_compras["Resid. Elim."] != "S", :]
        df_compras["Producto"] = df_compras["Producto"].astype(str).str.strip()
        try:
            df_compras = eliminar_productos_no_deseados(
                df_compras, ['Producto'],['MAT', 'GAS', 'BSUSO', 'FLE', 'HON', 'SER'])
        except Exception as e:
            logger.info(f"No existen productos a eliminar o error: {e}")
        df_compras = df_compras[df_compras['Observacion'].apply(lambda x: 'RECHAZO' not in str(x).upper())]
        df_compras.Notas = df_compras.Notas.replace({'.' : ","})
        df_compras['Notas'] = pd.to_numeric(df_compras['Notas'], errors='coerce')
        df_compras['Tipo-Costos'] = df_compras.apply(clasificacion_compras, axis=1)
        df_compras = df_compras[~df_compras["Tipo-Costos"].isin(["Excedente - Pesos", "Sufacturacion - Dolar", "Excedente - Dolar"])]
        df_compras.loc[df_compras['Notas'].notna(), 'Prc.Unitario'] = df_compras['Notas']
        df_compras.loc[df_compras['Notas'].notna(), 'MONEDA'] = 'Dolar'
        df_compras = df_compras.sort_values(by=['Producto', 'Fch Emision', 'ULTCOS'], ascending=[True, False,False]).reset_index(drop = True)
        df_compras.drop_duplicates(subset=['Producto', 'ULTCOS', 'Fch Emision'], inplace=True)
        df_compras = df_compras.reset_index(drop=True)
        df_compras["Verificacion"] = df_compras.duplicated(subset = "Producto", keep = "last")
        repetidos = []
        for l in df_compras.index:
            if df_compras["Verificacion"][l] == True:
                repetidos.append(l)
                repetidos.append(l+1)
        df_compras["Para compras?"] = ""
        df_repetidos = df_compras.iloc[repetidos]
        df_compras = df_compras.drop(index = repetidos)
        df_repetidos = df_repetidos.reset_index(drop=True)
        logger.debug(f"Cantidad de códigos repetidos detectados: {len(df_repetidos)}")
        variable_finalizadora = len(df_repetidos)
        i = 0
        j = i + 1
        while j < variable_finalizadora or i < variable_finalizadora:
            if( i-j == -2):
                df_repetidos = df_repetidos.reset_index(drop=True)
                i = 0
                j = i + 1
                variable_finalizadora = len(df_repetidos)
                continue
            cant_duplicados = contador_duplicados(df_repetidos,i, variable_finalizadora)
            if (cant_duplicados == 2):
                if df_repetidos["Prc.Unitario"][i] == df_repetidos["Prc.Unitario"][j]:
                    df_repetidos.drop([j], axis = 0, inplace = True)
                    i = i + 2
                    j = i + 1
                else:
                    if df_repetidos["Fch Emision"][i] > df_repetidos["Fch Emision"][j]:
                        df_repetidos.drop([j], axis = 0, inplace = True)
                        i = i + 2
                        j = i + 1
                    elif df_repetidos["Fch Emision"][i] < df_repetidos["Fch Emision"][j]:
                        df_repetidos.drop([i], axis = 0, inplace = True)
                        i = i + 1
                        j = i + 1
                    else:
                        df_repetidos.at[i, "Para compras?"] = "SI"
                        df_repetidos.at[j, "Para compras?"] = "SI"
                        i = i + 2
                        j = i + 1
            elif (cant_duplicados > 2):
                if df_repetidos["Prc.Unitario"][i] == df_repetidos["Prc.Unitario"][j]:
                    df_repetidos.drop([j], axis=0, inplace=True)
                    j = j + 1
                elif df_repetidos["Prc.Unitario"][i] != df_repetidos["Prc.Unitario"][j]:
                    if df_repetidos["Fch Emision"][i] > df_repetidos["Fch Emision"][j]:
                        df_repetidos.drop([j], axis = 0, inplace = True)
                        j = j + 1
                    elif df_repetidos["Fch Emision"][i] < df_repetidos["Fch Emision"][j]:
                        df_repetidos.drop([i], axis = 0, inplace = True)
                        i = i + 1
                        j = j + 1
                    else:
                        df_repetidos.at[i, "Para compras?"] = "SI"
                        df_repetidos.at[j, "Para compras?"] = "SI"
                        i = i + 2
                        j = i + 1
            elif (cant_duplicados == 1):
                i = i + 1
                j = i + 1
        df_depuradas = pd.concat([df_compras, df_repetidos], ignore_index=True)
        df_depuradas['Tasa Moneda'] = np.where(df_depuradas['MONEDA'] == 'Dolar', dolar, 1.0)
        df_depuradas['ULTCOS'] = (df_depuradas['Prc.Unitario'] * df_depuradas['Tasa Moneda']).round(2)
        df_depuradas['Var'] = ((df_depuradas['ULTCOS'] / df_depuradas['Costo Estand']) - 1).replace({np.inf: 'NUEVO'})


        df_depuradas.drop(columns=['Verificacion'], inplace=True, errors='ignore')
        df_depuradas.sort_values(by=['Producto', 'Fch Emision', 'ULTCOS'], ascending=[True, False, False], inplace=True)
        df_depuradas["OBSERVACIONES COSTOS"] = ""
        df_depuradas["RESPUESTA COMPRAS"] = ""
        logger.debug(f"Cantidad de códigos finales es: {len(df_depuradas)}")
        
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")

        path_guardado = f"{carpeta_guardado}/{fecha_hoy} Compras depuradas.xlsx"
        df_depuradas.to_excel(path_guardado, index=False)
        logger.info(f'Archivo "Compras depuradas" guardado en: {path_guardado}')
        return {"compras_depuradas": path_guardado}
    except Exception as e:
        logger.error(f"Error en el procesamiento de compras: {e}", exc_info=True)
        raise 