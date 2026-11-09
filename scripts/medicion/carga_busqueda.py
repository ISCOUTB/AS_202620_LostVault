"""Prueba de carga del Escenario 4 desde línea de comandos (solo biblioteca estándar).

Complementa scripts/medicion/carga_navegador.js: en vez de ráfagas desde un único
navegador, simula N usuarios concurrentes, cada uno en su propio hilo, que buscan
durante un tiempo fijo con una pausa corta entre búsquedas. Así el generador de
carga deja de ser el cuello de botella (riesgo R13 de arc42 §11).

Uso:
    python3 scripts/medicion/carga_busqueda.py \
        --url https://backend-nu-self-91.vercel.app --usuarios 200 --segundos 60

Sale con código 0 si p95 <= umbral y no hubo errores; 1 en caso contrario.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

TERMS = ["termo", "negro", "biblioteca", "llaves", "cuaderno"]


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[max(0, math.ceil(p / 100 * len(s)) - 1)]


def user_loop(base: str, deadline: float, think_s: float, out: list, lock: threading.Lock) -> None:
    while time.monotonic() < deadline:
        url = f"{base}/objects?q={random.choice(TERMS)}"
        start = time.perf_counter()
        status, cache = 0, None
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                r.read()
                status, cache = r.status, r.headers.get("x-vercel-cache")
        except urllib.error.HTTPError as e:
            status = e.code
        except Exception:  # timeout, conexión rechazada, etc.
            status = 0
        ms = (time.perf_counter() - start) * 1000
        with lock:
            out.append({"ms": ms, "status": status, "cache": cache})
        time.sleep(random.uniform(0, think_s))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="https://backend-nu-self-91.vercel.app")
    ap.add_argument("--usuarios", type=int, default=200)
    ap.add_argument("--segundos", type=int, default=60)
    ap.add_argument("--pausa", type=float, default=1.0, help="pausa máxima entre búsquedas (s)")
    ap.add_argument("--umbral-ms", type=float, default=2000)
    args = ap.parse_args()

    results: list[dict] = []
    lock = threading.Lock()
    deadline = time.monotonic() + args.segundos
    with ThreadPoolExecutor(max_workers=args.usuarios) as pool:
        for _ in range(args.usuarios):
            pool.submit(user_loop, args.url.rstrip("/"), deadline, args.pausa, results, lock)

    ok = [r["ms"] for r in results if r["status"] == 200]
    errors = len(results) - len(ok)
    summary = {
        "usuarios": args.usuarios,
        "segundos": args.segundos,
        "peticiones": len(results),
        "errores": errors,
        "p50_ms": round(percentile(ok, 50), 1) if ok else None,
        "p95_ms": round(percentile(ok, 95), 1) if ok else None,
        "p99_ms": round(percentile(ok, 99), 1) if ok else None,
        "umbral_ms": args.umbral_ms,
    }
    summary["cumple"] = bool(ok) and errors == 0 and summary["p95_ms"] <= args.umbral_ms
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["cumple"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
