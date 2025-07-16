import traceback
from costeando.modulos.procesamiento_segundo_produciendo import procesar_segundo_produciendo

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_produciendo': r'Z:\Costos\Compartido\515 c15-2025\CALCULO COSTOS 515\Produciendo Etapas 515\Produciendo Primer Etapa 515\24-06-2025 Produciendo primera etapa 515.xlsx',
    'ruta_base_especiales': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\515 AL INICIO - Descuentos Especiales - Base de Datos C14 2025-Segunda Etapa Produciendo.xlsx',
    'ruta_importador_descuentos': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\Importadores C.Esp 515\23-06-25 Importador Dtos. Produciendo 515.xlsx',  # Puede ser None
    'campana': '15',
    'anio': '2025',
    'fecha_compras_inicio': '01/01/2025',
    'fecha_compras_final': '31/12/2025',
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_segundo_produciendo(
            paths['ruta_produciendo'],
            paths['ruta_base_especiales'],
            paths['ruta_importador_descuentos'],
            paths['campana'],
            paths['anio'],
            paths['fecha_compras_inicio'],
            paths['fecha_compras_final'],
            paths['carpeta_guardado']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 