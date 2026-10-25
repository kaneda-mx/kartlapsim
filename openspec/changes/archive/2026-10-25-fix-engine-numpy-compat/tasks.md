# Tasks

## 1. Línea base con la implementación original

- [x] 1.1 Crear `requirements-oracle.txt` con `numpy==1.23.5` y las mismas versiones de SciPy y Matplotlib que la imagen de validación. Verificar: las tres versiones aparecen fijadas y sólo difiere NumPy.
- [x] 1.2 Crear `Dockerfile.oracle`, copia del `Dockerfile` que instala `requirements-oracle.txt`, con un comentario que explique que es un patrón de calibración y no un destino de despliegue. Verificar: el archivo sólo difiere en el archivo de dependencias y en ese comentario.
- [x] 1.3 Construir la imagen oráculo **antes** de tocar el motor, de modo que contenga el código original. Verificar: la construcción termina y `pip` reporta `numpy-1.23.5`.
- [x] 1.4 Ejecutar la simulación de referencia (`rFinal = 7.1`) con la imagen oráculo. Verificar: termina con código 0, y se registra el tiempo de vuelta obtenido con el motor original.
- [x] 1.5 Ejecutar también una segunda configuración del barrido (`rFinal = 6.5`) con la imagen oráculo. Verificar: termina con código 0 y se registra su tiempo de vuelta.

## 2. Corrección del motor

- [x] 2.1 Aplicar en `kartlapsim/lapsim.py` el aplanado del vector de estado antes de `np.put`, con un comentario que indique la versión de NumPy que lo exige. Verificar: `git diff kartlapsim/lapsim.py` muestra una sola línea de código cambiada.
- [x] 2.2 Reconstruir la imagen de validación con el motor corregido. Verificar: la construcción termina y `pip` reporta `numpy-1.26.4`.
- [x] 2.3 Ejecutar el ejemplo original del upstream (`example1_single.py`) dentro de la imagen corregida. Verificar: termina con código 0, lo que confirma que el arreglo es del motor y no del ejecutor.
- [x] 2.4 Ejecutar las dos mismas configuraciones (`7.1` y `6.5`) con la imagen corregida. Verificar: terminan con código 0 y se registran sus tiempos de vuelta.

## 3. Validación cruzada

- [x] 3.1 Comparar numéricamente los resultados de las dos pilas para `rFinal = 7.1`: tiempo de vuelta, serie de velocidad simulada y serie de revoluciones, con tolerancia relativa `1e-12`, excluyendo los puntos no registrados. Verificar: se pega la diferencia máxima observada por magnitud.
- [x] 3.2 Repetir la comparación para `rFinal = 6.5`. Verificar: se pega la diferencia máxima observada.
- [x] 3.3 Comprobar que el conjunto de puntos no registrados es el mismo en las dos pilas. Verificar: los índices coinciden y se registra cuántos son.
- [x] 3.4 Si alguna diferencia supera la tolerancia, detener la validación y reportarla sin continuar. Verificar: queda escrito que la comparación pasó o que se detuvo, con los números.
- [x] 3.5 Registrar la comparación en el `README` como evidencia de equivalencia, con las versiones, las órdenes exactas y las diferencias máximas. Verificar: la sección permite repetir la comparación desde cero.

## 4. Curación de las estadísticas derivadas

- [x] 4.1 Detectar en el ejecutor las filas del registro de estado que quedaron íntegramente en cero y escribir `NaN` en las magnitudes derivadas de ellas, en lugar de cero. Verificar: en el CSV, el punto del ápice más lento muestra `nan` en revoluciones y no `0`.
- [x] 4.2 Añadir al resumen el número de puntos sin registrar y la convención de dato ausente. Verificar: el JSON declara ambos y el número coincide con las filas `nan` del CSV.
- [x] 4.3 Añadir al resumen el rango de las entradas medidas y el paso de integración: velocidad medida mínima y máxima, número de puntos, paso de distancia medio y máximo. Verificar: los valores del JSON coinciden con los calculados directamente sobre el CSV de pista.
- [ ] 4.4 Declarar en el resumen que las revoluciones suponen relación de caja unitaria, y no exportarlas cuando la configuración tenga más de una relación de caja. Verificar: con el conjunto `mini` se exportan con su advertencia; con una configuración de caja, no se exportan y el resumen dice por qué.
- [x] 4.5 Evitar que un fallo total deje directorio de salida: crear el directorio de la ejecución al escribir el primer archivo. Verificar: una ejecución con entrada que falla deja el volumen sin directorio nuevo.
- [x] 4.6 Actualizar en el `README` la lista de limitaciones con la convención de dato ausente, la validez de las revoluciones y el error de integración declarado. Verificar: cada punto aparece con su consecuencia práctica.

## 5. Cierre

- [x] 5.1 Volver a ejecutar la validación completa con el ejecutor curado y confirmar que el resumen trae todas las claves nuevas. Verificar: se pega el `summary.json` resultante.
- [x] 5.2 Desbloquear el cambio `validate-engine-in-docker` retomando sus tareas 3.3 a 5.6. Verificar: su progreso avanza y se pegan los resultados.
