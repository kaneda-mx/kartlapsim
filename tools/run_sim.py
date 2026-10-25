#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ejecutor de simulaciones sin interfaz gráfica.

Carga una pista y un kart de los datos versionados en el repositorio, simula
una o varias relaciones de transmisión final y escribe los resultados en
archivos (CSV de series, JSON de resumen y PNG de velocidad).

El directorio de trabajo se fija en la raíz del proyecto antes de simular:
el kart serializado guarda la ruta relativa de su curva de par
('./data/torqueCurveMiniDyno.csv') y la vuelve a leer en cada simulate(),
así que ejecutar desde otro directorio fallaría dentro de np.loadtxt.

Códigos de salida:
    0  simulación correcta
    1  fallo del motor durante el cálculo
    2  entrada inválida (argumentos)
    3  faltan los datos de ejemplo del repositorio
"""

import matplotlib

# Debe quedar fijado antes de importar pyplot: la imagen define MPLBACKEND=Agg,
# pero el ejecutor no depende sólo de la variable de entorno.
matplotlib.use("Agg")

import argparse
import csv
import json
import math
import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np
import scipy

# Raíz del proyecto deducida de la ubicación de este archivo (tools/run_sim.py).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Conjuntos de datos de confianza: los versionados en el repositorio. No se
# acepta ninguna ruta externa, porque cargar un pickle ejecuta código.
DATASETS = {
    "mini": {
        "track": "data/trackMariembourgMini.csv",
        "kart": "data/kartMini.pickle",
        "descripcion": "kart mini en Mariembourg (transmisión directa, verificado)",
    },
    "kz": {
        "track": "data/trackMariembourgKz.csv",
        "kart": "data/kartKz.pickle",
        "descripcion": "kart KZ en Mariembourg (caja de cambios, sin verificar)",
    },
}

# Rango admitido para la relación de transmisión final (nAxle/nEng). Los karts
# de transmisión directa de los datos de ejemplo usan ~6.5-7.3 (piñón 10 /
# corona 65-73) y los de caja ~1.4 (24/17); el rango es deliberadamente amplio.
RFINAL_MIN = 0.5
RFINAL_MAX = 20.0


class InputError(Exception):
    """Entrada inválida detectada antes de simular."""


def dataset_name(value):
    if value not in DATASETS:
        raise argparse.ArgumentTypeError(
            "'%s' no es un conjunto de datos de confianza. Sólo se admiten los "
            "datos versionados en el repositorio: %s. No se cargan pickles ni "
            "rutas externas, porque deserializar un pickle ejecuta código."
            % (value, ", ".join(sorted(DATASETS)))
        )
    return value


def final_drive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(
            "'%s' no es un número. La relación de transmisión final debe estar "
            "entre %s y %s." % (value, RFINAL_MIN, RFINAL_MAX)
        )
    if not math.isfinite(number):
        raise argparse.ArgumentTypeError(
            "'%s' no es finito. La relación de transmisión final debe estar "
            "entre %s y %s." % (value, RFINAL_MIN, RFINAL_MAX)
        )
    if number <= 0 or number < RFINAL_MIN or number > RFINAL_MAX:
        raise argparse.ArgumentTypeError(
            "%s está fuera del rango admitido [%s, %s] para la relación de "
            "transmisión final." % (number, RFINAL_MIN, RFINAL_MAX)
        )
    return number


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="run_sim.py",
        description=(
            "Ejecuta el simulador de vuelta sin interfaz gráfica y exporta los "
            "resultados (CSV, JSON y PNG). Se ejecuta siempre con la raíz del "
            "proyecto como directorio de trabajo, porque el kart serializado "
            "relee su curva de par por ruta relativa."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dataset",
        type=dataset_name,
        default="mini",
        help="conjunto de datos de confianza del repositorio: %s"
        % ", ".join("%s (%s)" % (k, v["descripcion"]) for k, v in sorted(DATASETS.items())),
    )
    parser.add_argument(
        "--final-drive",
        type=final_drive,
        nargs="+",
        default=None,
        metavar="R",
        help="una o varias relaciones de transmisión final, rango admitido "
        "[%s, %s] (por omisión, la del kart de ejemplo)" % (RFINAL_MIN, RFINAL_MAX),
    )
    parser.add_argument(
        "--baseline",
        type=final_drive,
        default=None,
        metavar="R",
        help="relación de referencia para las diferencias (por omisión, la primera)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        metavar="DIR",
        help="directorio donde se escriben los resultados",
    )
    parser.add_argument(
        "--label",
        default=None,
        metavar="TEXTO",
        help="etiqueta de la ejecución, se añade al nombre del directorio de salida",
    )
    return parser.parse_args(argv)


def require_dataset(dataset):
    """Comprueba que los datos de confianza existen antes de importar el motor."""
    missing = [p for p in (dataset["track"], dataset["kart"]) if not os.path.isfile(p)]
    if missing:
        raise SystemExit(
            "No se encuentran los datos de ejemplo del repositorio: %s\n"
            "Directorio de trabajo: %s\n"
            "Se esperaban relativos a la raíz del proyecto (%s). Si el "
            "contenedor no los tiene, revisa las instrucciones COPY del "
            "Dockerfile." % (", ".join(missing), os.getcwd(), PROJECT_ROOT)
        )


def read_track_metadata(path):
    """Extrae la cabecera del CSV de pista (metadatos medidos, no calculados)."""
    meta = {}
    with open(path, encoding="utf-8", errors="replace") as fd:
        for n, line in enumerate(fd):
            if n >= 12:
                break
            parts = line.strip().strip('"').split(",", 1)
            if len(parts) == 2:
                key = parts[0].strip().strip('"')
                value = parts[1].strip().strip('"').strip('"')
                if key:
                    meta[key] = value
    return meta


def kart_parameters(kart):
    """Parámetros del kart de ejemplo, tal como están en el objeto cargado."""
    skip = {"nAxlePT", "TAxlePT"}  # series derivadas de la curva de par
    params = {}
    for name, value in sorted(vars(kart).items()):
        if name in skip:
            continue
        if isinstance(value, np.ndarray):
            params[name] = value.ravel().tolist()
        elif isinstance(value, (np.floating, np.integer)):
            params[name] = value.item()
        elif isinstance(value, (bool, int, float, str)) or value is None:
            params[name] = value
    return params


def engine_revision():
    """Revisión del repositorio: la inyectada en la imagen o, si no, la de git."""
    for var in ("KARTLAPSIM_GIT_REV", "GIT_REV"):
        value = os.environ.get(var)
        if value:
            return value.strip()
    try:
        out = subprocess.run(
            ["git", "-C", PROJECT_ROOT, "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "desconocida"


def label_for(rfinal):
    return ("rfinal-%s" % ("%.4f" % rfinal).rstrip("0").rstrip(".")).replace(".", "_")


def simulate_one(dataset, rfinal, track):
    """Simula una relación de transmisión final y devuelve métricas y series."""
    from kartlapsim.lapsim import Lapsim
    from kartlapsim.utils.helperfunctions import load_object

    # El kart se recarga por configuración para que simulate() no herede estado
    # recalculado de la configuración anterior.
    kart = load_object(dataset["kart"])
    kart.rFinal = rfinal

    sim = Lapsim(kart, track)
    sim.simulate()

    s = np.asarray(sim.track.s).ravel()
    v_sim = np.asarray(sim.vqss).ravel()
    v_apex = np.asarray(sim.vApexSol).ravel()
    v_measured = np.asarray(sim.track.v).ravel()
    rpm_measured = np.asarray(sim.track.rpm).ravel()

    series = {
        "s_m": s,
        "v_sim_kph": v_sim * 3.6,
        "v_medida_kph": v_measured * 3.6,
        "v_apex_kph": v_apex * 3.6,
    }
    metrics = {
        "laptime_s": float(sim.laptime),
        "v_max_kph": float(np.max(v_sim) * 3.6),
    }

    # calcfwdbwd() recorre todos los índices salvo el del ápice más lento, así
    # que esas filas del registro de estado quedan en cero sin haberse
    # calculado. Un cero ahí sería un dato inventado: se marcan como ausentes.
    unlogged = np.all(np.asarray(sim.xsol) == 0, axis=1)
    diagnostics = {
        "puntos": int(s.size),
        "puntos_sin_registrar": int(np.count_nonzero(unlogged)),
        "indices_sin_registrar": np.flatnonzero(unlogged).tolist(),
    }

    # Las rpm de motor sólo se derivan del registro de estado si la relación de
    # caja es unitaria: con caja de cambios, nAxle*rFinal no es la velocidad
    # del motor y el número parecería correcto sin serlo.
    r_trans = np.ravel(np.asarray(kart.rTrans, dtype=float))
    if r_trans.size == 1 and float(r_trans[0]) == 1.0:
        n_axle = np.asarray(sim.xsol[:, 9]).ravel().astype(float)
        rpm_sim = n_axle * kart.rFinal * 60 / (2 * np.pi)
        rpm_sim[unlogged] = np.nan
        series["rpm_sim"] = rpm_sim
        series["rpm_medida"] = rpm_measured
        metrics["rpm_max"] = float(np.nanmax(rpm_sim))
        diagnostics["rpm_sim"] = {
            "exportada": True,
            "supuesto": "relación de caja unitaria (rTrans = 1); rpm = nAxle * rFinal * 60 / 2pi",
        }
    else:
        series["rpm_medida"] = rpm_measured
        diagnostics["rpm_sim"] = {
            "exportada": False,
            "motivo": "la configuración tiene %d relaciones de caja (rTrans = %s): "
            "nAxle * rFinal no es la velocidad del motor"
            % (r_trans.size, r_trans.tolist()),
        }

    return metrics, series, kart, diagnostics


def write_series_csv(path, series):
    columns = list(series)
    rows = len(series[columns[0]])
    with open(path, "w", newline="", encoding="utf-8") as fd:
        writer = csv.writer(fd)
        writer.writerow(columns)
        for i in range(rows):
            writer.writerow(["%.6f" % series[c][i] for c in columns])


def write_speed_png(path, series, label, metrics):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(series["s_m"], series["v_apex_kph"], label="límite de apex (modelo)", linewidth=1)
    ax.plot(series["s_m"], series["v_medida_kph"], label="medida GPS", linewidth=1)
    ax.plot(series["s_m"], series["v_sim_kph"], label="simulada", linewidth=1.5)
    ax.set_xlabel("distancia [m]")
    ax.set_ylabel("velocidad [km/h]")
    ax.set_title("%s - tiempo de vuelta simulado %.3f s" % (label, metrics["laptime_s"]))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def track_quality(track):
    """Rango de las entradas medidas y paso de integración.

    Va en el resumen para que quien lea los resultados pueda estimar su error
    sin volver a los datos de origen: el paso de distancia es el paso de la
    integración de Euler del motor.
    """
    v = np.asarray(track.v).ravel() * 3.6
    ds = np.asarray(track.ds).ravel()
    return {
        "puntos": int(v.size),
        "v_medida_min_kph": float(np.min(v)),
        "v_medida_max_kph": float(np.max(v)),
        "ds_medio_m": float(np.mean(ds)),
        "ds_max_m": float(np.max(ds)),
        "nota": "el paso de distancia es el paso de la integración de Euler; "
        "el error de integración crece con él",
    }


def build_summary(
    dataset_key, dataset, track_meta, kart_params, results, failures, baseline, quality
):
    configs = []
    baseline_metrics = results[baseline]["metrics"] if baseline in results else None
    for rfinal in sorted(results):
        entry = results[rfinal]
        config = {
            "etiqueta": entry["label"],
            "rFinal": rfinal,
            "es_referencia": rfinal == baseline,
            "estado": "calculada",
        }
        config.update(entry["metrics"])
        config["diagnostico"] = entry["diagnostics"]
        if baseline_metrics is not None and rfinal != baseline:
            config["diferencias_vs_referencia"] = {
                "laptime_s": entry["metrics"]["laptime_s"] - baseline_metrics["laptime_s"],
                "v_max_kph": entry["metrics"]["v_max_kph"] - baseline_metrics["v_max_kph"],
                "rpm_max": entry["metrics"]["rpm_max"] - baseline_metrics["rpm_max"],
            }
        configs.append(config)

    return {
        "ejecucion": {
            "instante_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "conjunto_de_datos": dataset_key,
            "referencia_rFinal": baseline,
            "configuraciones_solicitadas": len(results) + len(failures),
            "configuraciones_calculadas": len(results),
        },
        "configuraciones": configs,
        "fallidas": failures,
        "calidad_de_los_datos": quality,
        "convenciones": {
            "dato_ausente": "las magnitudes derivadas del registro de estado se "
            "escriben como NaN ('nan' en el CSV) en los puntos que el motor no "
            "registra; nunca como cero",
            "diferencias": "las diferencias entre configuraciones son más fiables "
            "que los valores absolutos: el modelo es punto-masa cuasi-estacionario "
            "y los errores se cancelan en parte al comparar dos configuraciones "
            "sobre la misma pista",
        },
        "procedencia": {
            "medido": {
                "pista": {
                    "archivo": dataset["track"],
                    "origen": "registro GPS (Mariembourg, 2019)",
                    "canales": ["Distance", "GPS_Speed", "GPS_Gyro", "GPS_Slope", "RPM"],
                    "cabecera": track_meta,
                },
                "curva_de_par": {
                    "archivo": kart_params.get("torqueCurveFile"),
                    "origen": "ensayo de banco",
                },
            },
            "de_ejemplo": {
                "archivo": dataset["kart"],
                "descripcion": dataset["descripcion"],
                "parametros_kart": kart_params,
            },
            "derivado_del_modelo": [
                "laptime_s",
                "v_max_kph",
                "rpm_max",
                "diferencias_vs_referencia",
                "series: v_sim_kph, v_apex_kph, rpm_sim",
            ],
        },
        "versiones": {
            "revision_repositorio": engine_revision(),
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    # El motor y el kart serializado usan rutas relativas a la raíz del proyecto.
    os.chdir(PROJECT_ROOT)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    # Los avisos numéricos no se silencian: una pista con v = 0 haría que la
    # curvatura saliera infinita y eso debe verse en los registros.
    np.seterr(all="warn")

    dataset = DATASETS[args.dataset]
    require_dataset(dataset)

    from kartlapsim.track import Track
    from kartlapsim.utils.helperfunctions import load_object

    track = Track(dataset["track"])
    track_meta = read_track_metadata(dataset["track"])

    rfinals = args.final_drive
    if not rfinals:
        rfinals = [float(load_object(dataset["kart"]).rFinal)]
        print("Sin --final-drive: se usa la del kart de ejemplo (%g)" % rfinals[0])

    # dict.fromkeys preserva el orden y descarta duplicados.
    rfinals = list(dict.fromkeys(rfinals))

    baseline = args.baseline if args.baseline is not None else rfinals[0]
    if baseline not in rfinals:
        raise InputError(
            "La referencia --baseline %g no está entre las configuraciones "
            "simuladas (%s)." % (baseline, ", ".join("%g" % r for r in rfinals))
        )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(args.output_dir, stamp if not args.label else "%s-%s" % (stamp, args.label))

    def ensure_run_dir():
        # El directorio se crea al escribir el primer archivo: un fallo total no
        # debe dejar un directorio vacío en el volumen de salida.
        os.makedirs(run_dir, exist_ok=True)
        return run_dir

    results = {}
    failures = []
    for rfinal in rfinals:
        label = label_for(rfinal)
        print("Simulando %s (rFinal = %g) ..." % (label, rfinal))
        try:
            metrics, series, kart, diagnostics = simulate_one(dataset, rfinal, track)
        except Exception as exc:  # el motor puede fallar; debe verse cuál y por qué
            print(
                "FALLO en la configuración rFinal = %g (%s): %s"
                % (rfinal, label, exc),
                file=sys.stderr,
            )
            traceback.print_exc()
            failures.append({"rFinal": rfinal, "etiqueta": label, "error": repr(exc)})
            continue

        out = ensure_run_dir()
        write_series_csv(os.path.join(out, "series_%s.csv" % label), series)
        write_speed_png(os.path.join(out, "speed_%s.png" % label), series, label, metrics)
        results[rfinal] = {
            "label": label,
            "metrics": metrics,
            "kart": kart,
            "diagnostics": diagnostics,
        }
        rpm = metrics.get("rpm_max")
        print(
            "  tiempo de vuelta %.3f s | v max %.2f km/h | rpm max %s | puntos sin registrar %d"
            % (
                metrics["laptime_s"],
                metrics["v_max_kph"],
                "%.0f" % rpm if rpm is not None else "no exportada",
                diagnostics["puntos_sin_registrar"],
            )
        )

    if not results:
        print(
            "Ninguna configuración se pudo calcular: no se escribe resumen.",
            file=sys.stderr,
        )
        return 1

    if baseline not in results:
        baseline = sorted(results)[0]
        print(
            "La referencia solicitada falló; se usa %g como referencia." % baseline,
            file=sys.stderr,
        )

    kart_params = kart_parameters(results[baseline]["kart"])
    summary = build_summary(
        args.dataset,
        dataset,
        track_meta,
        kart_params,
        results,
        failures,
        baseline,
        track_quality(track),
    )
    summary_path = os.path.join(ensure_run_dir(), "summary.json")
    with open(summary_path, "w", encoding="utf-8") as fd:
        json.dump(summary, fd, indent=2, ensure_ascii=False, sort_keys=False)
        fd.write("\n")

    print("Resultados en %s" % os.path.abspath(run_dir))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except InputError as exc:
        print("Entrada inválida: %s" % exc, file=sys.stderr)
        sys.exit(2)
    except SystemExit as exc:
        if isinstance(exc.code, str):  # require_dataset
            print(exc.code, file=sys.stderr)
            sys.exit(3)
        raise
