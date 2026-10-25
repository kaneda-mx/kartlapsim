# Design

## Context

Motivación y evidencia en `proposal.md`. Lo que condiciona el enfoque:

- La línea que falla es un **registro**, no un paso de cálculo (análisis de `xvec` en `proposal.md` → *Impact*). Eso acota el riesgo del parche a una sola estadística exportada: `rpm_sim`.
- **No hay línea base disponible**: la implementación original no arranca con NumPy 1.26.4, así que no se puede comparar "antes y después" en la misma pila. La comparación tiene que cruzar dos pilas.
- NumPy 1.23.5 es la última serie que acepta la conversión irregular (deprecada desde 1.20, error desde 1.24) y es compatible con `scipy==1.11.4` y `matplotlib==3.8.4`, que requieren NumPy ≥1.21.
- El motor se ejecuta en `zserver` (Docker 28.0.4, Standalone, `x86_64`), donde la imagen de validación ya construye en 36 s. Las dos imágenes se construyen y comparan en la misma máquina y arquitectura, de modo que la BLAS es la misma y una diferencia numérica sólo puede venir del código.

## Goals / Non-Goals

**Goals:**

- Que el motor corra con la pila fijada produciendo el resultado del autor original, demostrado y no asumido.
- Que las estadísticas derivadas del registro de estado no mientan: hueco declarado, validez declarada, error estimable.

**Non-Goals:**

- No se cambia la física: ni el modelo, ni el paso de integración, ni la definición de ápice, ni los parámetros del kart.
- No se migra a NumPy 2.x ni se regeneran los pickles.
- No se corrige `makekart.py`.
- La imagen oráculo no es un destino de despliegue; es un patrón de calibración que se descarta.

## Decisions

### 1. Aplanar en el punto del registro, no cambiar los tipos del estado

```python
# kartlapsim/lapsim.py:106
np.put(self.xvec, range(len(statevars)), [np.ravel(v)[0] for v in statevars.values()])
```

`np.ravel(v)[0]` es válido tanto para un escalar como para un array de tamaño 1, y es la coerción que NumPy ≤1.23 aplicaba al asignar un array de objetos dentro de un array de punto flotante. Los diez campos del estado están asignados cuando se llega a esa línea, así que no hay `None` que aplanar.

*Alternativa descartada:* convertir cada campo a escalar en su origen (`self.x.ay = float(...)`, etc.). Toca seis asignaciones dentro del cálculo, donde una conversión mal puesta sí podría alterar un resultado. El objetivo es el diff más pequeño posible sobre el código del autor.

*Alternativa descartada:* sustituir `np.put` por una asignación vectorizada. Equivalente, pero cambia más texto y no aporta nada.

### 2. Imagen oráculo con el motor sin tocar

`Dockerfile.oracle` es el mismo `Dockerfile` con `requirements-oracle.txt` (NumPy 1.23.5), y se construye **antes** de aplicar el parche, de forma que su capa de código contiene el motor original tal como está en la revisión `328520b`. El ejecutor headless es el mismo en las dos imágenes, para que la única variable sea el par (motor, NumPy).

Ambas ejecuciones usan la misma pista, el mismo kart y la misma relación de transmisión final, y se comparan los archivos de salida.

### 3. Tolerancia de comparación declarada

La comparación se hace sobre el tiempo de vuelta, las series de velocidad y la serie de revoluciones, con tolerancia relativa de `1e-12` (precisión de doble sin reordenamiento de operaciones). No se usa una tolerancia laxa: el parche no reordena ninguna operación aritmética, así que lo honesto es exigir igualdad salvo redondeo. Una diferencia mayor significa que el parche cambió algo y se rechaza.

Los puntos no registrados se excluyen de la comparación de revoluciones, porque en la implementación original son ceros y en la corregida son dato ausente: ésa es una diferencia buscada y no un desacuerdo numérico. Se compara que el conjunto de índices afectados sea el mismo.

### 4. Dato ausente, no cero

El ejecutor detecta las filas del registro que quedaron íntegramente en cero y escribe `NaN` en las magnitudes derivadas de ellas, además de contar cuántas fueron en el resumen. Se hace en el ejecutor y no en el motor porque es una decisión de presentación: el motor sigue devolviendo lo que devolvía, y el diff sobre el código del autor se mantiene en una línea.

`NaN` en CSV se escribe como la cadena `nan`, que Pandas y la mayoría de los lectores interpretan como ausente; el resumen lo declara explícitamente para que un consumidor que no lo sepa no lo lea como texto.

### 5. Revoluciones sólo con transmisión directa

Si la configuración tiene más de una relación de caja, la serie de revoluciones de motor no se exporta y el resumen dice por qué. Es preferible a exportar un número que parece correcto y no lo es.

## Risks / Trade-offs

- **NumPy 1.23.5 podría no aceptar la conversión irregular** → se descubre al construir la imagen oráculo, antes de aplicar el parche. Si ocurre, se prueba 1.22.x; si ninguna sirve, la equivalencia se argumenta leyendo el código en lugar de medirla, y eso se declara como limitación en vez de disimularlo.
- **La comparación demuestra equivalencia sólo para las configuraciones comparadas** → se compara al menos la del ejemplo (`rFinal = 7.1`) y una del barrido, no una sola.
- **El `NaN` puede romper un consumidor ingenuo** del CSV → el resumen declara la convención y el número de puntos afectados; es preferible a un cero que se promedia sin que nadie se entere.
- **El parche se aparta del upstream** → es una línea, aislada y comentada, con el motivo y la versión de NumPy que la exige, de modo que traer cambios del original siga siendo posible.

## Migration Plan

El parche no tiene estado que migrar. Revertir es `git revert` de una línea; la imagen oráculo y sus dos archivos se pueden borrar sin consecuencias una vez registrada la comparación.
