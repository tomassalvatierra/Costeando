import traceback
from costeando.modulos.procesamiento_compras import procesar_compras_puro

# === EDITA AQUÍ LOS PATHS DE TUS ARCHIVOS ===
paths = {
    'ruta_compras': r'Z:\Costos\Compartido\516 C16-2025\PEDIDOS DE COMPRA 516\PEDIDOS COMPRA PARA DEPURAR 516\10-07-25 ORDEN 001 516 DDE 23-06 AL 10-07 8AM-- costos_de_pedidos_de_compra_por_f.emision_080315.xlsx',
    'dolar': 1750,  # Ejemplo de valor para el dólar
    'carpeta_guardado': r'C:\Users\tsalvatierra\Desktop\PRUEBAS\PRUEBAS COMPLETAS'
}
# ===========================================

if __name__ == '__main__':
    try:
        resultados = procesar_compras_puro(
            paths['ruta_compras'],
            paths['dolar'],
            paths['carpeta_guardado']
        )
        print('\nProcesamiento exitoso. Archivos generados:')
        for nombre, path in resultados.items():
            print(f"{nombre}: {path}")
    except Exception as e:
        print('\n¡Error durante el procesamiento!')
        print(str(e))
        print(traceback.format_exc()) 