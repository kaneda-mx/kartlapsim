# Design

## Context

Motivación en `proposal.md` → *Why*. Lo que condiciona el diseño:

- **El motor se queda como está.** `kartlapsim/` funciona por composición (`Track`, `Kart`, `Lapsim`) y no imprime ni dibuja nada por sí mismo: `track.py` y `lapsim.py` importan `matplotlib.pyplot` pero no lo usan (`grep 'plt\.'` en el paquete no devuelve nada). Todo el dibujo y el `plt.show()` están en los dos `example*.py`. Por tanto se puede ejecutar el motor headless sin tocarlo.
- **El kart de ejemplo arrastra una ruta relativa.** `data/kartMini.pickle` guarda `torqueCurveFile = './data/torqueCurveMiniDyno.csv'`, y `Lapsim.simulate()` llama a `kart.ini()`, que vuelve a leer ese CSV en cada simulación. El proceso sólo funciona con el directorio de trabajo en la raíz del proyecto.
- **No hay aleatoriedad** en el motor (`grep -nE 'random|seed|shuffle'` no devuelve nada): el mismo entorno y las mismas entradas dan el mismo resultado, así que la reproducibilidad exigida por `simulation-run` es alcanzable sin semillas.
- **Hay referencias medidas ya versionadas**: la cabecera de `data/trackMariembourgMini.csv` declara `Lap 5 - 1:02.725` y sus primeras filas registran 97,25 km/h; `data/example1result.png` es la figura del autor original. Sirven para juzgar el resultado sin inventar cifras.
- **El entorno de planificación no puede ejecutar nada**: no hay `python3`, ni `docker`, ni `/var/run/docker.sock`. Construcción y ejecución las hace el usuario; el diseño tiene que producir comandos exactos y criterios de aceptación observables.
- **Las versiones fijadas no son arbitrarias**: el pickle es protocolo 3 y referencia `numpy.core.multiarray`, y el motor pasa arrays de tamaño 1 donde se esperan escalares (`min(vnew, self.vApexSol[idx], self.kart.vmax)` en `lapsim.py:79`, y los límites `nmin`/`nmax` que recibe `brentq` en `lapsim.py:97`).

## Goals / Non-Goals

**Goals:**

- Una orden reproducible que ejecute el motor en contenedor y deje CSV + JSON + PNG en almacenamiento persistente.
- Un JSON de resumen que sirva ya como contrato de datos de la futura interfaz web (configuraciones, métricas, diferencias, procedencia, versiones).
- Mantener el diff respecto al repositorio original pequeño y localizado, para poder seguir trayendo cambios de `Svennevs/kartlapsim`.
- Dejar escrito qué quedó sin verificar y con qué comando se verifica.

**Non-Goals:**

- No se decide nada del despliegue en Portainer (modalidad, red, proxy, dominio, HTTPS): es el cambio siguiente.
- No se construye imagen multiarquitectura ni se publica en ningún registro.
- No se añade capa de configuración de karts propios ni validación de esquemas JSON de entrada.
- No se corrige `makekart.py` ni se moderniza el motor; ambos están identificados pero fuera de este cambio.

## Decisions

### 1. Ejecutor nuevo en `tools/run_sim.py`, no modificar los ejemplos

Los `example*.py` son la documentación ejecutable del upstream y su `plt.show()` es parte de lo que el autor publicó. Un archivo nuevo en `tools/` deja los ejemplos intactos, evita conflictos al traer cambios del original y permite que el ejecutor tenga interfaz de línea de órdenes propia.

*Alternativa descartada:* parchear `example1_single.py` para guardar la figura. Es menos código pero ensucia el diff con upstream y mezcla ejemplo didáctico con herramienta de validación.

### 2. El ejecutor fija su directorio de trabajo en la raíz del proyecto

`tools/run_sim.py` deduce la raíz desde su propia ubicación y hace `chdir` a ella antes de simular, porque el kart serializado vuelve a abrir `./data/torqueCurveMiniDyno.csv` dentro de `simulate()`. Si falta `data/`, aborta con mensaje explícito en lugar de fallar dentro de `np.loadtxt`.

