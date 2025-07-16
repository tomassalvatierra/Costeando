# COSTEANDO

Hola, bienvenido al archivo README del proyecto "Costeando".

Diseñador y desarrollador: Tomás Lahuel Salvatierra.
Colaborador: Vanesa Mansilla.

Esta es la primera versión de un software específico para el área de Costos de la empresa GIGOT COSMETICOS. Con este servicio podremos procesar las etapas de, LEADER LIST, COMPRAS, COMPRANDO, PRODUCIENDO, PROYECTADOS y la VALORIZACION DE DOBLES Y COMBINADAS, son parte de un proceso mayor que ha sido fraccionado. Queda pendiente una conexión a una base de datos y mejoras, pero será un buen punto de partida.
Para este proyecto se utilizó el lenguaje de programación Python, las librerías Pandas, Numpy fueron las seleccionadas para el procesamiento de datos, Tkinter para la interfaz gráfica y Logging para el seguimiento de errores y registros de acciones. 

En este texto comentare las funcionalidades y como utilizar el programa. 
Para comenzar abra el ejecutable "Costeando", se abrirá el menú principal donde podrá seleccionar el proceso a conveniencia, una vez seleccione el proceso presione el botón "Ejecutar".

El formato de todos los programas con los que cuenta este software es la misma, le pedirá ingresar datos por teclado y seleccionar archivos necesarios para el procesamiento. Hare todos los ejemplos enfocados en campaña 509 (Campaña 09 del año 2025).

Comencemos...

# PROCESO LEADER LIST
Objetivo: con el Leader List proporcionado por comercial el programa se encargará de agregar información adicional para el análisis de los costos como, por ejemplo, dobles y combinadas, ¿atiende necesidad?, costo de la lista anterior, descuentos anteriores y columnas de interés. El proceso retornara dos archivos, el leader list procesado y las combinadas agrupadas (subproceso que se realiza con el fin de identificar todos los códigos que componen a una combinada).

El sistema le pedirá:

Seleccionar los siguientes archivos.

- Leader List: sin ningún cambio, exactamente igual a como lo envía Comercial.
- Listado de Costos: listado de costos anterior a la campaña a procesar, para este ejemplo ingresé Listado 508 (DEBE EXISTIR LA COLUMNA 'COSTOS LISTA 508').
- Maestro: el archivo original de TOTVS, (QUITAR LOS PICOS VERDES y los ESPACIOS, informe especifico "Productos")
- Dobles: original como lo envían de Fox.
- Combinadas: original como lo envían de Fox.
 
Ingresar los siguientes datos.
    
- Campaña a procesar (CC): ejemplo, 09.
- Año (AAAA): ejemplo, 2025.
    
Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final. De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el
proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# PROCESO COMPRAS

Objetivo: simplificar el archivo para que solo quede una ORDEN DE COMPRA por cada código que exista dentro del mediante operaciones lógicas y condiciones impuestas por el sector. Si un código esta repetido luego de finalizar revise la columna "PARA COMPRAS", esto indica que usted debe consultar con el área para la decisión de este registro.

El sistema le pedirá:

Ingresar los siguientes datos.

- Dólar: para pacificar las compras en moneda uso, ejemplo, 1600. Si se ponen valores con decimales utilizar el punto y no la coma.
    
Seleccionar los siguientes archivos.
    
- Compras:  archivo de pedidos de compras del periodo que se necesite, original como viene de TOTVS, solo quitar los picos verdes y los espacios de la columna "Producto" o "Código", informe especifico 'Costos de Pedidos de Compra por Fch Emisión'.

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final con el nombre que elija en la parte inferior. De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
    
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# VALORIZACION DE DYC (DOBLES Y COMBINADAS)

Objetivo: valorizar los códigos dobles y combinadas con el listado de la campaña que el usuario proporcione. Solo devolverá los códigos que tengan costo, los demás lo omitirá.

El sistema le pedirá:

Seleccionar los siguientes archivos.
    
- Dobles: (Original como lo envían de Fox)
- Combinadas: (Original como lo envían de Fox)
- Listado: (Con el listado que quiere valorizar las dobles y combinadas. Ejemplo, 509. DEBE EXISTIR LA COLUMNA "COSTOS LISTA 509").

Ingresar los siguientes datos.
    
- Campaña a procesar: (CC) (Ejemplo; 09)
- Año: (AAAA) (Ejemplo; 2025) 

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final con el nombre que elija en la parte inferior, *este programa guardara un solo archivo con dos solapas, una para las dobles valorizadas y otro para las combinadas valorizadas*.

