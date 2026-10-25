FROM python:3.11-slim-bookworm

# Revisión del repositorio desde la que se construye, para poder trazar un
# resultado hasta el código que lo produjo.
ARG GIT_REV=desconocida
LABEL org.opencontainers.image.title="kartlapsim" \
      org.opencontainers.image.description="Simulación de tiempo de vuelta de karts (validación headless)" \
      org.opencontainers.image.source="https://github.com/kaneda-mx/kartlapsim" \
      org.opencontainers.image.revision="${GIT_REV}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/home/kart \
    KARTLAPSIM_GIT_REV=${GIT_REV}

WORKDIR /app

# Usuario sin privilegios.
RUN groupadd --gid 10001 kart \
    && useradd \
       --uid 10001 \
       --gid kart \
       --create-home \
       --home-dir /home/kart \
       kart

# Separar dependencias del código permite aprovechar la caché de build.
COPY requirements-docker.txt ./

# --only-binary=:all: obliga a usar ruedas precompiladas: la imagen no trae
# compilador ni cabeceras, así que compilar numpy/scipy fallaría. Las tres
# dependencias tienen rueda cp311 para linux/amd64 y linux/arm64.
#
# numpy se queda en la serie 1.x deliberadamente: data/kartMini.pickle
# referencia numpy.core.multiarray (renombrado en numpy 2.x) y el motor pasa
# arrays de tamaño 1 donde se esperan escalares (kartlapsim/lapsim.py), que
# numpy 2.x convierte en error. Subir a 2.x es un cambio aparte con su propia
# validación.
RUN python -m pip install \
    --only-binary=:all: \
    -r requirements-docker.txt

COPY --chown=kart:kart kartlapsim/ ./kartlapsim/
COPY --chown=kart:kart data/ ./data/
COPY --chown=kart:kart tools/ ./tools/
COPY --chown=kart:kart example1_single.py example2_finaldrivescan.py ./

# /app es propiedad de root, así que el directorio de salida se crea aquí y se
# cede al usuario sin privilegios: de lo contrario no podría crearlo en tiempo
# de ejecución. Un volumen nombrado montado en /app/output hereda esta
# propiedad (uid 10001) y la escritura funciona sin privilegios.
RUN mkdir -p /app/output && chown kart:kart /app/output

USER kart

# Ejecutor headless: escribe CSV, JSON y PNG en /app/output y termina.
CMD ["python", "tools/run_sim.py"]