*Alternativa descartada:* reescribir `kart.torqueCurveFile` tras cargar el pickle. Funciona, pero modifica silenciosamente el objeto de ejemplo y oculta la dependencia real de rutas relativas.

### 3. Un `summary.json` por ejecución, con todas las configuraciones dentro

El resumen es un único documento que lista las configuraciones simuladas, sus métricas (tiempo de vuelta, velocidad máxima, rpm máxima), las diferencias respecto a la configuración declarada como referencia, la procedencia de cada bloque de datos y las versiones (revisión del repositorio, Python, NumPy, SciPy, Matplotlib). Los CSV y PNG van aparte, uno por configuración.

Un solo documento es lo que la interfaz web necesita leer para pintar una comparación; repartir las métricas en varios JSON obligaría a la interfaz a recomponerlas. Las rpm máximas se incluyen porque `example2` demuestra que el motor las produce (`ls1.xsol[:,9]*kart.rFinal*60/(2*np.pi)`); nada más se añade.

### 4. Estructura de salida con marca de tiempo

`/app/output/<YYYYmmdd-HHMMSS>/` con `summary.json`, `series_<etiqueta>.csv` y `speed_<etiqueta>.png`. No se sobreescriben ejecuciones anteriores, así que dos ejecuciones se pueden comparar para demostrar reproducibilidad. La etiqueta deriva del valor de `rFinal` normalizado (por ejemplo `rfinal-7_1`).

### 5. Figura con el backend no interactivo que ya está en la imagen

El `Dockerfile` ya fija `MPLBACKEND=Agg` y `MPLCONFIGDIR=/tmp/matplotlib`. El ejecutor usa `savefig` y nunca `show`, así que funciona igual dentro y fuera del contenedor siempre que el backend no sea interactivo; el ejecutor fija `Agg` por código antes de importar `pyplot` para no depender sólo de la variable de entorno.

### 6. Permisos de la salida: directorio creado en la imagen y volumen nombrado

El `Dockerfile` crea `/app/output` con `chown kart:kart` **antes** de `USER kart`. `/app` es propiedad de root, así que sin ese paso el usuario sin privilegios no podría crear el directorio en tiempo de ejecución.

Se usa un **volumen nombrado**: Docker lo inicializa con el contenido y la propiedad del directorio de la imagen, de modo que hereda el uid 10001 y la escritura funciona sin privilegios. Un bind mount del host aparecería como propiedad de root y provocaría `Permission denied`; si el usuario prefiere bind mount, hay que crear el directorio en el host con `chown 10001:10001`, y así queda documentado en el README. Bajar protecciones (ejecutar como root, `chmod 777`) está descartado.

### 7. `numpy` se queda en la serie 1.x

`numpy==1.26.4` es deliberado: NumPy 2.x renombró `numpy.core` (el pickle del kart lo referencia) y convirtió en error la conversión a escalar de arrays con `ndim > 0`, que es exactamente lo que hacen `lapsim.py:79` y los límites de `brentq`. `scipy==1.11.4` y `matplotlib==3.8.4` son compatibles con NumPy 1.26 y tienen rueda `cp311` para `linux/amd64` y `linux/arm64`, por lo que `--only-binary=:all:` no obliga a compilar en ninguna de las dos arquitecturas. Subir a NumPy 2.x es un cambio posterior, con su propia validación y probablemente con parches al motor.

### 8. Compose sólo para la validación por CLI

`compose.validate.yaml` define un único servicio de un disparo: `restart: "no"`, volumen nombrado en `/app/output`, `logging` con rotación y límites de memoria/CPU. Sin `healthcheck`, porque un contenedor que termina no tiene estado sano que comprobar. Este archivo no se declara como stack de Portainer: en Swarm un servicio que termina se reinicia solo y la estrategia correcta depende de la modalidad, que todavía no está confirmada.

