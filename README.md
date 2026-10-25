# Go-kart lap time simulation
This repo contains a simple lap time simulation algorithm, applied to go-karts.

<img src="data/example1result.png"/>

## Method
It's a quasi-steady-state method, vehicle model is a point-mass. Lateral acceleration limit is determined by tyre friction.
Longitudinal acceleration limit is determined by weight distribution, brake config (4 wheels or rear wheels) and tyre friction.
Combined acceleration limit determined by an ellipse, defined by long and lat acc limits. Other model features:
* Apex definition: intersection of ax for max ay with gradient of v for max ay.
* Forward/backward calculation from apexes: longitudinal acceleration at speed (previous +- acc x euler step) and curvature includes slip angle drag, rolling and aerodynamic resistance and track inclination.
* Euler integration used in forward-backwards calculation
* Longitudinal tyre slip in presence of speed dependent engine torque limit (defined by torque curve) is solved using the brentq solver of scipy.optimize.

## Applications
* Example_1 is a simple lap time simulation for a mini kart at the circuit of Mariembourg
* Example_2 contains a scan of final drive ratio options for this circuit.

The curvature data was obtained using gps logging (Mariembourg, 2019). The engine torque characteristic comes from dyno testing.

## Dependencies
Tested for python 3.6 (should work above)
---Packages:---
* matplotlib
* numpy
* math
* pickle (or cPickle for Python 2)
* scipy (specifically for scipy.optimize)
* itertools

## Develop branch
To improve precision of the method, it was attempted to include a two-track model.
Solving the apex solution and acceleration is now done numerically. So far the method was not succesfull.
With the scipy optimizers no reliable optima could be found.



---

# Validación en contenedor (fork)

Esta sección es propia de este fork y no forma parte del proyecto original.
Describe cómo ejecutar el motor sin interfaz gráfica, dentro de un contenedor,
y conservar los resultados.

## Qué hace

`tools/run_sim.py` carga una pista y un kart de los datos versionados en
`data/`, simula una o varias relaciones de transmisión final y escribe en el
directorio de salida, por cada ejecución:

| Archivo | Contenido |
| --- | --- |
| `summary.json` | tiempo de vuelta, velocidad máxima y rpm máxima por configuración, diferencias respecto a la referencia, procedencia de los datos y versiones usadas |
| `series_<etiqueta>.csv` | series a lo largo del circuito: distancia, velocidad simulada, velocidad medida, límite de apex y rpm |
| `speed_<etiqueta>.png` | curva de velocidad simulada, medida y límite de apex |

No abre ventanas ni usa `plt.show()`: funciona en un servidor sin pantalla.

## Construcción

```sh
docker build --build-arg GIT_REV=$(git rev-parse --short HEAD) -t kartlapsim:validate .
```

Comprobaciones rápidas de la imagen:

```sh
docker run --rm kartlapsim:validate id
# esperado: uid=10001(kart) gid=10001(kart)

docker run --rm kartlapsim:validate python -c \
  "import numpy, scipy, matplotlib; print(numpy.__version__, scipy.__version__, matplotlib.__version__)"
# esperado: 1.26.4 1.11.4 3.8.4

docker image inspect kartlapsim:validate \
  --format '{{index .Config.Labels "org.opencontainers.image.revision"}}'
# esperado: la revisión con la que se construyó
```

## Ejecución de la validación

Con compose (construye si hace falta, ejecuta y termina):

```sh
GIT_REV=$(git rev-parse --short HEAD) \
  docker compose -f compose.validate.yaml up --build
echo "código de salida: $?"
```

O directamente:

```sh
docker run --rm \
  -v kartlapsim-output:/app/output \
  kartlapsim:validate \
  python tools/run_sim.py --final-drive 6.5 7.1 --baseline 7.1
```

Opciones del ejecutor (`python tools/run_sim.py --help`):

| Opción | Significado |
| --- | --- |
| `--dataset {mini,kz}` | conjunto de datos de confianza del repositorio (por omisión `mini`) |
| `--final-drive R [R ...]` | una o varias relaciones de transmisión final, rango `[0.5, 20.0]` |
| `--baseline R` | configuración de referencia para las diferencias |
| `--output-dir DIR` | directorio de salida (por omisión `output`) |
| `--label TEXTO` | etiqueta añadida al nombre del directorio de la ejecución |

Códigos de salida: `0` correcto · `1` fallo del motor · `2` entrada inválida ·
`3` faltan los datos de ejemplo.

## Dónde quedan los resultados

En el volumen nombrado `kartlapsim-validate_kartlapsim-output`, bajo
`/app/output/<fecha-hora>/`. Sobreviven al borrado del contenedor.

