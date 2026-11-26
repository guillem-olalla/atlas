import { describe, expect, it } from "vitest";
import { disponer } from "./disposicion";
import type { Arista, Capa, Nodo } from "./modelo";

const capas: Capa[] = [
  { id: "c3", orden: 3, nombre: "Tres" },
  { id: "c1", orden: 1, nombre: "Uno" },
  { id: "c2", orden: 2, nombre: "Dos" },
];

function nodo(id: string, capa: string): Nodo {
  return {
    id,
    nombre: id,
    capa,
    tipo: "servicio",
    fase: "F0",
    dueno: "x",
    riesgo: "bajo",
    ejecuta: "script",
    identidad: "-",
    donde: "-",
    existe: true,
    estado: "hecho",
  };
}

describe("disposicion por carriles", () => {
  it("pone una columna por capa, en orden y sin solaparse, y cada pieza dentro de su carril", async () => {
    const nodos = [nodo("a", "c1"), nodo("b", "c1"), nodo("c", "c2"), nodo("d", "c3"), nodo("e", "c3")];
    // Una arista "hacia atras" (de la capa 3 a la 1) no puede desordenar los carriles.
    const aristas: Arista[] = [
      { de: "a", a: "c", tipo: "lee", protocolo: "x" },
      { de: "c", a: "d", tipo: "lee", protocolo: "x" },
      { de: "e", a: "b", tipo: "notifica", protocolo: "x" },
    ];
    const { posiciones, carriles } = await disponer(capas, nodos, aristas);
    expect(carriles.map((c) => c.capa.id)).toEqual(["c1", "c2", "c3"]);
    for (let i = 1; i < carriles.length; i++) {
      expect(carriles[i].x).toBeGreaterThanOrEqual(carriles[i - 1].x + carriles[i - 1].ancho - 1);
    }
    const carrilDe = new Map(carriles.map((c) => [c.capa.id, c]));
    for (const p of posiciones) {
      const c = carrilDe.get(nodos.find((n) => n.id === p.id)!.capa)!;
      expect(p.x).toBeGreaterThanOrEqual(c.x);
      expect(p.x).toBeLessThanOrEqual(c.x + c.ancho);
    }
  });

  it("sin piezas no hay carriles", async () => {
    expect(await disponer(capas, [], [])).toEqual({ posiciones: [], carriles: [] });
  });
});
