import pandas as pd


LIMITE_CAMPANIAS_GENERAL = 27
LIMITE_CAMPANIAS_COMPONENTES = 18
STOCK_MINIMO_PRODUCTO_TERMINADO = 500

NOTA_VENCIMIENTO_GENERAL = "Pierde descuento por sobrepasar de 27 campanias(anio y medio)"
NOTA_SIN_STOCK = "Pierde el descuento por no tener stock"
NOTA_VENCIMIENTO_COMPONENTES = "Pierde descuento por sobrepasar de 18 campanias"

COLUMNAS_AUXILIARES_VENCIMIENTO = [
    "Anio_Otorgamiento",
    "Campania_Otorgamiento",
    "Stock Actual",
    "anio/campania abs",
]


def campania_a_absoluta(campania, anio):
    return (int(anio) - 2021) * 18 + int(campania)


def agregar_columnas_otorgamiento(df_base_dtos, columna_origen="APLICA DDE CA:"):
    df_resultado = df_base_dtos.copy()
    split_aplica = df_resultado[columna_origen].astype(str).str.split("/", expand=True)
    anio = split_aplica[0] if 0 in split_aplica.columns else pd.Series(index=df_resultado.index, dtype=object)
    campania = split_aplica[1] if 1 in split_aplica.columns else pd.Series(index=df_resultado.index, dtype=object)
    df_resultado["Anio_Otorgamiento"] = pd.to_numeric(anio, errors="coerce").fillna(0).astype(int)
    df_resultado["Campania_Otorgamiento"] = pd.to_numeric(campania, errors="coerce").fillna(0).astype(int)
    return df_resultado


def calcular_campania_limite_stock(campania_stock, anio_actual):
    campania_limite = int(campania_stock)
    if campania_limite < 1:
        campania_limite += 18
        anio_limite = int(anio_actual) - 1
    else:
        anio_limite = int(anio_actual)
    return campania_limite, anio_limite


def _asegurar_columnas_otorgamiento(df_base_dtos):
    columnas_otorgamiento = {"Anio_Otorgamiento", "Campania_Otorgamiento"}
    if columnas_otorgamiento.issubset(df_base_dtos.columns):
        return df_base_dtos.copy()
    return agregar_columnas_otorgamiento(df_base_dtos)


def _marcar_vencidos(df_resultado, mascara, nota):
    df_resultado.loc[mascara, "VENCIDO"] = "Si"
    df_resultado.loc[mascara, "NOTAS"] = nota


def _mascara_vencimiento_general(df_resultado, absoluta_actual):
    return (
        (df_resultado["VENCIDO"] == "No")
        & ((absoluta_actual - df_resultado["anio/campania abs"]) > LIMITE_CAMPANIAS_GENERAL)
    )


def _mascara_sin_stock(df_resultado, absoluta_limite):
    return (
        (df_resultado["VENCIDO"] == "No")
        & (df_resultado["TIPO-DESCUENTO"] == "AGOTAMIENTO-PRODUCTO TERMINADO")
        & (df_resultado["Stock Actual"] < STOCK_MINIMO_PRODUCTO_TERMINADO)
        & (df_resultado["anio/campania abs"] < absoluta_limite)
    )


def _mascara_vencimiento_componentes(df_resultado, absoluta_actual):
    return (
        (df_resultado["VENCIDO"] == "No")
        & (df_resultado["TIPO-DESCUENTO"] == "AGOTAMIENTO-COMPONENTES")
        & ((absoluta_actual - df_resultado["anio/campania abs"]) > LIMITE_CAMPANIAS_COMPONENTES)
    )


def actualizar_vencimiento_descuentos(df_base_dtos, campania_actual, anio_actual, campania_stock=None):
    df_resultado = _asegurar_columnas_otorgamiento(df_base_dtos)
    if df_resultado.empty:
        df_resultado.drop(columns=COLUMNAS_AUXILIARES_VENCIMIENTO, inplace=True, errors="ignore")
        return df_resultado.copy(), df_resultado.copy(), df_resultado.copy()

    estado_original = df_resultado["VENCIDO"].copy()
    df_resultado["anio/campania abs"] = df_resultado.apply(
        lambda row: campania_a_absoluta(row["Campania_Otorgamiento"], row["Anio_Otorgamiento"]),
        axis=1,
    )
    absoluta_actual = campania_a_absoluta(campania_actual, anio_actual)

    _marcar_vencidos(
        df_resultado,
        _mascara_vencimiento_general(df_resultado, absoluta_actual),
        NOTA_VENCIMIENTO_GENERAL,
    )

    if campania_stock is not None:
        campania_limite, anio_limite = calcular_campania_limite_stock(campania_stock, anio_actual)
        absoluta_limite = campania_a_absoluta(campania_limite, anio_limite)
        _marcar_vencidos(
            df_resultado,
            _mascara_sin_stock(df_resultado, absoluta_limite),
            NOTA_SIN_STOCK,
        )

    _marcar_vencidos(
        df_resultado,
        _mascara_vencimiento_componentes(df_resultado, absoluta_actual),
        NOTA_VENCIMIENTO_COMPONENTES,
    )

    mascara_cambios = (estado_original != "Si") & (df_resultado["VENCIDO"] == "Si")
    df_cambios = df_resultado.loc[mascara_cambios].copy()
    
    df_resultado.drop_duplicates(inplace=True)
    
    df_resultado.drop(columns=COLUMNAS_AUXILIARES_VENCIMIENTO, inplace=True, errors="ignore")
    df_cambios.drop(columns=COLUMNAS_AUXILIARES_VENCIMIENTO, inplace=True, errors="ignore")
    df_no_vencidos = df_resultado.loc[df_resultado["VENCIDO"] == "No"].copy()
    return df_resultado, df_no_vencidos, df_cambios

