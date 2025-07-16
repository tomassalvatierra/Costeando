import traceback
from costeando.modulos.procesamiento_primer_comprando import procesar_primer_comprando

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'campana': '15',
    'anio': '2025',
    'indice_a': 1.25,  # Ejemplo de valor
    'indice_b': 1.0,  # Ejemplo de valor
    'mano_de_obra': 11.45,  # Ejemplo de valor
    'ruta_maestro': r'Z:\Costos\Compartido\515 c15-2025\MAESTRO 515\18-06-25 MAESTRO 515 PARA DEPURAR EL LEADER LIST productos_130158.xlsx',
    'ruta_compras': r'Z:\Costos\Compartido\515 c15-2025\PEDIDOS DE COMPRA 515\18-06-25 Compras y cotizaciones 515.xlsx',
    'ruta_stock': r'Z:\Costos\Compartido\515 c15-2025\COSTOS ESPECIALES 515\INFO. C ESPECIALES\09-06-2025 stock_actual_valorizado_por_producto_C10 2025.xlsx',
    'ruta_dto_especiales': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\515 AL INICIO - Descuentos Especiales - Base de Datos C14 2025-Segunda Etapa Produciendo.xlsx',
    'ruta_listado': r'Z:\Costos\Compartido\514 c14-2025\LISTA 514\10-06-25 LISTA 514 C14-2025 consulta_lista_de_precios_112153 (Planilla de Trabajo).xlsx',
    'ruta_calculo_comprando_ant': r'Z:\Costos\Compartido\514 c14-2025\CALCULO COSTOS 514\04-06-25 CALCULO COMPRANDO 514.xlsx',
    'ruta_ficha': r'Z:\Públicos\Ficha RMS\Historicos\202509\ficha_rms_20250605_14.xlsx',
    'ruta_salida': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
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