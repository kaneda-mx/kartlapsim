# Proposal

## Why

La validación en contenedor demostró que el motor **no corre** con las dependencias fijadas. Evidencia (imagen `kartlapsim:validate`, revisión `328520b-dirty`, NumPy 1.26.4, en `zserver`):

```
File "/app/kartlapsim/lapsim.py", line 106, in calcAx
  np.put(self.xvec, range(len(statevars)), list(statevars.values()))
ValueError: setting an array element with a sequence. The requested array has
an inhomogeneous shape after 1 dimensions. The detected shape was (10,) +
inhomogeneous part.
```

`example1_single.py`, el ejemplo original del upstream sin modificar, falla en la misma línea con el mismo error: el defecto es del motor, no del ejecutor headless. `statevars.values()` mezcla escalares con arrays de forma `(1,)` (porque `track.curv` es `(N,1)`); NumPy ≤1.23 aceptaba esa lista irregular creando un array de objetos con aviso de deprecación, y NumPy 1.24 lo convirtió en error.

Sin este arreglo no hay ningún resultado que validar, y las tareas 3.3 a 5.6 del cambio `validate-engine-in-docker` quedan bloqueadas.

## What Changes

- **Arreglo mínimo en `kartlapsim/lapsim.py`**: aplanar a escalar los valores del vector de estado antes de `np.put`, que es exactamente la coerción que NumPy ≤1.23 hacía de forma implícita. Una línea.
- **Validación cruzada contra la implementación original**: se construye una imagen oráculo (`Dockerfile.oracle` + `requirements-oracle.txt`, NumPy 1.23.5, **motor sin tocar**) donde el código original sí corre, y se compara su resultado numérico con el del motor parcheado bajo NumPy 1.26.4. Sin esa comparación, "el parche no cambió nada" no se puede afirmar: la versión sin parche no arranca en 1.26.
- **Curación de las estadísticas derivadas del registro de estado**:
  - Los puntos que el motor nunca registra se marcan como dato ausente, no como cero. `calcfwdbwd` recorre todos los índices salvo `idxSlowestPoint`, así que `xsol` queda en ceros en el ápice más lento y `rpm_sim` tendría un 0 espurio.
  - El resumen declara el rango de las entradas medidas y el paso de integración, para que quien lea el JSON pueda juzgar el error en lugar de confiar a ciegas.
  - `rpm_sim` se declara válido sólo con transmisión directa (`rTrans = 1`); con caja de cambios la conversión `nAxle·rFinal·60/2π` no aplica.
- **Un fallo total no deja directorio vacío** en el volumen de salida.

Fuera de alcance: cualquier cambio en la física del modelo, la migración a NumPy 2.x, y arreglar `makekart.py`.

## Capabilities

### New Capabilities

- `engine-numerics`: integridad numérica del motor frente a las dependencias fijadas y honestidad de las estadísticas que se derivan de su registro de estado — equivalencia con la implementación original, huecos declarados y validez de cada magnitud derivada.

### Modified Capabilities

Ninguna: `simulation-run` y `container-packaging` siguen siendo deltas sin archivar del cambio `validate-engine-in-docker`, y sus requisitos no cambian.

## Impact

**Archivos**: `kartlapsim/lapsim.py` (una línea), `tools/run_sim.py` (curación del resumen y de las series), nuevos `Dockerfile.oracle` y `requirements-oracle.txt`, `README.md` (limitaciones actualizadas).

**Por qué el parche no puede alterar la física**: `self.xvec` se escribe en `calcAx` (línea 106) y se lee únicamente en las líneas 66 y 68 para copiarlo al registro, del que sale `xsol` (línea 74). `calcAx` devuelve `ax` calculado desde `self.x.*`, no desde `xvec`, y el tiempo de vuelta sale de `vqss`. Es decir: la línea que falla es un registro, no un paso de cálculo. La única estadística exportada que depende de ella es `rpm_sim`, que se toma de `xsol[:,9]`.

**Riesgo asumido**: la imagen oráculo depende de que NumPy 1.23.5 siga aceptando la conversión irregular. Si no la aceptara, la comparación no se puede hacer y hay que buscar una versión anterior; eso se descubre al construirla, no después.

**Lo que este cambio no mejora**: la fidelidad del modelo. Es punto-masa cuasi-estacionario con integración de Euler y paso de 2,09 m de media (3,00 m máximo) sobre 628 pasos. El error de integración es inherente al método; este cambio sólo garantiza que el resultado sea el que el autor original obtenía y que los huecos se vean.
