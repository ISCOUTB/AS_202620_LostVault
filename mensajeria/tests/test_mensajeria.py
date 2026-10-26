"""Pruebas del Taller de Sistemas de Mensajes (ver docs/mensajeria/taller-mensajeria.md)."""

import copy
import json
import logging

import pytest

from mensajeria import consumidor as cons
from mensajeria import productor as prod
from mensajeria.consumidor import ErrorTransitorio, Notificador
from mensajeria.contrato import ContratoInvalido, nuevo_evento, validar
from mensajeria.despachador import CaidaSimulada, Despachador


class Reloj:
    def __init__(self) -> None:
        self.t = 1_000.0

    def __call__(self) -> float:
        return self.t

    def avanzar(self, segundos: float) -> None:
        self.t += segundos


class TransporteQueFalla:
    """Falla `veces` veces con ErrorTransitorio y luego funciona."""

    def __init__(self, veces: int) -> None:
        self.restantes = veces
        self.llamadas = 0

    def __call__(self, evento: dict) -> None:
        self.llamadas += 1
        if self.restantes > 0:
            self.restantes -= 1
            raise ErrorTransitorio("servicio de correo no responde")


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def db_productor():
    conn = prod.abrir()
    prod.sembrar_objeto(conn, "obj-001", "Termo negro")
    prod.sembrar_objeto(conn, "obj-002", "Sombrilla azul")
    return conn


@pytest.fixture
def db_consumidor():
    return cons.abrir()


def despachador(db_productor, notificador, reloj, **kw):
    # aleatorio fijo = 1.0 -> espera = techo (determinista en las pruebas)
    return Despachador(db_productor, notificador, reloj=reloj, aleatorio=lambda: 1.0, **kw)


def avisos(db_consumidor):
    return db_consumidor.execute("SELECT * FROM avisos").fetchall()


def estado_outbox(db_productor):
    return [dict(r) for r in db_productor.execute(
        "SELECT event_id, type, estado, intentos FROM outbox ORDER BY seq")]


# 1. Contrato y compatibilidad ------------------------------------------------

def test_evento_producido_cumple_el_contrato(db_productor):
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    payload = json.loads(db_productor.execute("SELECT payload FROM outbox").fetchone()[0])
    validar(payload)
    assert payload["type"] == "ClaimCreated"
    assert payload["schema_version"] == 1
    assert payload["correlation_id"] == "req-1"


def test_consumidor_acepta_campos_nuevos_opcionales(db_consumidor):
    """Compatibilidad hacia adelante: un productor más nuevo agrega campos."""
    evento = nuevo_evento("ClaimCreated", "obj-001", "student-42", "req-1", officeId="bloque-A")
    evento["priority"] = "alta"
    assert Notificador(db_consumidor).recibir(evento) is True


@pytest.mark.parametrize("romper", [
    lambda e: e.pop("event_id"),
    lambda e: e["data"].pop("userId"),
    lambda e: e.update(schema_version=2),
    lambda e: e.update(type="ClaimDeleted"),
])
def test_cambios_incompatibles_violan_el_contrato(romper):
    evento = nuevo_evento("ClaimCreated", "obj-001", "student-42", "req-1")
    romper(evento)
    with pytest.raises(ContratoInvalido):
        validar(evento)


def test_claim_rejected_exige_reason():
    evento = nuevo_evento("ClaimRejected", "obj-001", "student-42", "req-1")
    with pytest.raises(ContratoInvalido):
        validar(evento)


# 2. Garantía de entrega: el evento es atómico con la reclamación --------------

def test_si_la_transaccion_falla_no_queda_ni_reclamacion_ni_evento(db_productor):
    def caida():
        raise RuntimeError("se cae antes del COMMIT")

    with pytest.raises(RuntimeError):
        prod.reclamar(db_productor, "obj-001", "student-42", "req-1", antes_de_confirmar=caida)
    assert db_productor.execute("SELECT COUNT(*) FROM outbox").fetchone()[0] == 0
    assert db_productor.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 0
    status = db_productor.execute("SELECT status FROM objects WHERE id='obj-001'").fetchone()[0]
    assert status == "available"


