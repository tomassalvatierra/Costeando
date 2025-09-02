import traceback
from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'campana': '17',
    'anio': '2025',
    'indice_a': 1.25,  # Ejemplo de valor
    'indice_b': 1.0,  # Ejemplo de valor
    'mano_de_obra': 11.45,  # Ejemplo de valor
    'ruta_maestro': r'Z:\Costos\Compartido\517 c17-2025\MAESTRO 517\01-08-2025 MAESTRO COMPRANDO productos_142342.xlsx',
    'ruta_compras': r'Z:\Costos\Compartido\517 c17-2025\PEDIDOS DE COMPRA 517\01-08-2025 Compras y Cotizaciones 517.xlsx',
    'ruta_stock': r'Z:\Costos\Compartido\515 c15-2025\COSTOS ESPECIALES 515\INFO. C ESPECIALES\09-06-2025 stock_actual_valorizado_por_producto_C10 2025.xlsx',
    'ruta_dto_especiales': r'Z:\Costos\Compartido\516 C16-2025\CALCULO COSTOS 516\Produciendo Etapas 516\Segunda Etapa Produciendo 516\Descuentos Especiales - Base de Datos C16 2025.xlsx',
    'ruta_listado': r'Z:\Costos\Compartido\516 C16-2025\LISTA 516\16-07-25 LISTA 516 C16-2025 consulta_lista_de_precios_122323 (Planilla de trabajo).xlsx',
    'ruta_calculo_comprando_ant': r'Z:\Costos\Compartido\516 C16-2025\CALCULO COSTOS 516\15-07-25 CALCULO COMPRANDO 516.xlsx',
    'ruta_ficha': r'Z:\Públicos\Ficha RMS\Historicos\202509\ficha_rms_20250605_14.xlsx',
    'ruta_salida': r'C:\Users\tsalvatierra\Desktop'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_primer_comprando(
            paths['campana'],
            paths['anio'],
            paths['indice_a'],
            paths['indice_b'],
            paths['mano_de_obra'],
            paths['ruta_maestro'],
            paths['ruta_compras'],
            paths['ruta_stock'],
            paths['ruta_dto_especiales'],
            paths['ruta_listado'],
            paths['ruta_calculo_comprando_ant'],
            paths['ruta_ficha'],
            paths['ruta_salida']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 