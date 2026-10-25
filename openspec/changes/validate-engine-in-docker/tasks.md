# Tasks

> El entorno de planificación no tiene Python ni Docker. Las tareas marcadas **[VM/Mac]** las ejecuta el usuario en su VM o en la MacBook y se cierran pegando la salida real: código de salida, listado de archivos o traza del error. Nada de eso se da por hecho sin esa evidencia.

## 1. Ejecutor headless

- [x] 1.1 Crear `tools/run_sim.py` que fije `matplotlib.use("Agg")` antes de importar `pyplot`, deduzca la raíz del proyecto desde `__file__`, haga `chdir` a ella y aborte con mensaje explícito y código distinto de 0 si no existen `data/trackMariembourgMini.csv` o `data/kartMini.pickle`. Verificar: ejecutarlo desde otro directorio (`python tools/run_sim.py --help` desde `/tmp`) y comprobar que no falla por rutas.
- [x] 1.2 Añadir interfaz de línea de órdenes con `--final-drive` (uno o varios valores, por omisión el del kart de ejemplo), `--baseline` (configuración de referencia), `--output-dir` (por omisión `output/`) y `--label`. Verificar: `python tools/run_sim.py --help` lista las cuatro opciones con sus valores por omisión.
- [x] 1.3 Validar las entradas antes de simular: rechazar valores no numéricos, no finitos, `<= 0` o fuera del rango documentado, nombrando el valor y el rango, sin escribir nada en la salida. Verificar: `python tools/run_sim.py --final-drive 0` y `--final-drive abc` terminan con código distinto de 0 y `output/` no gana ningún archivo.
- [x] 1.4 Cargar pista y kart sólo desde los datos del repositorio y rechazar cualquier ruta de pickle externa con mensaje explícito. Verificar: pasar un pickle de fuera del repositorio termina con código distinto de 0 y el mensaje dice que sólo se admiten los datos de confianza del repositorio.
- [x] 1.5 Ejecutar la simulación por cada `rFinal` solicitada reutilizando el `Track` cargado y asignando `kart.rFinal` como hace `example2_finaldrivescan.py`, sin modificar nada de `kartlapsim/`. Verificar: `git status` no muestra cambios en `kartlapsim/`, `example1_single.py`, `example2_finaldrivescan.py` ni `requirements.txt`.
- [x] 1.6 Escribir por configuración `series_<etiqueta>.csv` con distancia, velocidad simulada, velocidad medida de referencia, velocidad de apex y rpm, y `speed_<etiqueta>.png` con la curva de velocidad sobre el circuito. Verificar: el CSV abre con cabecera y sin filas vacías, y el PNG se genera con tamaño mayor que cero.
- [x] 1.7 Escribir un único `summary.json` por ejecución con: configuraciones simuladas, tiempo de vuelta, velocidad máxima y rpm máxima de cada una, diferencias respecto a la referencia, bloque de procedencia (medido / de ejemplo / derivado del modelo) y versiones de revisión del repositorio, Python, NumPy, SciPy y Matplotlib. Verificar: leer el JSON y comprobar que están todas esas claves y que ninguna métrica es `null`.
- [x] 1.8 Hacer que un fallo del motor termine con código distinto de 0, imprima la configuración afectada y no deje en `summary.json` esa configuración como calculada. Verificar: forzar un fallo (por ejemplo `--final-drive` con un valor absurdamente alto admitido por el rango) y comprobar código de salida y contenido del JSON.
- [x] 1.9 Documentar el uso del ejecutor en su propio `--help` y en un docstring de cabecera que indique que debe ejecutarse con la raíz del proyecto como directorio de trabajo y por qué (la ruta relativa guardada dentro del pickle). Verificar: el texto de ayuda explica las opciones y la restricción de directorio.
- [x] 1.10 **[VM/Mac]** Primera ejecución del motor fuera del contenedor con las versiones fijadas (entorno virtual con `requirements-docker.txt`), una sola `rFinal`. Verificar: pegar el código de salida y el tiempo de vuelta obtenido, o la traza completa si falla en `brentq` / `np.loadtxt` como anticipa `design.md` → *Risks*.

## 2. Contexto de construcción e imagen

- [x] 2.1 Crear `.dockerignore` que excluya `.git/`, `openspec/`, `.claude/`, `__pycache__/`, `output/`, `data/example1result.png` y archivos de entorno local. Verificar: `docker build` imprime un contexto enviado notablemente menor que el tamaño del repositorio con `.git/`.
- [x] 2.2 Modificar el `Dockerfile` para crear `/app/output` con propiedad `kart:kart` antes de `USER kart`, copiar `tools/` y cambiar `CMD` al ejecutor headless, conservando usuario, variables y versiones actuales. Verificar: revisar el diff del `Dockerfile` y que no cambia ninguna versión fijada.
- [x] 2.3 Añadir al `Dockerfile` una etiqueta con la revisión del repositorio desde la que se construye (argumento de construcción con la revisión de git). Verificar: `docker image inspect` muestra la etiqueta con la revisión usada.
- [x] 2.4 Comentar en el `Dockerfile` por qué `--only-binary=:all:`, por qué NumPy se queda en 1.x y por qué `/app/output` se crea en la imagen. Verificar: los tres motivos aparecen junto a las líneas correspondientes.

