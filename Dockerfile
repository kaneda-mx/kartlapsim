FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    HOME=/home/kart

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

RUN python -m pip install \
    --only-binary=:all: \
    -r requirements-docker.txt

COPY --chown=kart:kart kartlapsim/ ./kartlapsim/
COPY --chown=kart:kart data/ ./data/
COPY --chown=kart:kart example1_single.py example2_finaldrivescan.py ./

USER kart

CMD ["python", "example1_single.py"]
