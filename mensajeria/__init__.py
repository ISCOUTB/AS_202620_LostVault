"""Simulador local de mensajería de LostVault (Taller de Sistemas de Mensajes).

Implementa el flujo diseñado en docs/datos/eventos.md:

    reclamar() ──(misma transacción)──▶ outbox ──▶ Despachador ──▶ Notificador

- Entrega al menos una vez (outbox + reintentos).
- Consumidor idempotente por event_id.
- Reintentos con backoff exponencial + jitter y cola de mensajes fallidos.
- Logs JSON con correlation_id para seguir cada mensaje.

Usa SQLite (biblioteca estándar) como base del productor y del consumidor, para
tener transacciones reales sin servicios externos. Ver
docs/mensajeria/taller-mensajeria.md.
"""