```sh
# listar
docker run --rm -v kartlapsim-validate_kartlapsim-output:/out alpine ls -R /out

# copiar al host
docker run --rm -v kartlapsim-validate_kartlapsim-output:/out -v "$PWD":/dst \
  alpine cp -r /out /dst/resultados
```

## Registros

```sh
docker compose -f compose.validate.yaml logs
```

Rotan a 3 archivos de 10 MB (`logging` en `compose.validate.yaml`). Los avisos
numéricos de NumPy no se silencian a propósito: si una pista futura trae
velocidad cero, la curvatura saldría infinita y debe verse aquí.

## Resolución de problemas

| Síntoma | Causa | Qué hacer |
| --- | --- | --- |
| `PermissionError: '/app/output/...'` | se montó un **bind mount** del host en `/app/output`; el directorio pertenece a root y el proceso corre como uid 10001 | usar el volumen nombrado (como hace `compose.validate.yaml`) o, si se quiere bind mount, `mkdir -p ./output && sudo chown 10001:10001 ./output`. No ejecutar como root ni usar `chmod 777` |
| `No se encuentran los datos de ejemplo del repositorio` | se ejecutó fuera de la raíz del proyecto, o faltan los `COPY` de `data/` | el ejecutor ya fija su directorio de trabajo; si ocurre dentro del contenedor, reconstruir la imagen |
| `FileNotFoundError: './data/torqueCurveMiniDyno.csv'` | `data/kartMini.pickle` guarda esa ruta **relativa** y la relee en cada `simulate()` | ejecutar con la raíz del proyecto como directorio de trabajo (el ejecutor lo hace solo; `example1_single.py` no) |
| `ModuleNotFoundError: numpy.core` o error al convertir array a escalar | se instaló NumPy 2.x | mantener `numpy==1.26.4` de `requirements-docker.txt`; ver *Limitaciones* |
| El contenedor se reinicia una y otra vez | política de reinicio aplicada a un contenedor que termina | `restart: "no"`; la validación debe terminar |
| `Authentication required` / no hay pantalla | se intentó una figura interactiva | el ejecutor fija el backend `Agg`; no usar `example1_single.py` en el contenedor |

## Equivalencia numérica con la implementación original

El motor original no arranca con NumPy ≥1.24: `kartlapsim/lapsim.py` construía
un array a partir de una lista irregular (escalares mezclados con arrays de
tamaño 1), lo que NumPy ≤1.23 aceptaba creando un array de objetos y NumPy 1.24
convirtió en error. La corrección aplicada aplana explícitamente esos valores,
que es la coerción que la versión antigua hacía de forma implícita.

Como la versión sin corregir no corre sobre la pila fijada, la equivalencia no
se puede comprobar "antes y después" en el mismo entorno. Se comprueba cruzando
dos pilas: una imagen de calibración con **NumPy 1.23.5 y el motor sin tocar**
(`Dockerfile.oracle`, `requirements-oracle.txt`) contra la imagen de validación
con **NumPy 1.26.4 y el motor corregido**.

```sh
# linea base con el motor original
docker build -f Dockerfile.oracle -t kartlapsim:oracle .
docker run --rm -v kartlapsim-oracle:/app/output kartlapsim:oracle \
  python tools/run_sim.py --final-drive 7.1 6.5 --baseline 7.1

# motor corregido
docker build --build-arg GIT_REV=$(git describe --always --dirty) -t kartlapsim:validate .
docker run --rm -v kartlapsim-fix:/app/output kartlapsim:validate \
  python tools/run_sim.py --final-drive 7.1 6.5 --baseline 7.1
```

Resultado medido en `zserver` (Docker 28.0.4, x86_64), comparando los dos
`summary.json` y las dos series completas con tolerancia relativa `1e-12`:

| Magnitud | Original (NumPy 1.23.5) | Corregido (NumPy 1.26.4) | Diferencia relativa |
| --- | --- | --- | --- |
| `laptime_s` rFinal 7.1 | 62.360518117975 | 62.360518117975 | 0 |
| `laptime_s` rFinal 6.5 | 62.299173196705 | 62.299173196705 | 0 |
| `v_max_kph` rFinal 7.1 | 98.455019126730 | 98.455019126730 | 0 |
| `rpm_max` rFinal 7.1 | 14323.242495074523 | 14323.242495074523 | 0 |
| Series completas (6 columnas × 629 puntos × 2 configuraciones) | — | — | 0, arrays idénticos |
| Puntos sin registrar | 1 (índice 432) | 1 (índice 432) | mismos índices |

No "dentro de la tolerancia": bit a bit idénticos. La corrección afecta
únicamente al registro del vector de estado, que el motor escribe pero no
vuelve a leer en el cálculo (`self.xvec` se escribe en `calcAx` y sólo se copia
al histórico en `calcfwdbwd`), por lo que no puede alterar un tiempo de vuelta.

