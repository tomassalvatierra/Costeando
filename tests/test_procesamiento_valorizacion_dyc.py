import traceback
from costeando.modulos.procesamiento_valorizacion_dyc import procesar_valorizacion_dyc_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_listado': r'Z:\Costos\Compartido\515 c15-2025\LISTA 515\25-06-25 LISTA 515 C15-2025 consulta_lista_de_precios_140815(Planilla trabajo).xlsx',
    'ruta_combinadas': r'Z:\Costos\Compartido\515 c15-2025\DOBLES Y COMB 515\18-06-25 COMBINADAS 515 A LA FECHA (ANDRE).xlsx',
    'ruta_dobles': r'Z:\Costos\Compartido\515 c15-2025\DOBLES Y COMB 515\17-06-25 DOBLES 515 A LA FECHA (ANDRE).xlsx',
    'campana': '15',  # Ejemplo: '01'
    'anio': '2025',   # Ejemplo: '2024'
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_valorizacion_dyc_puro(
            paths['ruta_listado'],
            paths['ruta_combinadas'],
            paths['ruta_dobles'],
            paths['campana'],
            paths['anio'],
            paths['carpeta_guardado']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 