## 3. Construcción y validación en contenedor

- [x] 3.1 **[VM/Mac]** Construir la imagen (`docker build --build-arg GIT_REV=$(git rev-parse --short HEAD) -t kartlapsim:validate .`). Verificar: pegar las últimas líneas de la construcción y la salida de `docker images kartlapsim:validate`.
- [x] 3.2 **[VM/Mac]** Comprobar el entorno dentro de la imagen: usuario sin privilegios y versiones instaladas (`docker run --rm kartlapsim:validate id` y un `python -c` con las versiones de NumPy, SciPy y Matplotlib). Verificar: `uid=10001(kart)` y las tres versiones exactas de `requirements-docker.txt`.
- [x] 3.3 **[VM/Mac]** Ejecutar la validación de una sola configuración con volumen nombrado en `/app/output`. Verificar: el contenedor termina solo, `docker wait` o `docker inspect` devuelve código 0 y el volumen contiene `summary.json`, el CSV y el PNG.
- [x] 3.4 **[VM/Mac]** Comprobar que la escritura funciona sin privilegios y que los resultados sobreviven al borrado del contenedor. Verificar: tras `docker rm` del contenedor, listar el volumen y ver los archivos intactos.
- [x] 3.5 Documentar en el `README` la sección de construcción y validación con las órdenes exactas de 3.1 a 3.4 y la salida esperada. Verificar: seguir el README desde cero en una máquina limpia reproduce los mismos archivos.

## 4. Contenedor de validación declarativo

- [x] 4.1 Crear `compose.validate.yaml` con un único servicio de un disparo: `restart: "no"`, volumen nombrado en `/app/output`, `logging` con rotación de tamaño y número de archivos, y límites de memoria y CPU. Verificar: `docker compose -f compose.validate.yaml config` valida sin avisos.
- [x] 4.2 **[VM/Mac]** Ejecutar la validación con compose y confirmar que el servicio termina y no se reinicia. Verificar: `docker compose -f compose.validate.yaml up` termina por sí solo, el código de salida es 0 y el contenedor queda en estado `exited` sin reintentos.
- [x] 4.3 **[VM/Mac]** Comprobar el comportamiento ante fallo: forzar una entrada inválida y confirmar que el código de salida no es 0, el error queda en `docker compose logs` y no hay bucle de reinicio. Verificar: pegar el código de salida y el fragmento de registro.
- [x] 4.4 Documentar en el `README` el uso del compose, dónde quedan los registros, cómo consultar el volumen y la resolución de problemas conocidos: `Permission denied` al usar bind mount en lugar de volumen nombrado (con la orden `chown 10001:10001` en el host), ausencia de pantalla, y falta de `data/` al ejecutar desde otro directorio. Verificar: cada problema listado trae su orden de diagnóstico y su solución.
- [x] 4.5 Dejar escrito en el `README` que este archivo **no** es el stack de Portainer y que la estrategia de despliegue depende de la modalidad (Standalone o Swarm), todavía sin confirmar. Verificar: la nota aparece junto a las órdenes de compose.

## 5. Aceptación del motor y limitaciones

- [x] 5.1 **[VM/Mac]** Ejecutar la comparación de dos relaciones de transmisión final en una sola ejecución, con una declarada como referencia. Verificar: `summary.json` trae las dos configuraciones, sus métricas y las diferencias respecto a la referencia.
- [x] 5.2 **[VM/Mac]** Repetir el barrido de `rFinal` de `example2_finaldrivescan.py` (de 6.5 a 7.3) con el ejecutor headless. Verificar: los tiempos de vuelta varían de forma monótona o con un mínimo claro, y se pega la tabla obtenida.
- [x] 5.3 **[VM/Mac]** Comprobar la reproducibilidad dentro de la misma imagen: dos ejecuciones idénticas y comparación numérica de sus CSV y JSON. Verificar: las métricas coinciden; si hay diferencias, se documentan con su magnitud.
- [x] 5.4 **[VM/Mac]** Contrastar el resultado con las referencias ya versionadas: el tiempo medido `1:02.725` de la cabecera de `data/trackMariembourgMini.csv` y la figura `data/example1result.png`. Verificar: anotar el tiempo simulado y su diferencia con el medido, sin ajustar ningún parámetro del kart ni del modelo para acercarlos.
- [x] 5.5 Escribir en el `README` la lista explícita de limitaciones y pruebas pendientes: modelo punto-masa cuasi-estacionario, diferencia observada frente al dato medido, NumPy anclado en 1.x por el pickle y las conversiones de arrays de tamaño 1, `kartlapsim/utils/makekart.py` roto (importa `save_file`, que no existe en `helperfunctions.py`), `Kart.rFinal` sin propiedad definida, ausencia de licencia en el repositorio original y, por tanto, imagen sin publicar en ningún registro. Verificar: cada punto aparece con su consecuencia práctica.
- [x] 5.6 Verificación de integración final: desde un clon limpio del fork, seguir el `README` y obtener una ejecución correcta en contenedor con resultados en el volumen. Verificar: pegar la secuencia de órdenes ejecutadas y el listado final del volumen.