La imagen de calibración es un patrón de medida, no un destino de despliegue:
se puede borrar una vez registrada esta comparación.

## Cómo leer los resultados

- **Las diferencias valen más que los absolutos.** El modelo es punto-masa
  cuasi-estacionario: al comparar dos configuraciones sobre la misma pista y el
  mismo kart, buena parte del error se cancela. El tiempo absoluto no es una
  predicción de cronómetro.
- **Referencia medida**: la vuelta de ejemplo está cronometrada en **62.725 s**
  (`Lap 5 - 1:02.725` en la cabecera del CSV). El modelo da **62.361 s** con la
  configuración de ejemplo: **0.36 s más rápido, un 0.58 %**. No se ajustó
  ningún parámetro para acercarlo.
- **Dato ausente, nunca cero**: las magnitudes derivadas del registro de estado
  se escriben como `nan` en los puntos que el motor no registra. El resumen
  declara cuántos son y en qué índices.
- **`calidad_de_los_datos`** en el resumen trae el rango de la velocidad medida
  y el paso de integración (`ds_medio_m`, `ds_max_m`) para estimar el error sin
  volver a los datos de origen.

## Limitaciones y pruebas pendientes

- **Modelo**: punto-masa cuasi-estacionario. La diferencia entre el tiempo
  simulado y el medido se anota tal cual; no se ajusta ningún parámetro del
  kart ni del modelo para acercarlos. Referencia medida de la vuelta de
  ejemplo: `Lap 5 - 1:02.725`, declarada en la cabecera de
  `data/trackMariembourgMini.csv`; la figura del autor original está en
  `data/example1result.png`.
- **NumPy anclado en 1.x**: `data/kartMini.pickle` referencia
  `numpy.core.multiarray` y el motor pasa arrays de tamaño 1 donde se esperan
  escalares (`kartlapsim/lapsim.py`). Salir de esa serie exige regenerar los
  karts y revisar el motor.
- **`kartlapsim/utils/makekart.py` no funciona**: importa `save_file`, que no
  existe en `kartlapsim/utils/helperfunctions.py` (allí está `save_object`).
  Afecta a regenerar karts, no a esta validación.
- **`Kart.rFinal` no es una propiedad**: `Kart.__init__` asigna `_rFinal` pero
  no define `rFinal`. Cargar los karts de ejemplo funciona porque el pickle
  guarda el atributo; construir un `Kart` nuevo y llamar a `ini()` sin asignar
  `rFinal` fallaría.
- **El conjunto `kz` no funciona**, y no por la corrección de NumPy: en la
  pista `data/trackMariembourgKz.csv` el motor detecta **0 ápices** (121 en la
  pista `mini`), así que `calcfwdbwd()` llama a `np.argmin` sobre un array
  vacío y falla. Comprobado con el motor original sobre NumPy 1.23.5: es un
  defecto preexistente del upstream. Queda sin diagnosticar a fondo.
- **`rpm_sim` supone relación de caja unitaria** (`rTrans = 1`): la conversión
  `nAxle · rFinal · 60 / 2π` sólo vale con transmisión directa. Con caja de
  cambios la serie no se exporta y el resumen dice por qué. Esa rama **no está
  verificada con datos reales**, porque el único kart de caja disponible es el
  `kz`, que falla antes por el defecto anterior.
- **Error de integración**: Euler con paso igual al muestreo de la pista,
  `ds` medio 2.09 m y máximo 3.00 m sobre 628 pasos. Es inherente al método.
- **Un punto por vuelta sin registrar**: `calcfwdbwd()` recorre todos los
  índices salvo el del ápice más lento, de modo que ese punto del registro de
  estado queda sin calcular. Se exporta como `nan`.
- **Reproducibilidad**: se exige y se comprueba dentro de la misma imagen y
  arquitectura. Entre `amd64` y `arm64` puede haber diferencias en los últimos
  bits por la BLAS de la rueda de NumPy.
- **Sin licencia en el proyecto original**: no hay `LICENSE` ni `COPYING` en
  `Svennevs/kartlapsim`. Mientras no se aclare con el autor, la imagen no se
  publica en ningún registro de acceso público; se construye en destino.
- **Pickles sólo de confianza**: el ejecutor no acepta rutas de pickle
  externas, porque deserializar un pickle ejecuta código. Las configuraciones
  propias usarán un formato validado (JSON) en un cambio posterior.
- **Despliegue**: `compose.validate.yaml` es para CLI, no es el stack de
  Portainer. La modalidad del entorno (Standalone o Swarm), el proxy inverso,
  el dominio y la autenticación se deciden en el cambio siguiente.
