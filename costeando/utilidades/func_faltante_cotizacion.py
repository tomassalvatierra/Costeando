import pandas as pd

def asignar_faltantes_cotizacion(df_produciendo, df_maestro,ruta_estructuras):
    """
    Esta función procesa dos archivos de Excel para identificar componentes sin cotización
    y genera un archivo de salida con los registros de prodcutos terminados que no deben ser bloqueados.
    """
    df_estructuras = pd.read_excel(ruta_estructuras, usecols= "A:O",engine='openpyxl', skiprows=4)
    
    df_analsis = df_estructuras.drop(['QUANT_NIVEL1','QUANT_NIVEL2', 'QUANT_NIVEL3'],axis=1)

    #==========================================
    # Filtrar registros donde COSTO_NIVEL3 es 0 
    #==========================================
    
    df_sin_componente3 = df_analsis.loc[(df_analsis["COSTO_NIVEL3" ]==0) & (df_analsis["DESC_NIVEL3"].notna())]

    # Crear lista de tuplas usando zip()
    codigos_sin_costo_pt = list(zip(df_sin_componente3['COD_NIVEL0'], df_sin_componente3['COMP_NIVEL3']))
    codigos_sin_costo_comp1 = list(zip(df_sin_componente3['COMP_NIVEL1'], df_sin_componente3['COMP_NIVEL3']))
    codigos_sin_costo_comp2 = list(zip(df_sin_componente3['COMP_NIVEL2'], df_sin_componente3['COMP_NIVEL3']))

    codigos_a_cero_compo3 =codigos_sin_costo_pt+codigos_sin_costo_comp1+ codigos_sin_costo_comp2

    df_codigos_a_cero_compo3 = pd.DataFrame(codigos_a_cero_compo3, columns=['Codigo', 'COMPONENTE FALTANTE'])
    
    #==========================================
    # Filtrar registros donde COSTO_NIVEL2 es 0 
    #==========================================
    
    df_sin_componente2 = df_estructuras.loc[(df_estructuras["COSTO_NIVEL2" ]==0) & (df_estructuras["DESC_NIVEL2"].notna())]

    # Crear una lista de tuplas con las columnas concatenadas y el COMP_NIVEL3 asociado
    codigos_sin_costo_pt = list(zip(df_sin_componente2['COD_NIVEL0'], df_sin_componente2['COMP_NIVEL2']))
    codigos_sin_costo_comp1 = list(zip(df_sin_componente2['COMP_NIVEL1'], df_sin_componente2['COMP_NIVEL2']))

    codigos_a_cero_compo2 =codigos_sin_costo_pt+codigos_sin_costo_comp1
    df_codigos_a_cero_compo2 = pd.DataFrame(codigos_a_cero_compo2, columns=['Codigo', 'COMPONENTE FALTANTE'])

    #==========================================
    # Filtrar registros donde COSTO_NIVEL1 es 0 
    #==========================================
    
    df_sin_componente1 = df_estructuras.loc[(df_estructuras["COSTO_NIVEL1" ]==0) & (df_estructuras["DESC_NIVEL1"].notna())]

    # Crear una lista de tuplas con las columnas concatenadas y el COMP_NIVEL3 asociado
    codigos_sin_costo_pt = list(zip(df_sin_componente1['COD_NIVEL0'], df_sin_componente1['COMP_NIVEL1']))

    df_codigos_a_cero_compo1 = pd.DataFrame(codigos_sin_costo_pt, columns=['Codigo', 'COMPONENTE FALTANTE'])

    df_sin_cotizacion = pd.concat([df_codigos_a_cero_compo3, df_codigos_a_cero_compo2, df_codigos_a_cero_compo1], ignore_index=True)
    
    
    df_sin_cotizacion.drop_duplicates(subset='Codigo', keep='first', inplace=True)


    df_sin_cotizacion = df_sin_cotizacion.astype({'Codigo': str})
    df_sin_cotizacion = pd.merge(df_sin_cotizacion, df_maestro[["Codigo", "Blq. de Pant"]], how='left')
    df_sin_cotizacion = pd.merge(df_sin_cotizacion, df_maestro[["Codigo", "Descripcion"]], how='left')

    df_registros_sin_bloquear = df_sin_cotizacion.loc[df_sin_cotizacion['Blq. de Pant']== 2]

    df_filtrado = df_registros_sin_bloquear.loc[
        ~(
            (df_registros_sin_bloquear['COMPONENTE FALTANTE'].astype(str).str.len() == 7) &
            (df_registros_sin_bloquear['COMPONENTE FALTANTE'].astype(str).str.startswith('180'))
        )
    ]
    
    df_produciendo = pd.merge(df_produciendo, df_filtrado[['Codigo', 'COMPONENTE FALTANTE']], how='left')
    df_produciendo['COMPONENTE FALTANTE']= df_produciendo['COMPONENTE FALTANTE'].fillna('') 
    
    return df_produciendo