def test_segunda_reclamacion_del_mismo_objeto_no_genera_evento(db_productor):
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    with pytest.raises(prod.ObjetoYaReclamado):
        prod.reclamar(db_productor, "obj-001", "otro", "req-2")
    assert len(estado_outbox(db_productor)) == 1


def test_identidad_invalida_publica_claim_rejected_sin_reclamar(db_productor, db_consumidor, reloj):
    assert prod.reclamar(db_productor, "obj-001", "intruso", "req-9", identidad_valida=False) is None
    despachador(db_productor, Notificador(db_consumidor), reloj).despachar_pendientes()
    assert "IDENTITY_NOT_VERIFIED" in avisos(db_consumidor)[0]["texto"]
    status = db_productor.execute("SELECT status FROM objects WHERE id='obj-001'").fetchone()[0]
    assert status == "available"


# 3. Duplicados ---------------------------------------------------------------

def test_duplicado_por_caida_tras_entregar_produce_un_solo_aviso(db_productor, db_consumidor, reloj):
    """El despachador entrega, se cae antes de marcar 'publicado' y al volver reenvía."""
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    d = despachador(db_productor, Notificador(db_consumidor), reloj)
    d.caer_tras_entregar = lambda evento: True
    with pytest.raises(CaidaSimulada):
        d.despachar_pendientes()
    assert estado_outbox(db_productor)[0]["estado"] == "pendiente"  # no alcanzó a marcar

    d.caer_tras_entregar = lambda evento: False  # el proceso reinicia
    assert d.despachar_pendientes() == 1
    assert len(avisos(db_consumidor)) == 1  # entregado 2 veces, efecto 1 vez
    assert estado_outbox(db_productor)[0]["estado"] == "publicado"


def test_mismo_mensaje_recibido_dos_veces_se_ignora_la_segunda(db_consumidor):
    evento = nuevo_evento("ClaimCreated", "obj-001", "student-42", "req-1")
    notificador = Notificador(db_consumidor)
    assert notificador.recibir(evento) is True
    assert notificador.recibir(copy.deepcopy(evento)) is False
    assert len(avisos(db_consumidor)) == 1


# 4. Reintentos, backoff y fallidos -------------------------------------------

def test_fallo_recuperable_se_reintenta_con_backoff_y_se_entrega_una_vez(
    db_productor, db_consumidor, reloj
):
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    transporte = TransporteQueFalla(veces=2)
    d = despachador(db_productor, Notificador(db_consumidor, transporte), reloj)

    assert d.despachar_pendientes() == 0  # intento 1 falla -> espera 1 s
    assert d.despachar_pendientes() == 0  # aún no toca: no reintenta antes de tiempo
    assert transporte.llamadas == 1

    reloj.avanzar(1)
    assert d.despachar_pendientes() == 0  # intento 2 falla -> espera 2 s
    reloj.avanzar(1.5)
    assert d.despachar_pendientes() == 0  # 1.5 s < 2 s: sigue esperando
    reloj.avanzar(0.5)
    assert d.despachar_pendientes() == 1  # intento 3 funciona

    assert transporte.llamadas == 3
    assert len(avisos(db_consumidor)) == 1
    fila = estado_outbox(db_productor)[0]
    assert (fila["estado"], fila["intentos"]) == ("publicado", 3)


def test_backoff_exponencial_con_tope_y_jitter(db_productor, db_consumidor, reloj):
    d = Despachador(db_productor, Notificador(db_consumidor), reloj=reloj,
                    aleatorio=lambda: 0.0, base_segundos=1, tope_segundos=8)
    assert [d.espera(i) for i in range(1, 6)] == [0.5, 1, 2, 4, 4]  # mitad del techo
    d.aleatorio = lambda: 1.0
    assert [d.espera(i) for i in range(1, 6)] == [1, 2, 4, 8, 8]  # techo completo, con tope