### 9. Criterio de aceptación: comparar con lo medido, sin ajustar nada

La validación se acepta si: (a) el ejecutor termina con código 0; (b) `summary.json` trae un tiempo de vuelta finito y positivo; (c) la curva de velocidad simulada es del mismo orden y forma que la de `data/example1result.png` y que la columna `GPS_Speed` medida; (d) al barrer varias `rFinal` los tiempos de vuelta cambian de forma monótona o con un mínimo claro, como en `example2`.

El tiempo medido de referencia es `1:02.725` (62,725 s), declarado en la cabecera del CSV. La diferencia entre simulación y medición se **registra tal cual** en el README; no se toca ningún parámetro del kart ni del modelo para acercarla. El modelo es punto-masa cuasi-estacionario y una discrepancia es información, no un defecto a maquillar.

### 10. Los avisos numéricos no se silencian

`track.py` calcula `curv = deg2rad(gyro)/v`, que divide por la velocidad; con la vuelta de ejemplo (arranca a 97,25 km/h, es una vuelta cronometrada sin paradas) no debería haber división por cero, pero el ejecutor no oculta los `RuntimeWarning` de NumPy: los deja salir a los registros para que un dato de pista futuro con `v = 0` sea visible en lugar de propagarse como `inf`.

## Risks / Trade-offs

- **`brentq` recibe límites que son arrays de tamaño 1** (`lapsim.py:97`) y `errornAxle` devuelve también un array de tamaño 1 → con SciPy 1.11 y NumPy 1.26 esto es una deprecación, no un error, pero es el punto más probable de fallo de la primera ejecución. Mitigación: es justamente lo que la validación tiene que descubrir; si falla, el arreglo mínimo (convertir a `float` en esas tres expresiones) se propone como cambio aparte con la traza como evidencia, nunca a ciegas dentro de este.
- **El pickle ancla la versión de NumPy** → la deuda se registra en el README como limitación conocida, con la ruta de salida identificada: regenerar los karts desde JSON validado, que es el cambio que también arregla `makekart.py` (importa `save_file`, que no existe).
- **Nada de esto se puede verificar en el entorno de planificación** (sin Python ni Docker) → todas las tareas de construcción y ejecución están redactadas como órdenes exactas con la evidencia que deben devolver; no se marcan completadas sin esa salida pegada.
- **`np.loadtxt` cambió de implementación entre NumPy 1.20 y 1.26** → la pista de ejemplo tiene 10 columnas constantes y 17 líneas de cabecera, consistentes con `skiprows=17`, así que el riesgo es bajo; la primera ejecución lo confirma o lo refuta.
- **Dos ejecuciones en máquinas distintas pueden diferir en los últimos bits** por la BLAS que traiga la rueda de NumPy. La reproducibilidad se exige y se comprueba dentro de la misma imagen y arquitectura; el README lo dice así en lugar de prometer igualdad bit a bit entre amd64 y arm64.
- **El repositorio original no declara licencia** → la validación local no la necesita, pero publicar la imagen queda bloqueado. La imagen se construye en destino en lugar de distribuirse.

## Migration Plan

No hay migración de datos ni servicio en marcha. El despliegue es: construir la imagen en la máquina donde se vaya a ejecutar, lanzar el contenedor de un disparo, revisar el código de salida y los archivos del volumen. Revertir es borrar el contenedor, el volumen y la imagen; el motor y los datos no se modifican, así que no hay estado que deshacer en el repositorio más allá de `git revert` de los archivos añadidos.

## Open Questions

Ninguna de estas bloquea las especificaciones, el enfoque ni las tareas de este cambio:

- Arquitectura de la VM (`amd64` o `arm64`): sólo decide si la imagen construida en la MacBook M1 se puede reutilizar en la VM o hay que construirla en cada sitio. Se resuelve con `uname -m` en la VM.
- Modalidad de Portainer (Standalone o Swarm), proxy inverso existente, redes y dominio: necesarias para el cambio siguiente, que es el que decide la estrategia de stack, no para validar el motor.
