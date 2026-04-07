# Sistema de Costeo - Guia tecnica

---

## Tabla de contenidos

1. [Introduccion](#1-introduccion)
2. [Estructura del proyecto](#2-estructura-del-proyecto)
3. [Flujo general de procesamiento](#3-flujo-general-de-procesamiento)
4. [Modulos principales](#4-modulos-principales)
5. [Validaciones centralizadas](#5-validaciones-centralizadas)
6. [Sistema de logging y auditoria](#6-sistema-de-logging-y-auditoria)
7. [Pruebas automatizadas](#7-pruebas-automatizadas)
8. [Empaquetado y distribucion](#8-empaquetado-y-distribucion)
9. [Buenas practicas y recomendaciones](#9-buenas-practicas-y-recomendaciones)
10. [Extension y mantenimiento](#10-extension-y-mantenimiento)
11. [Contacto y soporte](#11-contacto-y-soporte)

---

## 1. Introduccion

Este proyecto automatiza el procesamiento de archivos Excel para analisis y calculo de costos.
La aplicacion mantiene un modelo operativo simple (GUI + Excel), con foco en:

- Confiabilidad operativa.
- Trazabilidad de ejecuciones.
- Validacion temprana de datos.
- Refactor incremental sin romper resultados de negocio.

La logica de negocio esta desacoplada de la GUI para permitir ejecucion por interfaz, scripts y pruebas automatizadas.

---

## 2. Estructura del proyecto

```text
Costeando1.1/
|-- main_interfaz_grafica.py
|-- main_interfaz_grafica.spec
|-- Costeando.spec
|-- setup.bat
|-- requirements.txt
|-- README.md
|-- metodo_uso.md
|-- costeando/
|   |-- gui/
|   |   |-- compras_window.py
|   |   |-- listado_gral_window.py
|   |   |-- primer_comprando_window.py
|   |   |-- primer_produciendo_window.py
|   |   |-- segundo_comprando_window.py
|   |   |-- segundo_produciendo_window.py
|   |   |-- proyectados_window.py
|   |   |-- valorizacion_dyc_window.py
|   |   |-- actualizacion_fchs_window.py
|   |   `-- leader_list_window.py
|   |-- modulos/
|   |   |-- procesamiento_compras.py
|   |   |-- procesamiento_primer_comprando.py
|   |   |-- procesamiento_segundo_comprando.py
|   |   |-- procesamiento_primer_produciendo.py
|   |   |-- procesamiento_segundo_produciendo.py
|   |   |-- procesamiento_listado_gral.py
|   |   |-- procesamiento_proyectados.py
|   |   |-- procesamiento_valorizacion_dyc.py
|   |   |-- procesamiento_actualizacion_fchs.py
|   |   `-- procesamiento_leader_list.py
|   `-- utilidades/
|       |-- validaciones.py
|       |-- errores_aplicacion.py
|       |-- manejo_errores_gui.py
|       |-- auditoria.py
|       |-- configuracion_logging.py
|       `-- func_faltante_cotizacion.py
|-- tests/
|   |-- test_primer_comprando_*.py
|   |-- test_segundo_comprando_*.py
|   |-- test_procesamiento_*.py
|   |-- test_*_confiabilidad.py
|   `-- test_validaciones.py
`-- _artifacts/
    `-- manifiestos/   # salida por defecto de manifiestos cuando no se informa carpeta valida
```

---

## 3. Flujo general de procesamiento

1. Entrada de archivos Excel y parametros por GUI.
2. Validacion de archivos, columnas, tipos y reglas minimas.
3. Normalizacion y transformaciones de datos.
4. Calculo de reglas de negocio del modulo.
5. Exportacion de archivos resultado.
6. Generacion de `id_ejecucion` y manifiesto JSON de auditoria (`OK` o `ERROR`).
7. En caso de error, mapeo a mensaje legible para usuario y log tecnico para soporte.

---

## 4. Modulos principales

Cada modulo expone una funcion principal de procesamiento desacoplada de GUI.

- `procesamiento_compras.py`: transforma base de compras y genera salida operativa.
- `procesamiento_primer_comprando.py`: primera etapa de costo comprando.
- `procesamiento_segundo_comprando.py`: segunda etapa de costo comprando.
- `procesamiento_primer_produciendo.py`: primera etapa de costo produciendo.
- `procesamiento_segundo_produciendo.py`: segunda etapa de costo produciendo.
- `procesamiento_listado_gral.py`: consolidacion y armado de listado general.
- `procesamiento_proyectados.py`: calculos de proyectados.
- `procesamiento_valorizacion_dyc.py`: valorizacion de costos.
- `procesamiento_actualizacion_fchs.py`: actualizacion de FCHS.
- `procesamiento_leader_list.py`: armado de leader list.

Contrato general esperado por modulo:

- Entradas validadas antes de calcular.
- Errores de dominio con codigo estable.
- Salidas de archivos + trazabilidad de ejecucion.

---

## 5. Validaciones centralizadas

`costeando/utilidades/validaciones.py` concentra las validaciones reutilizables:

- existencia y extension valida de archivo Excel.
- columnas obligatorias.
- deteccion de duplicados de clave.
- estandarizacion de clave de producto cuando aplica.

Reglas de integridad recomendadas:

- fallar temprano ante inconsistencia.
- error deterministico para el mismo problema.
- no modificar nombres de columnas externas que vienen del origen Excel.

---

## 6. Sistema de logging y auditoria

### Logging

- Configuracion central en `costeando/utilidades/configuracion_logging.py`.
- Se registran eventos informativos, de depuracion y de error.
- Errores tecnicos se guardan en logs, no se muestran crudos al usuario final.

### Contrato de errores de aplicacion

Definido en `costeando/utilidades/errores_aplicacion.py` con jerarquia tipada:

- `ErrorEntradaArchivo`
- `ErrorEsquemaArchivo`
- `ErrorReglaNegocio`
- `ErrorEscrituraSalida`
- `ErrorInternoInesperado`

### Error legible en GUI

`costeando/utilidades/manejo_errores_gui.py` construye mensajes con:

- `codigo_error`
- `titulo_usuario`
- `mensaje_usuario`
- `accion_sugerida`
- `id_ejecucion`

### Manifiesto de auditoria

`costeando/utilidades/auditoria.py` guarda un JSON por ejecucion con:

- `id_ejecucion`, `proceso`, `estado`, `fecha_hora`
- `entradas`, `parametros`, `metricas`, `archivos_generados`
- `codigo_error` cuando aplica

Ubicacion:

- Si el proceso recibe carpeta de salida valida, se guarda ahi.
- Si no recibe carpeta valida (`None`, `"."`, `"./"`, `".\\"`), se guarda en `_artifacts/manifiestos`.

---

## 7. Pruebas automatizadas

### Framework

La suite usa `pytest`.

### Ejecucion completa

```powershell
pytest tests -q
```

### Gates recomendados por modulo (ejemplo comprando)

```powershell
pytest tests/test_primer_comprando_reglas.py tests/test_primer_comprando_confiabilidad.py tests/test_primer_comprando_regresion.py tests/test_primer_comprando_helpers_refactor.py -q
pytest tests/test_segundo_comprando_confiabilidad.py tests/test_procesamiento_segundo_comprando.py -q
```

### Criterio de avance

- No avanzar de fase con pruebas rojas.
- Toda refactorizacion debe mantener regresion funcional en verde.

---

## 8. Empaquetado y distribucion

- `setup.bat` automatiza tareas de empaquetado.
- Los archivos `.spec` (`Costeando.spec`, `main_interfaz_grafica.spec`) definen configuracion de build.
- Recomendacion operativa: validar ejecutable en entorno limpio antes de distribuir.

---

## 9. Buenas practicas y recomendaciones

- Usar entorno virtual para desarrollo y pruebas.
- Mantener `requirements.txt` alineado con dependencias reales.
- Priorizar funciones pequenas, legibles y de una sola responsabilidad.
- Mantener nombres en espaniol en codigo nuevo o refactorizado.
- Respetar columnas externas de origen sin renombrarlas arbitrariamente.
- Registrar evidencia con tests antes y despues de cada cambio.

---

## 10. Extension y mantenimiento

Estrategia recomendada para nuevos cambios:

1. Definir contrato de entrada/salida y errores.
2. Agregar o actualizar pruebas.
3. Refactorizar en cortes pequenos.
4. Ejecutar gate de modulo y luego suite completa.
5. Documentar impacto tecnico y criterios de aceptacion.

Se evita enfoque big bang para no degradar confiabilidad operativa.

---

## 11. Contacto y soporte

- Responsable inicial: [LinkedIn](https://www.linkedin.com/in/tomas-lahuel-salvatierra-787a53249)
- Soporte tecnico: [salvatierratomaslahuel@gmail.com](email:salvatierratomaslahuel@gmail.com)

Para soporte, incluir siempre:

- modulo ejecutado
- `codigo_error`
- `id_ejecucion`
- archivo de log y manifiesto asociado

---

## Advertencias para nuevos desarrolladores

- Leer esta guia y `metodo_uso.md` antes de modificar modulos.
- No cambiar reglas de negocio sin prueba de regresion asociada.
- No introducir fallbacks silenciosos en columnas externas de origen.
- Mantener foco en simplicidad + confiabilidad.
