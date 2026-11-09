// Medición S14 — Escenario 4 (rendimiento de la búsqueda).
// Versión consolidada, en un solo archivo, de los dos fragmentos que se ejecutaron en la
// consola de un navegador Chromium abierto en https://backend-nu-self-91.vercel.app/health
// (mismo origen, así no hay CORS): uno con las corridas A y B y otro con la corrida C.
// La lógica de medición es la misma.
// Resultados crudos: docs/medicion/s14-resultados-crudos.json
//
// Corridas:
//   A  200 peticiones simultáneas x 5 rondas, misma URL por término, fetch con cache:"no-store".
//      Es la primera ráfaga sobre una sola instancia caliente: obliga a Vercel a escalar.
//   B  Igual, pero cada URL es única (&nocache=...), así cada petición llega al origen y el
//      navegador no las serializa (Chrome bloquea en su caché las URL idénticas en vuelo).
//   C  Base secuencial (30 búsquedas, una tras otra) + 200 x 5 con caché por defecto, separando
//      con Resource Timing la espera en la cola del navegador de la espera del servidor (TTFB).

const BASE = location.origin;
const terms = ["termo", "negro", "biblioteca", "llaves", "cuaderno"];

function pct(a, p) {
  const s = [...a].sort((x, y) => x - y);
  return +s[Math.max(0, Math.ceil((p / 100) * s.length) - 1)].toFixed(1);
}
function summ(a) {
  return { n: a.length, p50: pct(a, 50), p95: pct(a, 95), p99: pct(a, 99), max: +Math.max(...a).toFixed(1) };
}
async function one(url, init) {
  const t = performance.now();
  try {
    const r = await fetch(url, init);
    await r.text();
    return { ms: performance.now() - t, status: r.status, cache: r.headers.get("x-vercel-cache") };
  } catch (e) {
    return { ms: performance.now() - t, status: 0, err: String(e) };
  }
}
async function rafagas(bust, init, users = 200, rounds = 5) {
  const all = [], wall = [];
  for (let r = 0; r < rounds; r++) {
    const t0 = performance.now();
    const res = await Promise.all(Array.from({ length: users }, (_, i) => {
      const u = `${BASE}/objects?q=${terms[i % terms.length]}` + (bust ? `&nocache=${Date.now()}-${r}-${i}` : "");
      return one(u, init);
    }));
    wall.push(Math.round(performance.now() - t0));
    all.push(...res);
  }
  const ok = all.filter((x) => x.status === 200);
  return { ...summ(ok.map((x) => x.ms)), requests: all.length, errors: all.length - ok.length, roundWallMs: wall };
}

async function medir() {
  performance.setResourceTimingBufferSize(10000);
  await one(`${BASE}/objects?q=termo`); // calentamiento
  const A = await rafagas(false, { cache: "no-store" });
  const B = await rafagas(true, { cache: "no-store" });

  const seq = [];
  for (let i = 0; i < 30; i++) seq.push(await one(`${BASE}/objects?q=${terms[i % 5]}&seq=${Date.now()}-${i}`));
  performance.clearResourceTimings();
  const C = await rafagas(false, undefined);
  const rt = performance.getEntriesByType("resource").filter((e) => e.name.includes("/objects?q="));
  return {
    A, B,
    base_secuencial: summ(seq.map((x) => x.ms)),
    C_total: C,
    C_cola_navegador: summ(rt.map((e) => e.requestStart - e.startTime)),
    C_servidor_ttfb: summ(rt.map((e) => e.responseStart - e.requestStart)),
  };
}

medir().then((r) => console.log(JSON.stringify(r, null, 2)));