De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# PROCESO PRIMER COMPRANDO

Objetivo: procesara solo los códigos que pertenezcan a la categoría “Atiende Ne" igual a "Comprando"(componentes o productos terminados comprados a terceros), actualizara sus costos dependiendo de si tuvieron compras nuevas o no, asignara descuentos previamente existentes, y prepara el archivo para poder asignar nuevos descuentos y el cálculo final de los costos. El proceso retornara 4 archivos, la base de descuentos actualizada, el archivo primer comprando listo para calcular descuentos, la rotación calculada y los cambios realizados en la base de datos de los descuentos especiales.

Solicitará los siguientes archivos.
    
- Maestro: el original de TOTVS, QUITAR LOS PICOS VERDES y los ESPACIOS a la columna "Producto" o "Código", es el informe especifico "Productos".
- Compras: Compras y Cotizaciones revisadas.
- Stock: Archivos de stock que este a disposición, QUITAR LOS PICOS VERDES y los ESPACIOS a la columna "Producto" o "Código", es el informe especifico 'Stock Actual Valorizado por Producto'.
- Base Descuentos: La base de descuentos más actualizada.
- Lista N-1: listado de costos anterior a la campaña a procesar(n-1), para este ejemplo, ingrese Listado 508. (DEBE EXISTIR LA COLUMNA "COSTO LISTA 508").
- Comprando N-1: comprando anterior, para este ejemplo ingrese Comprando 508. (DEBE EXISTIR LA COLUMNA "Costo sin Descuento C08").
- Ficha: ficha rms, el archivo que hay que seleccionar este dentro de la ruta “Z:\Públicos\Ficha RMS\Historicos” y dentro de esta buscar la carpeta que sea 5 campañas menor a la que se está procesando (202504) y seleccionar el primer archivo que aparezca.

La interfaz pedirá los siguientes datos. 
    
    - Campaña a procesar (CC): (ejemplo: 09).
    - Año (AAAA): el año que acompaña a la campaña a procesar, (ejemplo: 2025).
    - Mano de Obra: valor de lamino de obra, (ejemplo: 9.56).
    - Índice A: valor del coeficiente Nacional, (ejemplo: 1.0217).
    - Índice B: valor del coeficiente Internacional, (ejemplo: 1).

Recuerde utilizar siempre el punto (.) como separador decimal y no la coma (,).

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final con el nombre que elija en la parte inferior.
De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# PROCESO SEGUNDO COMPRANDO

Objetivo: se importarán los nuevos descuentos y se calcularán de manera que la suma de todos no supere el 75%. Concluirá la etapa de los "Comprando" creando la columna "Costo primer importador". Devolverá el archivo finalizado, el archivo importador para TOTVS y la base de descuentos modificada para su próxima utilización.

La interfaz pedirá los siguientes datos. 
    
- Campaña a procesar (CC.): (ejemplo: 09).
- Año (AAAA): el año que acompaña a la campaña a procesar (ejemplo: 2025).
- Fecha de inicio de compras (dd/mm/aaaa): ingrese la fecha del día inicial de las compras, (ejemplo 27/01/2025)
- Fecha de final de compras (dd/mm/aaaa): ingrese la fecha del día final de las compras, (ejemplo 18/02/2025)

Solicitará los siguientes archivos.

- Comprando: archivo "Comprando primera etapa" de la campaña que procesa, para este ejemplo, (Primer Comprando C09).
- Base Dtos: la base de descuentos más actualizada.
- Importador: archivo con los descuentos que desea agregar en este proceso. Misma estructura que la base de descuentos, pero solo con los nuevos descuentos.

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde seleccione la carpeta donde va a guardar los archivos.
De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.  
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# PROCESO PRODUCIENDO PRIMERA ETAPA

Objetivo: ¿procesara solo los códigos que pertenezcan a la categoría “Atiende Ne?" igual a "Produciendo"(productos producidos y acondicionados y envasados por gigot), actualizara los costos dependiendo de si llevan o no carga fabril, asignara descuentos previamente existentes, y prepara el archivo para poder asignar nuevos descuentos y el cálculo final de los costos. El proceso retornara 3 archivos, la base de descuentos modificada, los cambios que se realizaron en la base de descuentos, y los produciendo primera etapa.

Solicitará los siguientes archivos.
    
