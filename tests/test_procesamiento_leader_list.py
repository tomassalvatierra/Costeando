import traceback
from costeando.modulos.procesamiento_leader_list import procesar_leader_list_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_leader_list': r'Z:\Costos\Compartido\515 c15-2025\LEADER LIST 515\LL RECIBIDOS 515\18-06-25 Leader List C15 2025 actualizada todas las unid.negocio (DENU).xlsx',
    'ruta_listado_anterior': r'Z:\Costos\Compartido\514 c14-2025\LISTA 514\10-06-25 LISTA 514 C14-2025 consulta_lista_de_precios_112153 (Planilla de Trabajo).xlsx',
    'ruta_maestro': r'Z:\Costos\Compartido\515 c15-2025\MAESTRO 515\18-06-25 MAESTRO 515 PARA DEPURAR EL LEADER LIST productos_130158.xlsx',
    'ruta_dobles': r'Z:\Costos\Compartido\515 c15-2025\DOBLES Y COMB 515\17-06-25 DOBLES 515 A LA FECHA (ANDRE).xlsx',
    'ruta_combinadas': r'Z:\Costos\Compartido\515 c15-2025\DOBLES Y COMB 515\18-06-25 COMBINADAS 515 A LA FECHA (ANDRE).xlsx',
    'ruta_stock': r'Z:\Costos\Compartido\515 c15-2025\COSTOS ESPECIALES 515\INFO. C ESPECIALES\09-06-2025 stock_actual_valorizado_por_producto_C10 2025.xlsx',
    'campana': '15',  # Ejemplo: '01'
    'anio': '2025',   # Ejemplo: '2024'
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_leader_list_puro(
            paths['ruta_leader_list'],
            paths['ruta_listado_anterior'],
            paths['ruta_maestro'],
            paths['ruta_dobles'],
            paths['ruta_combinadas'],
            paths['ruta_stock'],
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