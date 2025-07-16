import traceback
from costeando.modulos.procesamiento_actualizacion_fchs import procesar_actualizacion_fchs_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_estructuras': r'Z:\Costos\Compartido\515 c15-2025\ESTRUCTURAS 515\24-06-25 sccybbl0 Reporte Estructuras por Nivel 515 - Costo Producción-.xlsx',
    'ruta_compras': r'Z:\Costos\Compartido\515 c15-2025\PEDIDOS DE COMPRA 515\18-06-25 Compras y cotizaciones 515.xlsx',
    'ruta_maestro': r'Z:\Costos\Compartido\515 c15-2025\MAESTRO 515\18-06-25 MAESTRO 515 PARA DEPURAR EL LEADER LIST productos_130158.xlsx',
    'ruta_ordenes_apuntadas': r'Z:\Costos\Compartido\515 c15-2025\FECHA ULT.COMPRA 515\19-06-25 Ordenes Apuntadas 515 dde 02-06 al dia 11 am - ordenes_apuntadas_105737.xlsx',
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_actualizacion_fchs_puro(
            paths['ruta_estructuras'],
            paths['ruta_compras'],
            paths['ruta_maestro'],
            paths['ruta_ordenes_apuntadas'],
            paths['carpeta_guardado']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 