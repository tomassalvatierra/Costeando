import pandas as pd
import numpy as np
import os
from datetime import datetime
import logging
from costeando.utilidades.auditoria import guardar_manifiesto_ejecucion
from costeando.utilidades.errores_aplicacion import (
    ErrorAplicacion,
    ErrorEsquemaArchivo,
    ErrorInternoInesperado,
    ErrorReglaNegocio,
    generar_id_ejecucion,
)
from costeando.utilidades.validaciones import (
    estandarizar_columna_producto,
    validar_archivo_excel,
    validar_columna_fecha_parseable,
    validar_columnas,
)

logger = logging.getLogger(__name__)

def asignar_clasificacion(rotacion):
    if rotacion == 0:
        return 'SIN ROTACION'
    elif 0 < rotacion < 0.11:
        return 'BAJA ROTACION'
    elif rotacion <= 0.75:
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
    df_ficha["Promedio"] = df_ficha["Promedio"].fillna(0)
    df_ficha["Clasificacion"] = ""
    Rota = df_ficha["Promedio"] / df_ficha["Stock N+6"]
    df_ficha = df_ficha.assign(Rotacion=Rota.values)
    df_ficha.rename(columns={"Rotacion": "% RotaciAn"}, inplace=True)
    df_ficha['Clasificacion'] = df_ficha['% RotaciAn'].apply(asignar_clasificacion)
    return df_ficha

def campania_a_absoluta(campania, anio):
    return (anio - 2021) * 18 + campania

def asignacion_campanias(campania, anio):
    if campania == '01':
        campania_anterior = '18'
        anio_anterior = str(int(anio) - 1)
    else:
        campania_anterior = str(int(campania) - 1).zfill(2)
        anio_anterior = anio
    ultimo_digito_anio_anterior = anio_anterior[-1]
    anio_campania_anterior = ultimo_digito_anio_anterior + campania_anterior
    return campania_anterior, anio_campania_anterior

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

def calcular_costo_sin_descuento(campania_anterior, row):
    if pd.notna(row['Costo Compra']):
        return row['Costo Compra'] * 1
    else:
        return round(row['Costo sin Descuento C' + campania_anterior] * row['Coef de Actualizacion'], 2)

def rellenar_valores(df, columnas, valor=0):
    df[columnas] = df[columnas].fillna(valor)
    return df

def calcular_variacion(df, numerador, denominador, nueva_columna, reemplazo_inf='NUEVO'):
    variacion = (df[numerador] / df[denominador]) - 1
    df[nueva_columna] = variacion.replace({np.inf: reemplazo_inf})
    return df

