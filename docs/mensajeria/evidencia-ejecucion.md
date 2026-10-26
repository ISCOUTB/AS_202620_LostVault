# Evidencia de ejecución — Taller de Sistemas de Mensajes

Ejecutado el 2026-10-25 en local (Windows 10, Python 3.12, SQLite de la
biblioteca estándar). Se reproduce con los comandos de cada sección. El CI corre las
mismas pruebas en cada push (`.github/workflows/backend.yml`, paso *Messaging workshop tests*).

## 1. Pruebas automatizadas

```bash
python -m pytest -v mensajeria/tests
```

```text
test_mensajeria.py::test_evento_producido_cumple_el_contrato PASSED
test_mensajeria.py::test_consumidor_acepta_campos_nuevos_opcionales PASSED
test_mensajeria.py::test_cambios_incompatibles_violan_el_contrato[<lambda>0] PASSED
test_mensajeria.py::test_cambios_incompatibles_violan_el_contrato[<lambda>1] PASSED
test_mensajeria.py::test_cambios_incompatibles_violan_el_contrato[<lambda>2] PASSED
test_mensajeria.py::test_cambios_incompatibles_violan_el_contrato[<lambda>3] PASSED
test_mensajeria.py::test_claim_rejected_exige_reason PASSED
test_mensajeria.py::test_si_la_transaccion_falla_no_queda_ni_reclamacion_ni_evento PASSED
test_mensajeria.py::test_segunda_reclamacion_del_mismo_objeto_no_genera_evento PASSED
test_mensajeria.py::test_identidad_invalida_publica_claim_rejected_sin_reclamar PASSED
test_mensajeria.py::test_duplicado_por_caida_tras_entregar_produce_un_solo_aviso PASSED
test_mensajeria.py::test_mismo_mensaje_recibido_dos_veces_se_ignora_la_segunda PASSED
test_mensajeria.py::test_fallo_recuperable_se_reintenta_con_backoff_y_se_entrega_una_vez PASSED
test_mensajeria.py::test_backoff_exponencial_con_tope_y_jitter PASSED
test_mensajeria.py::test_tras_max_intentos_va_a_fallidos_y_no_se_reintenta PASSED
test_mensajeria.py::test_mensaje_fuera_de_contrato_va_a_fallidos_sin_reintentar PASSED
test_mensajeria.py::test_orden_por_objeto_se_respeta_y_otros_objetos_no_se_bloquean PASSED
test_mensajeria.py::test_un_mensaje_se_puede_seguir_por_correlation_id PASSED
============================= 18 passed in 4.98s ==============================
```

| Lo que pide el taller | Prueba |
|---|---|
| Un duplicado | `test_duplicado_por_caida_tras_entregar_produce_un_solo_aviso`, `test_mismo_mensaje_recibido_dos_veces_se_ignora_la_segunda` |
| Un fallo recuperable | `test_fallo_recuperable_se_reintenta_con_backoff_y_se_entrega_una_vez` |
| Cola de fallidos | `test_tras_max_intentos_va_a_fallidos_y_no_se_reintenta`, `test_mensaje_fuera_de_contrato_va_a_fallidos_sin_reintentar` |
| Contrato y compatibilidad | `test_evento_producido_cumple_el_contrato`, `test_consumidor_acepta_campos_nuevos_opcionales`, `test_cambios_incompatibles_violan_el_contrato[*]` |
| Seguimiento productor → consumidor | `test_un_mensaje_se_puede_seguir_por_correlation_id` |

## 2. Ejecución de la demo con trazas

```bash
python -m mensajeria.demo
```

Cuatro reclamaciones, cada una con su `correlation_id`:

- `req-A`: el despachador se cae justo después de entregar. Al reiniciar reenvía y el
  consumidor registra `duplicado_ignorado`: un solo aviso.
- `req-B`: el correo falla dos veces; reintentos tras ~0,8 s y ~1,2 s; entregado en el intento 3.
- `req-C`: identidad inválida → `ClaimRejected` para revisión de la oficina.
- `req-D`: el correo nunca responde; esperas crecientes (0,5 → 1,3 → 3,5 → 6,7 s) y a
  fallidos en el intento 5.

Para seguir un mensaje basta filtrar por su `correlation_id`
(p. ej. `python -m mensajeria.demo | grep req-B`). Los `event_id` cambian en cada
ejecución (UUID v4); las esperas no, porque la demo fija la semilla del jitter.

