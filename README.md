# Documentación Técnica – Sistema de Costeo y Procesamiento de Archivos Excel

---

## Tabla de Contenidos

1. [Introducción](#introducción)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Flujo General de Procesamiento](#flujo-general-de-procesamiento)
4. [Módulos Principales](#módulos-principales)
5. [Validaciones Centralizadas](#validaciones-centralizadas)
6. [Sistema de Logging](#sistema-de-logging)
7. [Pruebas Automatizadas](#pruebas-automatizadas)
8. [Empaquetado y Distribución](#empaquetado-y-distribución)
9. [Buenas Prácticas y Recomendaciones](#buenas-prácticas-y-recomendaciones)
10. [Extensión y Mantenimiento](#extensión-y-mantenimiento)
11. [Contacto y Soporte](#contacto-y-soporte)

---

## 1. Introducción

Este proyecto automatiza el procesamiento y depuración de archivos Excel relacionados con costos, compras y producción. Está diseñado para ser **modular, validado, testeable y fácil de mantener**. La arquitectura desacopla la lógica de negocio de la interfaz gráfica, permitiendo su uso tanto desde la GUI como desde scripts o tests.

---

## 2. Estructura del Proyecto

```
Costeando1.1/
│
├── main_interfaz_grafica.py         # Interfaz gráfica principal (GUI)
├── configuracion_logging.py         # Configuración centralizada de logs
├── requirements.txt                 # Dependencias del proyecto
├── setup.bat / empaquetar.bat       # Scripts para empaquetado con PyInstaller
├── README.md                        # Documentación de usuario
├── logs/                            # Carpeta de logs generados
├── versiones/                       # Versionado de archivos de salida
├── costeando/
│   ├── modulos/
│   │   ├── procesamiento_actualizacion_fchs.py   
│   │   ├── procesamiento_compras.py   
│   │   ├── procesamiento_leader_list.py   
│   │   ├── procesamiento_primer_comprando.py   
│   │   ├── procesamiento_segundo_comprando.py   
│   │   ├── procesamiento_primer_produciendo.py   
│   │   ├── procesamiento_segundo_produciendo.py
│   │   ├── procesamiento_proyectados.py
│   │   ├── procesamiento_valorizacion_dyc.py          
|   |
│   └── utilidades/
│       ├── validaciones.py          # Validaciones reutilizables
│       |── configuracion_logging.py
│       |── func_faltante_cotizacion.py
|                   
└── tests/
    |── test_procesamiento_*.py  
    ├──test_actualizacion_fchs.py  
    ├── test_compras.py   
    ├── test_leader_list.py   
    ├── test_primer_comprando.py   
    ├── test_segundo_comprando.py   
    ├── test_primer_produciendo.py  
    ├── test_segundo_produciendo.py
    ├── test_proyectados.py
    ├── test_valorizacion_dyc.py      
```

---

## 3. Flujo General de Procesamiento

1. **Entrada:** Archivos Excel de costos, compras, estructuras, etc.
2. **Procesamiento:** Cada módulo realiza validaciones, transformaciones y cálculos específicos.
3. **Salida:** Archivos Excel procesados, listos para uso operativo o análisis.
4. **Interfaz:** El usuario puede operar desde la GUI o ejecutar los módulos de procesamiento de forma independiente.

---

## 4. Módulos Principales

Cada módulo de procesamiento está desacoplado de la interfaz y expone una función principal, por ejemplo:

```python
def procesar_compras_puro(ruta_compras: str, dolar: float, carpeta_guardado: str) -> Dict[str, str]:
    ...
```

**Características:**
- Validan entradas antes de procesar.
- Registran logs en cada etapa clave.
- Manejan excepciones y reportan errores de forma clara.
- Son fácilmente testeables y reutilizables.

**Ejemplo de uso en un script:**
```python
from costeando.modulos.procesamiento_compras import procesar_compras_puro
procesar_compras_puro('compras.xlsx', 900.0, 'resultados/')
```

---

## 5. Validaciones Centralizadas

El archivo `validaciones.py` contiene funciones reutilizables para:
- Validar existencia y formato de archivos.
- Verificar columnas obligatorias.
- Detectar nulos y duplicados.
- Lanzar excepciones con mensajes claros.

**Uso típico:**
```python
from costeando.utilidades.validaciones import validar_archivo_excel, validar_columnas
validar_archivo_excel(ruta, "nombre lógico")
validar_columnas(df, ["Col1", "Col2"], "nombre lógico")
```

**Ventaja:** Si cambian los requisitos de validación, solo se modifica este archivo.

---

## 6. Sistema de Logging

- **Configuración centralizada:** En `configuracion_logging.py`.
- **Uso en todos los módulos:**
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("Mensaje informativo")
  logger.debug("Mensaje de depuración")
  logger.error("Mensaje de error", exc_info=True)
  ```
- **Archivos de log:** Se almacenan en la carpeta `logs/` y permiten trazabilidad completa de los procesos.
- **Importante:** Revisa los logs ante cualquier error o comportamiento inesperado.

---

## 7. Pruebas Automatizadas

- **Ubicación:** Carpeta `tests/`.
- **Cobertura:** Todos los módulos principales tienen su test correspondiente.
- **Ejecución:**
  ```bash
  python -m unittest discover tests
  ```
- **Buenas prácticas:** Los paths de archivos de prueba se definen en variables para facilitar la reutilización.

---

## 8. Empaquetado y Distribución

- **Script `setup.bat`:** Automatiza el empaquetado con PyInstaller.
- **Opciones recomendadas:**
  - `--onefile` para un solo ejecutable.
  - `--windowed` para aplicaciones GUI.
  - Incluir archivos de datos con `--add-data` si es necesario.
- **Prueba en limpio:** Siempre probar el ejecutable en una PC sin Python instalado para asegurar que no falte ninguna dependencia.

**Ejemplo de línea en el .bat para incluir archivos de datos:**
```bat
pyinstaller --noconfirm --onefile --windowed --add-data "configuracion_logging.py;." %SCRIPT%
```

---

## 9. Buenas Prácticas y Recomendaciones

- **Usar entorno virtual** para desarrollo y empaquetado.
- **Actualizar `requirements.txt`** al agregar nuevas dependencias.
- **Documentar funciones y módulos** con docstrings claros.
- **Mantener los logs limpios** y revisarlos periódicamente.
- **Eliminar código obsoleto** y mantener la estructura ordenada.
- **Probar siempre en un entorno limpio** antes de distribuir.

---

## 10. Extensión y Mantenimiento

- **Nuevos módulos:** Seguir el patrón de función pura, validaciones y logging.
- **Nuevas validaciones:** Agregar en `validaciones.py` y reutilizar en los módulos.
- **Integración con CI/CD:** Se recomienda agregar workflows para ejecutar tests automáticamente en cada push.
- **Soporte multiplataforma:** Si se requiere soporte para Mac/Linux, adaptar los scripts de empaquetado.

---

## 11. Contacto y Soporte

- **Responsable inicial:** [www.linkedin.com/in/tomas-lahuel-salvatierra-787a53249]
- **Consultas técnicas:** Revisar primero los logs y la documentación de cada módulo.
- **Soporte:** [salvatierratomaslahuel@gmail.com]

---

## **Advertencias y Consejos para Nuevos Desarrolladores**

- **Lee el README y esta documentación antes de modificar el código.**
- **No borres ni modifiques scripts de procesamiento sin entender su flujo.**
- **Si tienes dudas, consulta con el responsable antes de hacer cambios mayores.**
- **Haz siempre pruebas después de modificar cualquier módulo.**
- **Mantén la estructura y los nombres de archivos para evitar errores en la GUI y los scripts.**

---

**Este fue el primer proyecto que realize como desarrollador, aprendi, acerte y me equivoque, seguramente si sos un dev esperimentado vas a encontrar millones de errores, y agradeceria mucho que me dieras un feedback. Siempre el fin fue empezar e ir mejorando.**

**"Adelanten a su yo de ayer. Mantenerse igual, es lo mismo que retroceder." Endeavor.**