- Maestro: El original de TOTVS, lo único que hay que hacer es QUITAR LOS PICOS VERDES y los ESPACIOS a la columna "Producto" o "Código", informe especifico "Productos".
- Produciendo: archivo produciendo N-1, para traer la carga fabril.
- Stock: Archivos de stock que este a disposición, lo único que hay que hacer es QUITAR LOS PICOS VERDES y los ESPACIOS a la columna "Producto" o "Código", informe especifico 'Stock Actual Valorizado por Producto'.
- Base Descuentos: La base de descuentos más actualizada.
- Rotación: archivo de rotación procesado por el proceso de Primer Comprando.

La interfaz pedirá los siguientes datos. 
    
- Campaña a procesar (CC.): (ejemplo: 09).
- Año (AAAA): el año que acompaña a la campaña a procesar (ejemplo: 2025).

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final con el nombre que elija en la parte inferior.
De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

# PROCESO PRODUCIENDO SEGUNDA ETAPA

Objetivo: se importarán los nuevos descuentos y se calcularán de manera que la suma de todos no supere el 75%. Concluirá la etapa de los "Produciendo" creando la columna "Costo segundo importador". EL proceso retornara 3 archivos, el importador para TOTVS, la base de descuentos medicada y los preciando segunda etapa finalizado.

Solicitará los siguientes archivos.

- Produciendo: archivo "Produciendo primera etapa" de la campaña que se procesara.
- Base Descuentos: la base de descuentos que retorna el proceso "Produciendo primera etapa".
- Importador Dtos: archivo con los descuentos que desea agregar en este proceso. Misma estructura que la base de descuentos, pero solo con los nuevos descuentos.

La interfaz pedirá los siguientes datos. 
    
- Campaña a procesar (CC): (ejemplo: 09).
- Año (AAAA): el año que acompaña a la campaña a procesar (ejemplo: 2025).
- Fecha de inicio de compras (dd/mm/aaaa): ingrese la fecha del día inicial de las compras, (ejemplo 27/01/2025)
- Fecha de final de compras (dd/mm/aaaa): ingrese la fecha del día final de las compras, (ejemplo 18/02/2025)

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted seleccione la carpeta donde va a guardar los archivos.
    
De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.


# PROYECTADOS
Objetivo: proyectara todos los códigos incluidos en el Listado General de Costos que se le dé. Las proyecciones corresponderán a los distintos tipos de "VARIABLE" que puede tener un código (DOLAR, NACIONAL, MIX). El proceso devolverá la lista proyectada n+10 campaña hacia delante general (con todos los códigos de la lista) y un filtrado para comercial (solo productos terminados de 5 dígitos o menos).

Solicitará los siguientes archivos.

- Lista: Lista de Costos para Proyectar (deben existir las columnas "VARIABLE" y "COSTO LISTA 509").
- Coeficientes: (Archivo de coeficientes, mínimo tiene que tener N+10 campañas de coeficientes).

La interfaz pedirá los siguientes datos. 
    
- Campaña a procesar (CC): ejemplo, 09.
- Año (AAAA): ejemplo, 2025.

Presione el botón "Procesar" y este comenzara a trabajar, si la ventana no responde no se preocupe, mantenga la calma y pronto abrirá un cuadro para que usted guarde el archivo final con el nombre que elija en la parte inferior. De ocurrir un error se abrirá un cuadro de texto indicando porque no se pudo terminar el proceso.
Una vez finalizado el guardado del archivo aparecerá un cartel de aviso, presione "Aceptar" y el programa lo enviará al menú principal.

*Comentarios adicionales*

Base de descuentos: este archivo es la base de datos de los descuentos especiales que se aplican cada campaña, descuentos por producto terminado o por componentes. Luego de la utilización del primer comprando, una vez finalizado el cálculo del costo especial a otorgar en la campaña corriente, el usuario debe crear un importador para en la segunda etapa poder introducirlos en el proceso. El importador debe tener la siguiente estructura.

Codigo, DESCUENTO ESPECIAL, APLICA DDE CA:, TIPO-DESCUENTO, VENCIDO.

Ejemplo:
- Código: 365
- DESCUENTO ESPECIAL: 35, (si el descuento es un valor racional utiliza el punto como separador decimal).
- APLICA DDE CA: 2025/09, (siempre respete este formato)
- TIPO-DESCUENTO: AGOTAMIENTO-COMPONENTES / AGOTAMIENTO-PRODUCTO TERMINADO
- Vencido: (No). Este último campo es muy importante, ya que el programa eliminara todos los 'Vencidos'== 'Si', y luego trabajara con los descuentos vigentes.

Los demás campos no son obligatorios, puede llenarlos para tener más información en la base, pero no se necesitan para el proceso.

Para salir del programa presione el botón "Salir" o la equis de arriba a la derecha, le repreguntará si desea salir, presione que sí y el programa se habrá cerrado.
