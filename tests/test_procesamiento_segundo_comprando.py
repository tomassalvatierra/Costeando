import traceback
from costeando.modulos.procesamiento_segundo_comprando import procesar_segundo_comprando

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_comprando': r'Z:\Costos\Compartido\515 c15-2025\CALCULO COSTOS 515\Comprando Etapas 515\Comprando Primer Etapa 515\19-06-25 Primera Etapa  Comprando 515.xlsx',
    'ruta_costos_especiales': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\515 AL INICIO - Descuentos Especiales - Base de Datos C14 2025-Segunda Etapa Produciendo.xlsx',
    'ruta_importador_descuentos': r'Z:\Costos\Compartido\515 c15-2025\BASE DTOS ESPECIALES 515\Importadores C.Esp 515\23-06-25 Importador Dtos. Comprando 515.xlsx',  # Puede ser None
    'campana': '15',
    'anio': '2025',
    'fecha_compras_inicio': '01/01/2025',
    'fecha_compras_final': '31/12/2025',
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_segundo_comprando(
            paths['ruta_comprando'],
            paths['ruta_costos_especiales'],
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