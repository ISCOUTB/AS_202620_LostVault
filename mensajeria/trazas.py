"""Logs JSON y métricas para seguir un mensaje de productor a consumidor.

Cada línea lleva event_id, correlation_id y la etapa. Filtrando por
correlation_id se ve el recorrido completo de un mensaje:
producido → despachado → entregado (o reintento_programado / duplicado_ignorado
/ enviado_a_fallidos).
"""

import json
import logging
import sys
from collections import Counter

logger = logging.getLogger("lostvault.mensajeria")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True

metricas: Counter = Counter()


def traza(etapa: str, componente: str, evento: dict | None = None, **extra) -> None:
    metricas[etapa] += 1
    registro = {"etapa": etapa, "componente": componente}
    if evento is not None:
        for campo in ("event_id", "correlation_id", "type", "aggregate_id"):
            if campo in evento:
                registro[campo] = evento[campo]
    registro.update(extra)
    logger.info(json.dumps(registro, ensure_ascii=False), extra={"traza": registro})