```text
# Productor
{"etapa": "producido", "componente": "productor", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A"}
{"etapa": "producido", "componente": "productor", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B"}
{"etapa": "producido", "componente": "productor", "event_id": "5b8303c0-7889-4613-b5c4-b2da204673e9", "correlation_id": "req-C", "type": "ClaimRejected", "aggregate_id": "obj-C"}
{"etapa": "producido", "componente": "productor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}

# Despachador, vuelta 1 (t = 0.000 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A", "intento": 1}
{"etapa": "recibido", "componente": "consumidor", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A"}
{"etapa": "entregado", "componente": "consumidor", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A"}
# !! el despachador se cayó tras entregar req-A, antes de marcarlo; reinicia

# Despachador, vuelta 2 (t = 0.000 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A", "intento": 1}
{"etapa": "recibido", "componente": "consumidor", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A"}
{"etapa": "duplicado_ignorado", "componente": "consumidor", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A"}
{"etapa": "confirmado_en_outbox", "componente": "despachador", "event_id": "7c183c45-b36f-46cc-9413-e1eb8829b1a3", "correlation_id": "req-A", "type": "ClaimCreated", "aggregate_id": "obj-A", "intento": 1}
{"etapa": "despachado", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 1}
{"etapa": "recibido", "componente": "consumidor", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 1, "espera_s": 0.82, "detalle": "ErrorTransitorio('correo no responde (obj-B)')"}
{"etapa": "despachado", "componente": "despachador", "event_id": "5b8303c0-7889-4613-b5c4-b2da204673e9", "correlation_id": "req-C", "type": "ClaimRejected", "aggregate_id": "obj-C", "intento": 1}
{"etapa": "recibido", "componente": "consumidor", "event_id": "5b8303c0-7889-4613-b5c4-b2da204673e9", "correlation_id": "req-C", "type": "ClaimRejected", "aggregate_id": "obj-C"}
{"etapa": "entregado", "componente": "consumidor", "event_id": "5b8303c0-7889-4613-b5c4-b2da204673e9", "correlation_id": "req-C", "type": "ClaimRejected", "aggregate_id": "obj-C"}
{"etapa": "confirmado_en_outbox", "componente": "despachador", "event_id": "5b8303c0-7889-4613-b5c4-b2da204673e9", "correlation_id": "req-C", "type": "ClaimRejected", "aggregate_id": "obj-C", "intento": 1}
{"etapa": "despachado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 1}
{"etapa": "recibido", "componente": "consumidor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 1, "espera_s": 0.513, "detalle": "ErrorTransitorio('correo no responde (obj-D)')"}

# Despachador, vuelta 3 (t = 0.513 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 2}
{"etapa": "recibido", "componente": "consumidor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 2, "espera_s": 1.275, "detalle": "ErrorTransitorio('correo no responde (obj-D)')"}

# Despachador, vuelta 4 (t = 0.820 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 2}
{"etapa": "recibido", "componente": "consumidor", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 2, "espera_s": 1.223, "detalle": "ErrorTransitorio('correo no responde (obj-B)')"}

# Despachador, vuelta 5 (t = 1.788 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 3}
{"etapa": "recibido", "componente": "consumidor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 3, "espera_s": 3.473, "detalle": "ErrorTransitorio('correo no responde (obj-D)')"}

# Despachador, vuelta 6 (t = 2.043 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 3}
{"etapa": "recibido", "componente": "consumidor", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B"}
{"etapa": "entregado", "componente": "consumidor", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B"}
{"etapa": "confirmado_en_outbox", "componente": "despachador", "event_id": "a5fadec3-59ea-4a9a-92de-cbe77ee9cc39", "correlation_id": "req-B", "type": "ClaimCreated", "aggregate_id": "obj-B", "intento": 3}

# Despachador, vuelta 7 (t = 5.260 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 4}
{"etapa": "recibido", "componente": "consumidor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}
{"etapa": "reintento_programado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 4, "espera_s": 6.707, "detalle": "ErrorTransitorio('correo no responde (obj-D)')"}

# Despachador, vuelta 8 (t = 11.967 s)
{"etapa": "despachado", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 5}
{"etapa": "recibido", "componente": "consumidor", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D"}
{"etapa": "enviado_a_fallidos", "componente": "despachador", "event_id": "dc04910e-6abd-4336-8f50-98c14911b983", "correlation_id": "req-D", "type": "ClaimCreated", "aggregate_id": "obj-D", "intento": 5, "detalle": "ErrorTransitorio('correo no responde (obj-D)')"}

# Estado final del outbox (productor)
  obj-A  ClaimCreated   publicado  intentos=1 
  obj-B  ClaimCreated   publicado  intentos=3 ErrorTransitorio('correo no responde (obj-B)')
  obj-C  ClaimRejected  publicado  intentos=1 
  obj-D  ClaimCreated   fallido    intentos=5 ErrorTransitorio('correo no responde (obj-D)')

# Avisos entregados a la oficina (consumidor)
  req-A: Entregar objeto obj-A a student-1 (identidad verificada).
  req-C: Revisar intento bloqueado sobre obj-C por intruso: IDENTITY_NOT_VERIFIED.
  req-B: Entregar objeto obj-B a student-2 (identidad verificada).

# Métricas
  confirmado_en_outbox   3
  despachado             11
  duplicado_ignorado     1
  entregado              3
  enviado_a_fallidos     1
  producido              4
  recibido               11
  reintento_programado   6
```
