# Proposal

## Why

El fork tiene `Dockerfile` y `requirements-docker.txt` (commit `328520b`), pero no existe evidencia de que la imagen construya, de que el motor funcione con NumPy/SciPy/Matplotlib actuales, ni de un resultado conservado: los dos ejemplos dibujan con `plt.show()` y no guardan nada, así que una ejecución en contenedor no deja ningún artefacto que inspeccionar ni comparar.

Sin una ejecución headless reproducible y archivada no se puede construir la aplicación web encima (no hay contrato de datos), ni detectar regresiones cuando se toquen las versiones fijadas. Este cambio es el mínimo que convierte "el contenedor arranca" en "el motor produce resultados verificables".

## What Changes

- **Ejecutor headless nuevo** (`tools/run_sim.py`): carga la pista y el kart de ejemplo del repositorio, ejecuta `Lapsim.simulate()` para una o varias relaciones de transmisión final (`rFinal`) y escribe los resultados en un directorio de salida. No usa ventanas ni `plt.show()`.
- **Exportación de resultados**: por ejecución, un CSV de series por distancia, un JSON de resumen (tiempo de vuelta, velocidad máxima, rpm máxima, diferencias entre configuraciones) y un PNG de velocidad sobre el circuito.
- **Procedencia explícita de los datos**: cada salida declara qué es medido (curvatura GPS Mariembourg 2019, curva de par de banco), qué es de ejemplo (parámetros de `kartMini.pickle`) y qué es derivado del modelo (todo lo simulado). Sin este campo la aplicación web no podría etiquetar nada honestamente.
- **Dockerfile revisado**: directorio de salida creado en la imagen y propiedad del usuario sin privilegios, `CMD` apuntando al ejecutor headless, mismo usuario `kart` (uid 10001) y mismas versiones fijadas. Se justifica cada decisión en `design.md`.
- **`.dockerignore` nuevo**: el contexto de build hoy incluiría `.git/`, `openspec/`, `.claude/` y `data/example1result.png`.
- **`compose.validate.yaml` nuevo**: servicio de validación de un solo disparo, `restart: "no"`, con volumen para `/app/output`. Es para ejecutar por CLI en la VM o en la MacBook; **no** es todavía el stack de Portainer.
- **README**: sección de construcción, ejecución de la validación, dónde quedan los resultados, lectura de logs, resolución de problemas y lista de limitaciones y pruebas pendientes.
- **Dependencias**: se mantienen `numpy==1.26.4`, `scipy==1.11.4`, `matplotlib==3.8.4` y se documenta por qué NumPy debe quedar en la serie 1.x (abajo, en Impact).
- **El motor no se modifica** (`kartlapsim/*.py`, `example1_single.py`, `example2_finaldrivescan.py`, `requirements.txt` quedan intactos). Si la validación demuestra un fallo real, el arreglo mínimo se propone aparte con la traza como evidencia.

Fuera de alcance en este cambio: interfaz web, stack de Portainer, proxy inverso y HTTPS, configuración del kart real, modelo 3D del iPad.

## Capabilities

### New Capabilities

- `simulation-run`: cómo se lanza una simulación de vuelta sin interfaz gráfica, qué entradas acepta, qué resultados escribe, cómo se etiqueta la procedencia de cada dato y cómo falla de forma visible.
- `container-packaging`: el contrato de la imagen y del contenedor de validación — dependencias fijadas, usuario sin privilegios, directorio de salida escribible, backend gráfico no interactivo, terminación del proceso y contexto de build.

### Modified Capabilities

Ninguna: el proyecto no tiene especificaciones previas (`openspec list --specs` no devuelve nada).

## Impact

**Archivos**: `Dockerfile` (modificado), `README.md` (sección añadida), y nuevos `tools/run_sim.py`, `.dockerignore`, `compose.validate.yaml`. Sin cambios en `kartlapsim/`, en los dos `example*.py`, ni en `requirements.txt`.

**Dependencias**: `data/kartMini.pickle` es un pickle protocolo 3 que referencia `numpy.core.multiarray` y la clase `kartlapsim.kart.Kart`; `numpy.core` dejó de existir con ese nombre en NumPy 2.x. Además el motor pasa arrays de tamaño 1 donde se esperan escalares (`min(vnew, self.vApexSol[idx], ...)` en `lapsim.py`, y los límites que recibe `brentq`), lo que NumPy 1.25+ avisa como deprecación y NumPy 2.x convierte en error. Por eso la fijación en `numpy==1.26.4` es deliberada y subir a 2.x es un cambio aparte con su propia validación.

**Seguridad de datos**: los pickles sólo se cargan desde el repositorio. Ningún pickle de origen externo entra en el flujo; la configuración de karts propios usará JSON validado en un cambio posterior.

**Hallazgos de la inspección que condicionan el plan**:
- El repositorio original **no incluye archivo de licencia** (ni `LICENSE` ni `COPYING`). Redistribuir la imagen en un registro público queda bloqueado hasta aclararlo con el autor; la validación local no lo requiere.
- `kartlapsim/utils/makekart.py` importa `save_file`, que no existe en `helperfunctions.py` (allí está `save_object`): el script que regenera los pickles está roto en master. No afecta a esta validación porque los pickles ya están versionados, sí afecta a la configuración del kart real.
- `Kart.__init__` asigna `_rFinal` pero no define la propiedad `rFinal`; el pickle guarda ambos atributos, así que cargar el ejemplo funciona y `kart.rFinal = x` (como en `example2`) también, pero construir un `Kart` nuevo y llamar a `ini()` sin asignar `rFinal` fallaría.
- El pickle guarda la ruta **relativa** `./data/torqueCurveMiniDyno.csv`, que se vuelve a leer en cada `simulate()`: el ejecutor sólo funciona con el directorio de trabajo en la raíz del proyecto (`/app` en la imagen).
- La pista de ejemplo trae su propia referencia medida: `trackMariembourgMini.csv` declara `Lap 5 - 1:02.725`, y `data/example1result.png` es la figura del autor original. Ambas sirven como criterio de aceptación sin inventar cifras.

**Entorno de trabajo**: la sesión donde se planificó esto no tiene Python ni Docker (`python3`, `docker` y `/var/run/docker.sock` no existen), por lo que ninguna tarea de construcción o ejecución puede marcarse hecha aquí: las ejecuta el usuario en su VM o MacBook y el resultado se pega como evidencia.
