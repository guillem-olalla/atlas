import { describe, expect, it } from "vitest";
import { alternar, avisos, filtrosIniciales, marcado, nodosDeRepo, recuento, repos, vecinos, visibles, type Arista, type Nodo } from "./modelo";

function nodo(id: string, extra: Partial<Nodo> = {}): Nodo {
  return {
    id,
    nombre: id,
    capa: "codigo",
    tipo: "servicio",
    fase: "F0",
    dueno: "persona-a",
    riesgo: "bajo",
    ejecuta: "script",
    identidad: "ninguna",
    donde: "servidor",
    existe: true,
    estado: "hecho",
    ...extra,
  };
}

const fases = ["F0", "F1", "F2"];
const nodos: Nodo[] = [
  nodo("a", { enlaces: { repo: "ejemplo/app" } }),
  nodo("b", { enlaces: { repo: "ejemplo/app" }, fase: "F1", estado: "en_curso" }),
  nodo("c", { capa: "servidor", fase: "F2", estado: "pendiente", cliente: "cliente-1" }),
  nodo("d", { capa: "servidor", tipo: "agente", estado: "bloqueado", marcas: ["personal"] }),
  nodo("e", { capa: "personas", tipo: "persona" }),
];
const aristas: Arista[] = [
  { de: "e", a: "a", tipo: "escribe", protocolo: "git" },
  { de: "a", a: "b", tipo: "dispara", protocolo: "x" },
  { de: "b", a: "c", tipo: "lee", protocolo: "x" },
  { de: "c", a: "d", tipo: "notifica", protocolo: "x" },
];
const mapa = { fases, nodos, aristas };
const ids = (r: { nodos: Nodo[] }) => r.nodos.map((n) => n.id).sort();

describe("filtros", () => {
  it("sin filtros se ve todo", () => {
    const r = visibles(mapa, filtrosIniciales(fases));
    expect(ids(r)).toEqual(["a", "b", "c", "d", "e"]);
    expect(r.aristas).toHaveLength(4);
  });

  it("el selector de fase muestra esa fase y las anteriores", () => {
    expect(ids(visibles(mapa, { ...filtrosIniciales(fases), faseMax: "F0" }))).toEqual(["a", "d", "e"]);
    expect(ids(visibles(mapa, { ...filtrosIniciales(fases), faseMax: "F1" }))).toEqual(["a", "b", "d", "e"]);
  });

  it("filtra por capa, tipo, estado y cliente, y quita las aristas a nodos ocultos", () => {
    const base = filtrosIniciales(fases);
    expect(ids(visibles(mapa, { ...base, capas: new Set(["servidor"]) }))).toEqual(["c", "d"]);
    expect(ids(visibles(mapa, { ...base, tipos: new Set(["agente"]) }))).toEqual(["d"]);
    expect(ids(visibles(mapa, { ...base, estados: new Set(["en_curso", "bloqueado"]) }))).toEqual(["b", "d"]);
    expect(ids(visibles(mapa, { ...base, clientes: new Set(["cliente-1"]) }))).toEqual(["c"]);
    const r = visibles(mapa, { ...base, capas: new Set(["servidor"]) });
    expect(r.aristas).toEqual([{ de: "c", a: "d", tipo: "notifica", protocolo: "x" }]);
  });

  it("filtra por la marca personal", () => {
    const base = filtrosIniciales(fases);
    expect(ids(visibles(mapa, { ...base, personal: "solo" }))).toEqual(["d"]);
    expect(ids(visibles(mapa, { ...base, personal: "sin" }))).toEqual(["a", "b", "c", "e"]);
  });
});