def actualizar_estado_vencido(df_base_dtos, campania_actual, anio_actual, campania_stock):
    df_resultado = df_base_dtos.copy()
    df_resultado['anio/campania abs'] = df_resultado.apply(
        lambda row: campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento']), axis=1)
    absoluta_actual = campania_a_absoluta(campania_actual, anio_actual)
    mascara_general = df_resultado.apply(
        lambda row: (absoluta_actual - campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento'])) > 27, axis=1)
    df_resultado.loc[mascara_general, 'VENCIDO'] = 'Si'
    df_resultado.loc[mascara_general, 'NOTAS'] = 'Pierde descuento por sobrepasar de 27 campanias(anio y medio)'
    df_vencidos = df_resultado[df_resultado['VENCIDO'] == 'Si']
    df_no_vencidos = df_resultado[df_resultado['VENCIDO'] == 'No']
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
        (df_no_vencidos['anio/campania abs'] < absoluta_limite))
    df_vencidos_terminados = df_no_vencidos[mascara_terminados].copy()
    df_vencidos_terminados['VENCIDO'] = 'Si'
    df_vencidos_terminados['NOTAS'] = 'Pierde el descuento por no tener stock'
    df_no_vencidos = df_no_vencidos[~mascara_terminados]
    mascara_componentes = (
        (df_no_vencidos['TIPO-DESCUENTO'] == 'AGOTAMIENTO-COMPONENTES') &
        df_no_vencidos.apply(
            lambda row: (absoluta_actual - campania_a_absoluta(row['Campania_Otorgamiento'], row['Anio_Otorgamiento'])) > 18, axis=1))
    df_vencidos_componentes = df_no_vencidos[mascara_componentes].copy()
    df_vencidos_componentes['VENCIDO'] = 'Si'
    df_vencidos_componentes['NOTAS'] = 'Pierde descuento por sobrepasar de 18 campanias'
    df_no_vencidos = df_no_vencidos[~mascara_componentes]
    df_final = pd.concat([df_vencidos, df_vencidos_terminados, df_vencidos_componentes, df_no_vencidos], ignore_index=True)
    df_final = df_final.sort_index()
    df_final.drop(columns=['Anio_Otorgamiento', 'Campania_Otorgamiento', 'Stock Actual', 'anio/campania abs'], inplace=True, errors='ignore')
    df_no_vencidos = df_final[df_final['VENCIDO'] == 'No'].copy()
    df_cambios = df_final[df_final['VENCIDO'] == 'Si'].copy()
    return df_final, df_cambios

def procesar_descuento(df_calculo_comprando, df_costos_especiales, campania, anio, df_compras):
    df_sin_vencidos01 = df_costos_especiales.loc[df_costos_especiales['VENCIDO'] == 'No'].copy()
    df_costos_especiales = df_costos_especiales.loc[df_costos_especiales['VENCIDO'] == 'Si']
    df_sin_vencidos01[['Anio_Otorgamiento', 'Campania_Otorgamiento']] = df_sin_vencidos01['APLICA DDE CA:'].str.split('/', expand=True)
    df_sin_vencidos01['Anio_Otorgamiento'] = df_sin_vencidos01['Anio_Otorgamiento'].fillna(0).astype(int)
    df_sin_vencidos01['Campania_Otorgamiento'] = df_sin_vencidos01['Campania_Otorgamiento'].fillna(0).astype(int)
    df_base_descuentos, df_cambios = actualizar_estado_vencido(df_sin_vencidos01, int(campania), int(anio), int(campania) - 5)
    df_no_vencidos = df_base_descuentos.loc[df_base_descuentos['VENCIDO'] == 'No'].copy()
    df_vencidos = df_base_descuentos.loc[df_base_descuentos['VENCIDO'] == 'Si']
    fechas_validas = pd.to_datetime(df_compras['Fch Emision'], errors='coerce').notna()
    codigos_con_compras = df_compras.loc[fechas_validas, 'Codigo'].unique()
    mascara = df_no_vencidos['Codigo'].isin(codigos_con_compras)
    df_no_vencidos.loc[mascara, 'VENCIDO'] = "Si"
    df_no_vencidos.loc[mascara, 'NOTAS'] = "X OC en campania C"+campania+"-"+anio
    mascara_calculo = df_calculo_comprando['Codigo'].isin(codigos_con_compras)
    df_calculo_comprando.loc[mascara_calculo, '% de obsolescencia'] = 0
    df_final = pd.concat([df_vencidos, df_no_vencidos], ignore_index=True)
    df_no_vencidos = df_final.loc[df_final['VENCIDO'] == 'No'].copy()
    df_cambios = df_final.loc[df_final['VENCIDO'] == 'Si'].copy()
    return df_calculo_comprando, df_final, df_no_vencidos, df_cambios

def _obtener_columna_atiende(df_maestro: pd.DataFrame) -> str:
    for nombre_columna in ["Atiende Ne?", "¿Atiende Ne?", "Atiende Necsdd"]:
        if nombre_columna in df_maestro.columns:
            return nombre_columna
    raise ErrorEsquemaArchivo(
        mensaje_tecnico="No se encontro columna de atencion de necesidad en maestro.",
        codigo_error="CST-VAL-001",
        titulo_usuario="Estructura de archivo invalida",
        mensaje_usuario="El archivo maestro no tiene la columna de atencion de necesidad.",
        accion_sugerida="Revise encabezados del maestro y vuelva a intentar.",
    )


def _validar_parametros_primer_comprando(campania, anio, indice_a, indice_b, mano_de_obra, ruta_salida):
    if not all([campania, anio, indice_a, indice_b, mano_de_obra]):
        raise ErrorReglaNegocio(
            mensaje_tecnico="Faltan parametros obligatorios en Primer Comprando.",
            codigo_error="CST-NEG-010",
            titulo_usuario="Parametros incompletos",
            mensaje_usuario="Faltan datos obligatorios para ejecutar Primer Comprando.",
            accion_sugerida="Complete campania, anio, indices y mano de obra.",
        )
    if not ruta_salida:
        raise ErrorReglaNegocio(
            mensaje_tecnico="No se indico ruta de salida en Primer Comprando.",
            codigo_error="CST-NEG-011",
            titulo_usuario="Falta ruta de salida",
            mensaje_usuario="No se definio una carpeta de salida.",
            accion_sugerida="Seleccione una carpeta valida para guardar resultados.",
        )


def _validar_columnas_minimas_primer_comprando(
    df_maestro,
    df_compras,
    df_stock,
    df_costos_especiales,
    df_listado_anterior,
    df_calculo_comprando_anterior,
    df_ficha_rms,
    campania_anterior,
    anio_campania_anterior,
):
    columna_atiende = _obtener_columna_atiende(df_maestro)
    validar_columnas(df_maestro, ["Codigo", "Cod Actualiz", "Blq. de Pant", columna_atiende, "Tipo", "Grupo", "Ult. Compra"], "maestro")
    validar_columna_fecha_parseable(df_maestro, "Ult. Compra", "maestro")
    validar_columnas(df_compras, ["Codigo", "ULTCOS", "Fch Emision", "MONEDA"], "compras")
    validar_columnas(df_stock, ["Codigo", "Stock Actual"], "stock")
    validar_columnas(df_costos_especiales, ["Codigo", "VENCIDO", "APLICA DDE CA:", "TIPO-DESCUENTO"], "base descuentos")
    validar_columnas(df_listado_anterior, ["Codigo", "COSTO LISTA " + anio_campania_anterior], "listado anterior")
    validar_columnas(df_calculo_comprando_anterior, ["Codigo", "Costo sin Descuento C" + campania_anterior], "comprando anterior")
    validar_columnas(
        df_ficha_rms,
        ["Codigo", "Stock Actual", "Pedidos N+1", "Pedidos N+2", "Pedidos N+3", "Pedidos N+4", "Pedidos N+5", "Stock N+6", "Grupo", "Tipo"],
        "ficha",
    )
    return columna_atiende


def _validar_archivos_entrada_primer_comprando(
    ruta_maestro,
    ruta_compras,
    ruta_stock,
    ruta_dto_especiales,
    ruta_listado,
    ruta_calculo_comprando_ant,
    ruta_ficha,
):
    validar_archivo_excel(ruta_maestro, "maestro")
    validar_archivo_excel(ruta_compras, "compras")
    validar_archivo_excel(ruta_stock, "stock")
    validar_archivo_excel(ruta_dto_especiales, "dto especiales")
    validar_archivo_excel(ruta_listado, "listado")
    validar_archivo_excel(ruta_calculo_comprando_ant, "calculo comprando anterior")
    validar_archivo_excel(ruta_ficha, "ficha RMS")


def _cargar_dataframes_primer_comprando(
    ruta_maestro,
    ruta_compras,
    ruta_stock,
    ruta_dto_especiales,
    ruta_listado,
    ruta_calculo_comprando_ant,
    ruta_ficha,
):
    return (
        pd.read_excel(ruta_maestro, engine="openpyxl"),
        pd.read_excel(ruta_compras, engine="openpyxl"),
        pd.read_excel(ruta_stock, engine="openpyxl"),
        pd.read_excel(ruta_dto_especiales, engine="openpyxl"),
        pd.read_excel(ruta_listado, engine="openpyxl"),
        pd.read_excel(ruta_calculo_comprando_ant, engine="openpyxl"),
        pd.read_excel(ruta_ficha, engine="openpyxl"),
    )


def _estandarizar_dataframes_primer_comprando(
    df_maestro,
    df_compras,
    df_stock,
    df_costos_especiales,
    df_listado_anterior,
    df_calculo_comprando_anterior,
    df_ficha_rms,
):
    lista_dfs = [
        (df_maestro, "Maestro"),
        (df_compras, "Compras"),
        (df_stock, "Stock"),
        (df_costos_especiales, "Base Especiales"),
        (df_listado_anterior, "Listado"),
        (df_calculo_comprando_anterior, "Comprando Anterior"),
        (df_ficha_rms, "Ficha RMS"),
    ]
    lista_dfs_estandarizados = [estandarizar_columna_producto(df, nombre) for df, nombre in lista_dfs]
    return tuple(lista_dfs_estandarizados)


def _preparar_base_calculo_comprando(df_maestro, columna_atiende):
    df_calculo_comprando = df_maestro.copy()
    df_calculo_comprando = df_calculo_comprando.replace("  /  /    ", "")
    for valor_origen, valor_destino in [("1", "A"), ("2", "B"), (1, "A"), (2, "B")]:
        df_calculo_comprando["Cod Actualiz"] = df_calculo_comprando["Cod Actualiz"].replace(valor_origen, valor_destino)
    for valor_origen, valor_destino in [(1, "Si"), (2, "No"), ("1", "Si"), ("2", "No")]:
        df_calculo_comprando["Blq. de Pant"] = df_calculo_comprando["Blq. de Pant"].replace(valor_origen, valor_destino)
    df_calculo_comprando[columna_atiende] = df_calculo_comprando[columna_atiende].replace("P", "Produciendo")
    mascara_exclusion = (
        (df_calculo_comprando["Tipo"].isin(["GG", "GN", "GI"]))
        | (df_calculo_comprando["Blq. de Pant"] == "Si")
        | (df_calculo_comprando[columna_atiende] == "Produciendo")
    )
    return df_calculo_comprando.drop(df_calculo_comprando[mascara_exclusion].index)

def _anexar_columnas_base(
    df_calculo_comprando,
    df_compras,
    df_stock,
    df_listado_anterior,
    df_calculo_comprando_anterior,
    anio_campania_anterior,
    campania_anterior,
):
    columnas_para_merge = [
        "ULTCOS",
        "Fch Emision",
        "OBSERVACIONES COSTOS",
        "RESPUESTA COMPRAS",
        "Campaña",
        "MONEDA",
        "Stock Actual",
        "COSTO LISTA " + anio_campania_anterior,
        "Costo sin Descuento C" + campania_anterior,
    ]

    dataframes_para_merge = [
        df_compras,
        df_compras,
        df_compras,
        df_compras,
        df_compras,
        df_compras,
        df_stock,
        df_listado_anterior,
        df_calculo_comprando_anterior,
    ]
    for columna, dataframe_origen in zip(columnas_para_merge, dataframes_para_merge):
        df_calculo_comprando = pd.merge(
            df_calculo_comprando,
            dataframe_origen[["Codigo", columna]],
            how="left",
            on="Codigo",
        )
    return df_calculo_comprando.drop_duplicates(subset="Codigo", keep="first")

def procesar_primer_comprando(campania, anio, indice_a, indice_b, mano_de_obra,
    ruta_maestro, ruta_compras, ruta_stock, ruta_dto_especiales,
    ruta_listado, ruta_calculo_comprando_ant, ruta_ficha, ruta_salida, id_ejecucion: str | None = None):
    id_proceso = id_ejecucion or generar_id_ejecucion()
    campania_anterior = None
    anio_campania_anterior = None
    try:
        logger.info("Iniciando procesamiento puro de Primer Comprando. ID=%s", id_proceso)
        _validar_archivos_entrada_primer_comprando(
            ruta_maestro,
            ruta_compras,
            ruta_stock,
            ruta_dto_especiales,
            ruta_listado,
            ruta_calculo_comprando_ant,
            ruta_ficha,
        )
        _validar_parametros_primer_comprando(campania, anio, indice_a, indice_b, mano_de_obra, ruta_salida)

        (
            df_maestro,
            df_compras,
            df_stock,
            df_costos_especiales,
            df_listado_anterior,
            df_calculo_comprando_anterior,
            df_ficha_rms,
        ) = _cargar_dataframes_primer_comprando(
            ruta_maestro,
            ruta_compras,
            ruta_stock,
            ruta_dto_especiales,
            ruta_listado,
            ruta_calculo_comprando_ant,
            ruta_ficha,
        )

        campania_anterior, anio_campania_anterior = asignacion_campanias(campania, anio)
        fecha_ingresada = datetime.now()
        (
            df_maestro,
            df_compras,
            df_stock,
            df_costos_especiales,
            df_listado_anterior,
            df_calculo_comprando_anterior,
            df_ficha_rms,
        ) = _estandarizar_dataframes_primer_comprando(
            df_maestro,
            df_compras,
            df_stock,
            df_costos_especiales,
            df_listado_anterior,
            df_calculo_comprando_anterior,
            df_ficha_rms,
        )
        columna_atiende = _validar_columnas_minimas_primer_comprando(
            df_maestro,
            df_compras,
            df_stock,
            df_costos_especiales,
            df_listado_anterior,
            df_calculo_comprando_anterior,
            df_ficha_rms,
            campania_anterior,
            anio_campania_anterior,
        )
        df_calculo_comprando = _preparar_base_calculo_comprando(df_maestro, columna_atiende)
        df_calculo_comprando = _anexar_columnas_base(
            df_calculo_comprando,
            df_compras,
            df_stock,
            df_listado_anterior,
            df_calculo_comprando_anterior,
            anio_campania_anterior,
            campania_anterior,
        )
        df_calculo_comprando['Ult. Compra'] = pd.to_datetime(df_calculo_comprando['Ult. Compra'])
        
        df_calculo_comprando['Coef de Actualizacion'] = df_calculo_comprando.apply(
            lambda row: asignar_coeficiente(indice_a, indice_b, row), axis=1)
        
        df_calculo_comprando.rename(columns={'ULTCOS': 'Costo Compra'}, inplace=True)
        
        df_calculo_comprando["Costo Compra"] = pd.to_numeric(
            df_calculo_comprando["Costo Compra"], errors="coerce"
        ).astype(float)
        
        df_costos_especiales = pd.merge(df_costos_especiales, df_stock[['Codigo','Stock Actual']], how='left')
        df_costos_especiales['Stock Actual'] = df_costos_especiales['Stock Actual'].fillna(0)
        df_calculo_comprando['% de obsolescencia'] = df_calculo_comprando.apply(
            lambda row: calcular_obsolescencia(fecha_ingresada, row)
            if (row['Tipo'] in ('PA','PD','PC')) and (row['Grupo'] in (1,2,3,4,6)) else None, axis=1)
        
        df_calculo_comprando, df_costos_especiales, df_no_vencidos, df_cambios = procesar_descuento(
            df_calculo_comprando, df_costos_especiales, campania, anio, df_compras)
        
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_no_vencidos[['Codigo','DESCUENTO ESPECIAL']], how='left', on='Codigo')
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_no_vencidos[['Codigo','APLICA DDE CA:']], how='left', on='Codigo')
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_costos_especiales[['Codigo','ROYALTY']], how='left', on='Codigo')
        
        df_calculo_comprando = df_calculo_comprando.sort_values(by=['Codigo','APLICA DDE CA:'], ascending=[True,False])
        df_calculo_comprando.drop_duplicates(subset='Codigo', keep='first', inplace=True)
        
        for codigo in ['MOD0806','MOD0807','MOD0808']:
            df_calculo_comprando.loc[df_calculo_comprando['Codigo'] == codigo, 'Costo Compra'] = mano_de_obra
        
        df_calculo_comprando = calcular_variacion(df_calculo_comprando, 'Costo Compra',
            'Costo sin Descuento C'+campania_anterior, '% var Compra VS Costo sin dto C'+campania_anterior)
        df_calculo_comprando = calcular_variacion(df_calculo_comprando, 'Costo Compra',
            'COSTO LISTA '+anio_campania_anterior, '%var Compra vs COSTO LISTA C'+campania_anterior)
        
        df_calculo_comprando.loc[df_calculo_comprando['Costo Compra'].notnull(), 'Coef de Actualizacion'] = 1
        df_calculo_comprando['Costo sin Descuento C'+campania] = df_calculo_comprando.apply(
            lambda row: calcular_costo_sin_descuento(campania_anterior, row), axis=1)
        
        columnas_a_rellenar = ['DESCUENTO ESPECIAL','% de obsolescencia','ROYALTY',
                               'Costo sin Descuento C'+campania,'Costo sin Descuento C'+campania_anterior]
        df_calculo_comprando = rellenar_valores(df_calculo_comprando, columnas_a_rellenar)
        df_calculo_comprando.rename(columns={'MONEDA': 'MONEDA/COMPRAS'}, inplace=True)
        
        df_rotacion = procesar_rotacion(df_ficha_rms)
        df_calculo_comprando = pd.merge(df_calculo_comprando, df_rotacion[['Codigo','Clasificacion']], how='left', on='Codigo')
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        
        if not os.path.exists(ruta_salida):
            os.makedirs(ruta_salida)
        
        path_rotacion = os.path.join(ruta_salida, f'{fecha_hoy} Rotacion calculada C{campania}-{anio}.xlsx')
        path_base_descuentos = os.path.join(ruta_salida, f'{fecha_hoy} BASE DTOS-Primera etapa comprando C{campania}-{anio}.xlsx')
        path_cambios = os.path.join(ruta_salida, f'{fecha_hoy} Cambios realizados en la base C{campania}-{anio}.xlsx')
        path_calculo_comprando = os.path.join(ruta_salida, f'{fecha_hoy} Calculo Comprando-Primera etapa C{campania}-{anio}.xlsx')
        
        df_rotacion.to_excel(path_rotacion, index=False, engine='openpyxl')
        df_costos_especiales.to_excel(path_base_descuentos, index=False, engine='openpyxl')
        df_cambios.to_excel(path_cambios, index=False, engine='openpyxl')
        df_calculo_comprando.to_excel(path_calculo_comprando, index=False, engine='openpyxl')
        
        logger.info(f"Procesamiento finalizado. Archivos guardados en: {ruta_salida}")
        path_manifiesto = guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida,
            id_ejecucion=id_proceso,
            proceso="primer_comprando",
            estado="OK",
            entradas={
                "ruta_maestro": ruta_maestro,
                "ruta_compras": ruta_compras,
                "ruta_stock": ruta_stock,
                "ruta_dto_especiales": ruta_dto_especiales,
                "ruta_listado": ruta_listado,
                "ruta_calculo_comprando_ant": ruta_calculo_comprando_ant,
                "ruta_ficha": ruta_ficha,
            },
            parametros={
                "campania": campania,
                "anio": anio,
                "indice_a": indice_a,
                "indice_b": indice_b,
                "mano_de_obra": mano_de_obra,
            },
            metricas={"filas_salida": len(df_calculo_comprando)},
            archivos_generados={
                "calculo_comprando": path_calculo_comprando,
                "rotacion": path_rotacion,
                "base_descuentos": path_base_descuentos,
                "cambios": path_cambios,
            },
        )
        return {
            'calculo_comprando': path_calculo_comprando,
            'rotacion': path_rotacion,
            'base_descuentos': path_base_descuentos,
            'cambios': path_cambios,
            'manifiesto': path_manifiesto,
            'id_ejecucion': id_proceso,
        }
    except ErrorAplicacion as error:
        error.con_id_ejecucion(id_proceso)
        guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida or ".",
            id_ejecucion=id_proceso,
            proceso="primer_comprando",
            estado="ERROR",
            entradas={
                "ruta_maestro": ruta_maestro,
                "ruta_compras": ruta_compras,
                "ruta_stock": ruta_stock,
                "ruta_dto_especiales": ruta_dto_especiales,
                "ruta_listado": ruta_listado,
                "ruta_calculo_comprando_ant": ruta_calculo_comprando_ant,
                "ruta_ficha": ruta_ficha,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error.codigo_error,
        )
        logger.error("Error controlado en Primer Comprando. ID=%s Codigo=%s", id_proceso, error.codigo_error, exc_info=True)
        raise
    except Exception as error:
        error_interno = ErrorInternoInesperado(
            mensaje_tecnico=f"Error inesperado en Primer Comprando: {error}",
            codigo_error="CST-INT-001",
            titulo_usuario="Error inesperado",
            mensaje_usuario="Ocurrio un error inesperado en Primer Comprando.",
            accion_sugerida="Reintente y si persiste contacte soporte con codigo e ID.",
            id_ejecucion=id_proceso,
        )
        guardar_manifiesto_ejecucion(
            carpeta_guardado=ruta_salida or ".",
            id_ejecucion=id_proceso,
            proceso="primer_comprando",
            estado="ERROR",
            entradas={
                "ruta_maestro": ruta_maestro,
                "ruta_compras": ruta_compras,
                "ruta_stock": ruta_stock,
                "ruta_dto_especiales": ruta_dto_especiales,
                "ruta_listado": ruta_listado,
                "ruta_calculo_comprando_ant": ruta_calculo_comprando_ant,
                "ruta_ficha": ruta_ficha,
            },
            parametros={"campania": campania, "anio": anio},
            metricas={},
            archivos_generados={},
            codigo_error=error_interno.codigo_error,
        )
        logger.error("Error inesperado en Primer Comprando. ID=%s", id_proceso, exc_info=True)
        raise error_interno from error

