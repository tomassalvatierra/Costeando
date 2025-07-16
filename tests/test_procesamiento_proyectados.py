import traceback
from costeando.modulos.procesamiento_proyectados import procesar_proyectados_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_lista': r'Z:\Costos\Compartido\515 c15-2025\LISTA 515\25-06-25 LISTA 515 C15-2025 consulta_lista_de_precios_140815(Planilla trabajo).xlsx',
    'ruta_coef': r'Z:\Costos\Compartido\515 c15-2025\TABLA COEF 515\30-06-25 COEFICIENTES DE ACTUALIZACION 515.xlsx',
    'camp_inicial': '15',  # Ejemplo: '01'
    'anio_inicial': '2025',   # Ejemplo: '2024'
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_proyectados_puro(
            paths['ruta_lista'],
            paths['ruta_coef'],
            paths['camp_inicial'],
            paths['anio_inicial'],
            paths['carpeta_guardado']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 