def test_tras_max_intentos_va_a_fallidos_y_no_se_reintenta(db_productor, db_consumidor, reloj):
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    transporte = TransporteQueFalla(veces=100)
    d = despachador(db_productor, Notificador(db_consumidor, transporte), reloj, max_intentos=3)
    for _ in range(5):
        d.despachar_pendientes()
        reloj.avanzar(60)
    assert transporte.llamadas == 3
    [fallido] = d.fallidos()
    assert fallido["intentos"] == 3 and "ErrorTransitorio" in fallido["ultimo_error"]
    assert avisos(db_consumidor) == []

    # Redrive manual cuando el destino se recupera
    transporte.restantes = 0
    d.reprocesar(fallido["event_id"])
    assert d.despachar_pendientes() == 1
    assert len(avisos(db_consumidor)) == 1


def test_mensaje_fuera_de_contrato_va_a_fallidos_sin_reintentar(db_productor, db_consumidor, reloj):
    prod.reclamar(db_productor, "obj-001", "student-42", "req-1")
    payload = json.loads(db_productor.execute("SELECT payload FROM outbox").fetchone()[0])
    del payload["data"]["userId"]  # mensaje corrupto (p. ej. productor con un bug)
    with db_productor:
        db_productor.execute("UPDATE outbox SET payload = ?", (json.dumps(payload),))
    d = despachador(db_productor, Notificador(db_consumidor), reloj)
    d.despachar_pendientes()
    [fallido] = d.fallidos()
    assert fallido["intentos"] == 1 and fallido["ultimo_error"].startswith("contrato:")


def test_orden_por_objeto_se_respeta_y_otros_objetos_no_se_bloquean(
    db_productor, db_consumidor, reloj
):
    prod.reclamar(db_productor, "obj-001", "intruso", "req-1", identidad_valida=False)
    prod.reclamar(db_productor, "obj-001", "student-42", "req-2")
    prod.reclamar(db_productor, "obj-002", "student-7", "req-3")

    fallar_primero = TransporteQueFalla(veces=1)
    d = despachador(db_productor, Notificador(db_consumidor, fallar_primero), reloj)
    assert d.despachar_pendientes() == 1  # solo obj-002; obj-001 espera su reintento
    assert [a["object_id"] for a in avisos(db_consumidor)] == ["obj-002"]

    reloj.avanzar(1)
    assert d.despachar_pendientes() == 2
    obj1 = db_consumidor.execute(
        "SELECT correlation_id FROM avisos WHERE object_id='obj-001' ORDER BY rowid"
    ).fetchall()
    assert [r[0] for r in obj1] == ["req-1", "req-2"]  # mismo orden que en el outbox


# 6. Trazabilidad -------------------------------------------------------------

def test_un_mensaje_se_puede_seguir_por_correlation_id(db_productor, db_consumidor, reloj, caplog):
    with caplog.at_level(logging.INFO, logger="lostvault.mensajeria"):
        prod.reclamar(db_productor, "obj-001", "student-42", "req-trace")
        d = despachador(db_productor, Notificador(db_consumidor, TransporteQueFalla(1)), reloj)
        d.despachar_pendientes()
        reloj.avanzar(1)
        d.despachar_pendientes()

    trazas = [r.traza for r in caplog.records if getattr(r, "traza", {}).get("correlation_id") == "req-trace"]
    assert [t["etapa"] for t in trazas] == [
        "producido", "despachado", "recibido", "reintento_programado",
        "despachado", "recibido", "entregado", "confirmado_en_outbox",
    ]
    assert len({t["event_id"] for t in trazas}) == 1
    assert {t["componente"] for t in trazas} == {"productor", "despachador", "consumidor"}
    # cada línea de log es JSON válido
    for r in caplog.records:
        json.loads(r.getMessage())
