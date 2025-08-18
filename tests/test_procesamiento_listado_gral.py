import traceback
from costeando.modulos.procesamiento_listado_gral import procesar_listado_gral_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {

    'ruta_produciendo': r'Z:/Costos/Compartido/517 c17-2025/CALCULO COSTOS 517/07-08-2025 CALCULO PRODUCIENDO 517.xlsx',
    'ruta_comprando': r'Z:/Costos/Compartido/517 c17-2025/CALCULO COSTOS 517/07-08-2025 CALCULO COMPRANDO 517.xlsx',
    'ruta_costo_primo':r'Z:/Costos/Compartido/517 c17-2025/COSTO PRIMO 517/07-08-2025 MAESTRO COSTO PRIMO 517.xlsx',
    'ruta_base_descuentos':r'Z:/Costos/Compartido/517 c17-2025/BASE DTOS 517/07-08-2025 Descuentos Especiales - Base de Datos C17 2025 produciendo 2da etapa.xlsx',
    'ruta_listado':r'Z:/Costos/Compartido/517 c17-2025/LISTA 517/08-08-2025 LISTA 517 consulta_lista_de_precios_153702.xlsx',
    'ruta_mdo': r'Z:/Costos/Compartido/517 c17-2025/PT X COMPO 517/13-08-2025 PT X COMPONENTE 517.xlsx',
    'ruta_leader_list': r'Z:/Costos/Compartido/517 c17-2025/LEADER LIST 517/28-07-2025 RESUMEN LEADER LIST 517.xlsx',
    'campania': r'17',
    'anio': r'2025',
    'carpeta_guardado':r'Z:\Costos\Compartido\517 c17-2025\LISTA 517',
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_listado_gral_puro(
            paths['ruta_produciendo'],
            paths['ruta_comprando'],
            paths['ruta_costo_primo'],
            paths['ruta_base_descuentos'],
            paths['ruta_listado'],
            paths['ruta_mdo'],
            paths['ruta_leader_list'],
            paths['campania'],
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