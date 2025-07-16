import traceback
from costeando.modulos.procesamiento_primer_produciendo import procesar_primer_produciendo

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'campana_actual': '15',
    'anio_actual': '2025',
    'ruta_produciendo_anterior': r'Z:\Costos\Compartido\514 c14-2025\CALCULO COSTOS 514\09-06-25 CALCULO PRODUCIENDO 514.xlsx',
    'ruta_maestro_produciendo': r'Z:\Costos\Compartido\515 c15-2025\MAESTRO 515\18-06-25 MAESTRO 515 PARA DEPURAR EL LEADER LIST productos_130158.xlsx',
    'ruta_stock': r'Z:\Costos\Compartido\515 c15-2025\COSTOS ESPECIALES 515\INFO. C ESPECIALES\09-06-2025 stock_actual_valorizado_por_producto_C10 2025.xlsx',
    'ruta_descuentos_especiales': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\515 AL INICIO - Descuentos Especiales - Base de Datos C14 2025-Segunda Etapa Produciendo.xlsx',
    'ruta_rotacion': r'Z:\Costos\Compartido\515 c15-2025\CALCULO COSTOS 515\Comprando Etapas 515\Comprando Primer Etapa 515\Rotacion calculada C15 2025.xlsx',
    'ruta_estructuras': r'Z:\Costos\Compartido\515 c15-2025\ESTRUCTURAS 515\24-06-25 sccybbl0 Reporte Estructuras por Nivel 515 - Costo Producción-.xlsx',
    'ruta_salida': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_primer_produciendo(
            paths['campana_actual'],
            paths['anio_actual'],
            paths['ruta_produciendo_anterior'],
            paths['ruta_maestro_produciendo'],
            paths['ruta_stock'],
            paths['ruta_descuentos_especiales'],
            paths['ruta_rotacion'],
            paths['ruta_estructuras'],
            paths['ruta_salida']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 