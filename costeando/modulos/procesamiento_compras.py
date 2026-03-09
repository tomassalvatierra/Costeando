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


def resolver_duplicados(df_repetidos: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada grupo de productos con el mismo código, aplica la siguiente lógica:
      - Si todos tienen el mismo precio → queda uno solo (el de fecha más reciente).
      - Si tienen precios distintos → queda el de fecha más reciente.
      - Si tienen precios distintos Y la misma fecha más reciente → se marcan todos
        como "Para compras?" = "SI" para revisión manual.

    Reemplaza el loop while con índices manuales del código original.
    """
    result_frames = []

    # El df ya viene ordenado por ['Producto', 'Fch Emision', 'ULTCOS'] desc,
    # así que dentro de cada grupo el primer elemento es el más reciente / más caro.
    for _, group in df_repetidos.groupby('Producto', sort=False):
        group = group.copy().reset_index(drop=True)

        # Todos con el mismo precio → queda el primero (más reciente)
        if group['Prc.Unitario'].nunique() == 1:
            result_frames.append(group.iloc[[0]])
            continue

        # Precios distintos: buscamos los candidatos con la fecha más reciente
        max_fecha = group['Fch Emision'].max()
        candidatos = group[group['Fch Emision'] == max_fecha].copy()

        if len(candidatos) == 1:
            # Un único ganador claro
            result_frames.append(candidatos)
        else:
            # Varios registros con la misma fecha máxima y precios distintos
            # → requieren revisión manual
            candidatos['Para compras?'] = 'SI'
            result_frames.append(candidatos)

    if not result_frames:
        return pd.DataFrame(columns=df_repetidos.columns)

    return pd.concat(result_frames, ignore_index=True)


def procesar_compras_puro(ruta_compras: str, dolar: float, carpeta_guardado: str) -> Dict[str, str]:
    """
    Procesa el archivo de compras y guarda el archivo generado en la carpeta indicada.
    Devuelve un diccionario con el path del archivo generado.
    """
    try:
        validar_archivo_excel(ruta_compras, "Compras")
        logger.info("Iniciando procesamiento puro de compras")

        compras_originales = pd.read_excel(ruta_compras, engine="openpyxl")
        df_compras = compras_originales.copy()
        logger.debug(f"Filas originales: {len(df_compras)}")

        df_compras = df_compras.loc[df_compras["Resid. Elim."] != "S", :]
        df_compras["Producto"] = df_compras["Producto"].astype(str).str.strip()

        try:
            df_compras = eliminar_productos_no_deseados(
                df_compras, ['Producto'], ['MAT', 'GAS', 'BSUSO', 'FLE', 'HON', 'SER'])
        except Exception as e:
            logger.info(f"No existen productos a eliminar o error: {e}")

        df_compras = df_compras[
            df_compras['Observacion'].apply(lambda x: 'RECHAZO' not in str(x).upper())]
        
        df_compras.Notas = df_compras.Notas.replace({'.' : ","})
        df_compras['Notas'] = pd.to_numeric(df_compras['Notas'], errors='coerce')
        df_compras['Tipo-Costos'] = df_compras.apply(clasificacion_compras, axis=1)
        df_compras = df_compras[~df_compras["Tipo-Costos"].isin(["Excedente - Pesos", "Sufacturacion - Dolar", "Excedente - Dolar"])]
        df_compras.loc[df_compras['Notas'].notna(), 'Prc.Unitario'] = df_compras['Notas']
        df_compras.loc[df_compras['Notas'].notna(), 'MONEDA'] = 'Dolar'

        df_compras = df_compras.sort_values(
            by=['Producto', 'Fch Emision', 'ULTCOS'],
            ascending=[True, False, False]
        ).reset_index(drop=True)
        df_compras.drop_duplicates(subset=['Producto', 'ULTCOS', 'Fch Emision'], inplace=True)
        df_compras = df_compras.reset_index(drop=True)

        # Separar únicos de repetidos
        df_compras["Para compras?"] = ""
        mascara_repetidos = df_compras.duplicated(subset="Producto", keep=False)
        df_repetidos = df_compras[mascara_repetidos].copy()
        df_unicos = df_compras[~mascara_repetidos].copy()
        logger.debug(f"Códigos repetidos detectados: {df_repetidos['Producto'].nunique()}")

        # --- Resolución de duplicados (reemplaza el while con índices manuales) ---
        df_repetidos_resueltos = resolver_duplicados(df_repetidos)

        df_depuradas = pd.concat([df_unicos, df_repetidos_resueltos], ignore_index=True)
        df_depuradas['Tasa Moneda'] = np.where(df_depuradas['MONEDA'] == 'Dolar', dolar, 1.0)
        df_depuradas['ULTCOS'] = (df_depuradas['Prc.Unitario'] * df_depuradas['Tasa Moneda']).round(2)
        df_depuradas['Var'] = (
            (df_depuradas['ULTCOS'] / df_depuradas['Costo Estand']) - 1
        ).replace({np.inf: 'NUEVO'})

        df_depuradas.drop(columns=['Verificacion'], inplace=True, errors='ignore')
        df_depuradas.sort_values(
            by=['Producto', 'Fch Emision', 'ULTCOS'],
            ascending=[True, False, False],
            inplace=True
        )
        df_depuradas["OBSERVACIONES COSTOS"] = ""
        df_depuradas["RESPUESTA COMPRAS"] = ""
        logger.debug(f"Cantidad de códigos finales: {len(df_depuradas)}")

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        path_guardado = f"{carpeta_guardado}/{fecha_hoy} Compras depuradas.xlsx"
        df_depuradas.to_excel(path_guardado, index=False)
        logger.info(f'Archivo "Compras depuradas" guardado en: {path_guardado}')
        return {"compras_depuradas": path_guardado}

    except Exception as e:
        logger.error(f"Error en el procesamiento de compras: {e}", exc_info=True)
        raise