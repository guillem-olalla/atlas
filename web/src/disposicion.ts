// Disposicion del mapa con ELK: una columna (carril) por capa, en el orden de las capas.
import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkNode } from "elkjs/lib/elk-api";
import type { Arista, Capa, Nodo } from "./modelo";

export const ANCHO = 200;
export const ALTO = 52;
const MARGEN = 20;
const CABECERA = 36;

export interface Posicion {
  id: string;
  x: number;
  y: number;
}

export interface Carril {
  capa: Capa;
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

export interface Disposicion {
  posiciones: Posicion[];
  carriles: Carril[];
}

const elk = new ELK();

export async function disponer(capas: Capa[], nodos: Nodo[], aristas: Arista[]): Promise<Disposicion> {
  const orden = new Map(capas.map((c) => [c.id, c.orden]));
  const grafo: ElkNode = {
    id: "raiz",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.partitioning.activate": "true",
      "elk.spacing.nodeNode": "18",
      "elk.layered.spacing.nodeNodeBetweenLayers": "70",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
    },
    children: nodos.map((n) => ({
      id: n.id,
      width: ANCHO,
      height: ALTO,
      layoutOptions: { "elk.partitioning.partition": String(orden.get(n.capa) ?? 0) },
    })),
    edges: aristas.map((a, i) => ({ id: `a${i}`, sources: [a.de], targets: [a.a] })),
  };
  const resultado = await elk.layout(grafo);
  const posiciones = (resultado.children ?? []).map((c) => ({ id: c.id, x: c.x ?? 0, y: c.y ?? 0 }));
  return { posiciones, carriles: carriles(capas, nodos, posiciones) };
}

/** Un rectangulo por capa con piezas visibles, de la altura de todo el mapa. */
export function carriles(capas: Capa[], nodos: Nodo[], posiciones: Posicion[]): Carril[] {
  if (posiciones.length === 0) return [];
  const capaDe = new Map(nodos.map((n) => [n.id, n.capa]));
  const arriba = Math.min(...posiciones.map((p) => p.y)) - MARGEN - CABECERA;
  const abajo = Math.max(...posiciones.map((p) => p.y)) + ALTO + MARGEN;
  const salida: Carril[] = [];
  for (const capa of [...capas].sort((a, b) => a.orden - b.orden)) {
    const xs = posiciones.filter((p) => capaDe.get(p.id) === capa.id).map((p) => p.x);
    if (xs.length === 0) continue;
    const x = Math.min(...xs) - MARGEN;
    salida.push({ capa, x, y: arriba, ancho: Math.max(...xs) + ANCHO + MARGEN - x, alto: abajo - arriba });
  }
  return salida;
}
