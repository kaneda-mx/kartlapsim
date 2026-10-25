# simulation-run Specification

## Purpose
Ejecutar el simulador de vuelta sin interfaz gráfica y conservar los resultados en archivos legibles por máquina, de modo que una comparación de configuraciones pueda verificarse, repetirse y consumirse después por una interfaz web.

## Requirements

### Requirement: Ejecución sin interfaz gráfica

El sistema SHALL ejecutar una simulación completa sin necesidad de pantalla, servidor gráfico ni interacción del usuario, y SHALL terminar el proceso cuando acabe el cálculo.

#### Scenario: Ejecución en un entorno sin pantalla

- **WHEN** se lanza una simulación en un entorno sin pantalla ni variable de entorno de display
- **THEN** la simulación se completa, los resultados quedan escritos y el proceso termina con código de salida 0

#### Scenario: El proceso no queda esperando una ventana

- **WHEN** la simulación genera una figura
- **THEN** la figura se escribe en un archivo y el proceso no abre ninguna ventana ni espera que alguien la cierre

### Requirement: Selección de configuraciones a comparar

El sistema SHALL aceptar una o varias relaciones de transmisión final para una misma pista y kart de ejemplo, y SHALL simular cada una de ellas en la misma ejecución.

#### Scenario: Comparación de dos relaciones

- **WHEN** se pide la ejecución con dos relaciones de transmisión final distintas
- **THEN** se produce un resultado completo por cada relación, ambos identificados por el valor usado

#### Scenario: Ejecución con la configuración de ejemplo

- **WHEN** no se indica ninguna relación de transmisión final
- **THEN** se simula la configuración de ejemplo incluida en el repositorio y el resultado la identifica como tal

### Requirement: Validación de entradas antes de simular

El sistema SHALL rechazar entradas numéricas no finitas, no positivas o fuera del rango documentado antes de iniciar el cálculo, indicando el valor rechazado y el rango admitido.

#### Scenario: Relación de transmisión inválida

- **WHEN** se solicita una relación de transmisión final igual a cero, negativa o no numérica
- **THEN** la ejecución termina con código distinto de 0, el mensaje nombra el valor y el rango admitido, y no se escribe ningún resultado

### Requirement: Resultados exportados en archivos

El sistema SHALL escribir, por cada configuración simulada, las series a lo largo del circuito en CSV, un resumen numérico en JSON y una figura de velocidad en PNG, en un directorio de salida indicado por quien ejecuta.

#### Scenario: Una ejecución deja los tres formatos

- **WHEN** termina correctamente una simulación
- **THEN** el directorio de salida contiene el CSV de series, el JSON de resumen y el PNG de velocidad de cada configuración

#### Scenario: Las series y el resumen son coherentes

- **WHEN** se comparan el CSV y el JSON de una misma configuración
- **THEN** el tiempo de vuelta y la velocidad máxima del resumen se pueden recalcular desde las series del CSV

### Requirement: Resumen comparativo entre configuraciones

Cuando se simula más de una configuración, el sistema SHALL incluir en el resumen las diferencias de tiempo de vuelta y de velocidad máxima de cada configuración respecto a una configuración de referencia explícita.

#### Scenario: Diferencias respecto a la referencia

- **WHEN** se simulan dos configuraciones y se declara una de ellas como referencia
- **THEN** el resumen indica, para la otra, la diferencia de tiempo de vuelta y de velocidad máxima, y cuál es la referencia

### Requirement: Procedencia declarada de cada dato

El sistema SHALL etiquetar en el resumen el origen de los datos que intervienen: medidos, de ejemplo o derivados del modelo. El sistema SHALL NOT exportar magnitudes que el motor no calcula.

#### Scenario: Etiquetado del resumen

- **WHEN** se lee el JSON de resumen
- **THEN** la curvatura de la pista y la curva de par constan como medidas con su origen, los parámetros del kart como de ejemplo, y el tiempo de vuelta y las velocidades como derivados del modelo

#### Scenario: No se inventan magnitudes

- **WHEN** una magnitud no es producida por el motor de simulación
- **THEN** no aparece en ninguna de las salidas, ni con valor estimado ni con valor nulo

### Requirement: Reproducibilidad y trazabilidad de la ejecución

El sistema SHALL producir resultados numéricos idénticos para entradas idénticas, y SHALL registrar en el resumen la versión del código del motor y las versiones de las dependencias numéricas usadas.

#### Scenario: Dos ejecuciones iguales

- **WHEN** se ejecuta dos veces la misma configuración con los mismos datos de entrada
- **THEN** los valores numéricos de los CSV y de los JSON coinciden

#### Scenario: El resumen identifica el entorno

- **WHEN** se lee el JSON de resumen
- **THEN** incluye el identificador de la versión del motor y las versiones de las dependencias numéricas con las que se calculó

### Requirement: Sólo se deserializan datos de confianza

El sistema SHALL cargar objetos serializados con pickle únicamente desde los datos versionados en el repositorio, y SHALL NOT deserializar pickle recibido de un usuario o de una ruta externa.

#### Scenario: Pickle de origen externo

- **WHEN** se indica como configuración un pickle que no forma parte de los datos del repositorio
- **THEN** la ejecución termina con código distinto de 0 y el mensaje explica que sólo se admiten los datos de confianza del repositorio

### Requirement: Los fallos del motor son visibles

Si el motor falla durante el cálculo, el sistema SHALL terminar con código distinto de 0, SHALL mostrar el error y la configuración que lo provocó, y SHALL NOT dejar un resultado parcial que parezca completo.

#### Scenario: Error durante el cálculo

- **WHEN** el cálculo de una configuración lanza una excepción
- **THEN** el proceso termina con código distinto de 0, el error y la configuración afectada aparecen en la salida, y el directorio de salida no contiene un resumen que presente esa configuración como calculada
