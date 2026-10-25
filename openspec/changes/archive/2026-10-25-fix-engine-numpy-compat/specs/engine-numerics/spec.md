# Spec Delta

## Purpose

Garantiza que el motor produzca con las dependencias fijadas el mismo resultado numérico que la implementación original del autor, y que cada estadística derivada de su registro de estado declare su validez y sus huecos en lugar de aparentar un dato que no existe.

## ADDED Requirements

### Requirement: El motor completa el cálculo con las dependencias fijadas

El motor SHALL completar una simulación con las versiones declaradas en el archivo de dependencias de la imagen, sin depender de conversiones implícitas de secuencias irregulares a arrays de objetos.

#### Scenario: Simulación con la pila numérica fijada

- **WHEN** se ejecuta una simulación con las versiones fijadas de NumPy, SciPy y Matplotlib
- **THEN** el cálculo termina sin excepción y produce un tiempo de vuelta finito y positivo

#### Scenario: El ejemplo original del upstream también completa

- **WHEN** se ejecuta el ejemplo original del repositorio de origen con esas mismas versiones
- **THEN** el cálculo termina sin excepción

### Requirement: Equivalencia numérica con la implementación original

El resultado del motor corregido SHALL coincidir con el de la implementación original ejecutada sobre una versión de NumPy donde ésta sí funciona, para la misma pista, el mismo kart y la misma relación de transmisión final.

#### Scenario: Comparación cruzada contra la implementación original

- **WHEN** se simula la misma configuración con el motor corregido sobre la pila fijada y con el motor original sobre la pila donde éste funciona
- **THEN** el tiempo de vuelta, las velocidades y el registro de estado coinciden dentro de la tolerancia de redondeo declarada, y la comparación queda registrada como evidencia

#### Scenario: Divergencia numérica

- **WHEN** alguna magnitud comparada difiere más allá de esa tolerancia
- **THEN** la corrección se considera rechazada y no se continúa con la validación

### Requirement: Los huecos del registro de estado se declaran

Los puntos del circuito para los que el motor no registra estado SHALL exportarse como dato ausente, y SHALL NOT exportarse como valor cero ni como valor interpolado.

#### Scenario: Punto no registrado en el ápice más lento

- **WHEN** se exportan las series de un circuito cerrado y el registro de estado no cubre el punto más lento
- **THEN** las magnitudes derivadas del registro aparecen en ese punto como dato ausente, y el resumen indica cuántos puntos quedaron sin registrar

### Requirement: Cada magnitud derivada declara su validez

Las magnitudes derivadas del registro de estado SHALL declarar la condición bajo la cual son válidas, y SHALL NOT exportarse cuando esa condición no se cumple.

#### Scenario: Revoluciones de motor con transmisión directa

- **WHEN** se exporta la serie de revoluciones de motor para un kart de transmisión directa
- **THEN** el resumen declara que la conversión supone relación de caja unitaria

#### Scenario: Kart con caja de cambios

- **WHEN** la configuración simulada tiene más de una relación de caja
- **THEN** las revoluciones de motor no se exportan, y el resumen indica por qué

### Requirement: El resumen permite juzgar el error numérico

El resumen SHALL declarar el rango de las entradas medidas y el paso de integración utilizado, de modo que quien lea los resultados pueda estimar su error sin inspeccionar los datos de origen.

#### Scenario: Metadatos de calidad en el resumen

- **WHEN** se lee el resumen de una ejecución
- **THEN** incluye la velocidad medida mínima y máxima, el número de puntos y el paso de distancia medio y máximo

### Requirement: Un fallo total no deja artefactos

Cuando ninguna configuración se puede calcular, la ejecución SHALL NOT dejar directorios ni archivos de resultados en el destino de salida.

#### Scenario: Todas las configuraciones fallan

- **WHEN** ninguna configuración solicitada completa el cálculo
- **THEN** el destino de salida queda sin directorio ni archivo de esa ejecución, y el proceso termina con código distinto de 0