describe("aislar", () => {
  it("con 0 saltos deja solo los nodos elegidos y sus aristas entre ellos", () => {
    const f = { ...filtrosIniciales(fases), aislar: new Set(["a", "b"]), saltos: 0 };
    const r = visibles(mapa, f);
    expect(ids(r)).toEqual(["a", "b"]);
    expect(r.aristas).toEqual([{ de: "a", a: "b", tipo: "dispara", protocolo: "x" }]);
  });

  it("los saltos recorren las aristas en los dos sentidos", () => {
    expect([...vecinos(aristas, new Set(["c"]), 1)].sort()).toEqual(["b", "c", "d"]);
    expect([...vecinos(aristas, new Set(["c"]), 2)].sort()).toEqual(["a", "b", "c", "d"]);
  });

  it("aislar un proyecto muestra solo sus nodos y sus llamadas", () => {
    const delRepo = nodosDeRepo(nodos, "ejemplo/app");
    expect([...delRepo].sort()).toEqual(["a", "b"]);
    const r = visibles(mapa, { ...filtrosIniciales(fases), aislar: delRepo, saltos: 1 });
    expect(ids(r)).toEqual(["a", "b", "c", "e"]);
    expect(r.aristas.map((x) => `${x.de}->${x.a}`)).toEqual(["e->a", "a->b", "b->c"]);
  });

  it("aislar respeta los demas filtros", () => {
    const f = { ...filtrosIniciales(fases), faseMax: "F1", aislar: new Set(["b"]), saltos: 3 };
    expect(ids(visibles(mapa, f))).toEqual(["a", "b", "e"]);
  });

  it("lista los repos sin repetir", () => {
    expect(repos(nodos)).toEqual(["ejemplo/app"]);
  });
});

describe("alternar", () => {
  const todos = ["x", "y", "z"];
  it("vacio es todos; desmarcar uno deja los demas", () => {
    expect([...alternar(new Set(), "x", todos)].sort()).toEqual(["y", "z"]);
  });
  it("volver a marcarlos todos deja el conjunto vacio", () => {
    expect(alternar(new Set(["y", "z"]), "x", todos).size).toBe(0);
    expect(marcado(new Set(), "x")).toBe(true);
    expect(marcado(new Set(["y"]), "x")).toBe(false);
  });
});

describe("avisos", () => {
  const ahora = new Date("2026-06-01T12:00:00Z");
  const bien = {
    generado_en: "2026-06-01T11:50:00Z",
    token_caduca: "2026-12-01T00:00:00Z",
    error: null,
    errores_manifiesto: [] as string[],
  };

  it("sin avisos con datos frescos y token lejos de caducar", () => {
    expect(avisos(bien, ahora)).toEqual([]);
  });

  it("avisa si los datos tienen mas de 15 minutos", () => {
    expect(avisos({ ...bien, generado_en: "2026-06-01T11:45:00Z" }, ahora)).toEqual([]);
    const r = avisos({ ...bien, generado_en: "2026-06-01T11:44:00Z" }, ahora);
    expect(r).toHaveLength(1);
    expect(r[0].tipo).toBe("datos_viejos");
    expect(r[0].texto).toContain("16 minutos");
  });

  it("avisa si el token caduca en menos de 14 dias o ya ha caducado", () => {
    expect(avisos({ ...bien, token_caduca: "2026-06-15T12:00:01Z" }, ahora)).toEqual([]);
    const pronto = avisos({ ...bien, token_caduca: "2026-06-14T12:00:00Z" }, ahora);
    expect(pronto.map((a) => a.tipo)).toEqual(["token"]);
    expect(pronto[0].texto).toContain("13 días");
    expect(avisos({ ...bien, token_caduca: "2026-05-31T00:00:00Z" }, ahora)[0].texto).toContain("caducó");
  });

  it("avisa si no se conoce la caducidad, si falla la lectura y si el manifiesto tiene errores", () => {
    const r = avisos({ ...bien, token_caduca: null, error: "GitHub caido", errores_manifiesto: ["x"] }, ahora);
    expect(r.map((a) => a.tipo)).toEqual(["token", "error", "manifiesto"]);
    expect(avisos(bien, ahora, "sin red")[0].texto).toContain("sin red");
  });
});

describe("recuento", () => {
  it("cuenta por estado", () => {
    expect(recuento(nodos)).toEqual({ hecho: 2, en_curso: 1, bloqueado: 1, pendiente: 1, desconocido: 0 });
  });
});
