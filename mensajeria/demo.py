"""Ejecución de demostración del taller: genera la evidencia de docs/mensajeria.

    python -m mensajeria.demo

Escenarios (cada uno con su correlation_id):
  req-A  reclamación normal; el despachador se cae tras entregar -> duplicado deduplicado
  req-B  el correo falla 2 veces -> reintentos con backoff -> entregado una vez
  req-C  identidad inválida -> ClaimRejected para revisión de la oficina
  req-D  el correo nunca responde -> cola de fallidos tras 5 intentos
"""

import random

from mensajeria import consumidor as cons
from mensajeria import productor as prod
from mensajeria.consumidor import ErrorTransitorio, Notificador
from mensajeria.despachador import CaidaSimulada, Despachador
from mensajeria.trazas import metricas


class Reloj:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class CorreoSimulado:
    """Falla según el objeto: obj-B dos veces, obj-D siempre."""

    def __init__(self) -> None:
        self.fallos = {"obj-B": 2, "obj-D": 10**9}

    def __call__(self, evento: dict) -> None:
        objeto = evento["aggregate_id"]
        if self.fallos.get(objeto, 0) > 0:
            self.fallos[objeto] -= 1
            raise ErrorTransitorio(f"correo no responde ({objeto})")


def main() -> None:
    reloj = Reloj()
    db_p, db_c = prod.abrir(), cons.abrir()
    for oid in ("obj-A", "obj-B", "obj-C", "obj-D"):
        prod.sembrar_objeto(db_p, oid, f"Objeto {oid}")

    print("# Productor")
    prod.reclamar(db_p, "obj-A", "student-1", "req-A")
    prod.reclamar(db_p, "obj-B", "student-2", "req-B")
    prod.reclamar(db_p, "obj-C", "intruso", "req-C", identidad_valida=False)
    prod.reclamar(db_p, "obj-D", "student-4", "req-D")

    # Semilla fija: la evidencia es reproducible con las mismas esperas.
    d = Despachador(db_p, Notificador(db_c, CorreoSimulado()), reloj=reloj,
                    aleatorio=random.Random(42).random)
    caida = {"pendiente": True}

    def caer_una_vez(evento: dict) -> bool:
        if evento["correlation_id"] == "req-A" and caida["pendiente"]:
            caida["pendiente"] = False
            return True
        return False

    d.caer_tras_entregar = caer_una_vez

    vuelta = 0
    while vuelta < 20:
        proximo = db_p.execute(
            "SELECT MIN(proximo_intento) FROM outbox WHERE estado = 'pendiente'"
        ).fetchone()[0]
        if proximo is None:
            break
        reloj.t = max(reloj.t, proximo)  # el publicador despierta cuando toca
        vuelta += 1
        print(f"\n# Despachador, vuelta {vuelta} (t = {reloj.t:.3f} s)")
        try:
            d.despachar_pendientes()
        except CaidaSimulada:
            print("# !! el despachador se cayó tras entregar req-A, antes de marcarlo; reinicia")

    print("\n# Estado final del outbox (productor)")
    for r in db_p.execute("SELECT type, aggregate_id, estado, intentos, ultimo_error FROM outbox ORDER BY seq"):
        print(f"  {r['aggregate_id']:6} {r['type']:14} {r['estado']:10} intentos={r['intentos']} {r['ultimo_error'] or ''}")
    print("\n# Avisos entregados a la oficina (consumidor)")
    for r in db_c.execute("SELECT correlation_id, texto FROM avisos ORDER BY rowid"):
        print(f"  {r['correlation_id']}: {r['texto']}")
    print("\n# Métricas")
    for etapa, n in sorted(metricas.items()):
        print(f"  {etapa:22} {n}")


if __name__ == "__main__":
    main()
