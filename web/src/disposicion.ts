// Disposicion del mapa: una columna (carril) por capa, en el orden de las capas.
//
// ELK (layered, de izquierda a derecha) ordena las piezas para reducir cruces de aristas; despues
// cada pieza va a la columna de su capa, en el orden vertical que le dio ELK. Las particiones de
// ELK no bastan: con aristas "hacia atras" (de una capa a otra anterior) los carriles se solapan.
// Una capa con muchas piezas se parte en subcolumnas de FILAS como mucho.
import ELK from "elkjs/lib/elk.bundled.js";
import type { ElkNode } from "elkjs/lib/elk-api";
import type { Arista, Capa, Nodo } from "./modelo";

export const ANCHO = 200;
export const ALTO = 52;
export const FILAS = 14;
const SEP_FILA = 16;
const SEP_SUBCOLUMNA = 24;
const SEP_CARRIL = 70;
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

/** Orden de ELK: posicion (y, x) de cada pieza en un layered de izquierda a derecha. */
async function ordenElk(nodos: Nodo[], aristas: Arista[]): Promise<Map<string, [number, number]>> {
  const grafo: ElkNode = {
    id: "raiz",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "18",
      "elk.layered.spacing.nodeNodeBetweenLayers": "60",
    },
    children: nodos.map((n) => ({ id: n.id, width: ANCHO, height: ALTO })),
    edges: aristas.map((a, i) => ({ id: `a${i}`, sources: [a.de], targets: [a.a] })),
  };
  const resultado = await elk.layout(grafo);
  return new Map((resultado.children ?? []).map((c) => [c.id, [c.y ?? 0, c.x ?? 0]]));
}

export async function disponer(capas: Capa[], nodos: Nodo[], aristas: Arista[]): Promise<Disposicion> {
  if (nodos.length === 0) return { posiciones: [], carriles: [] };
  const orden = await ordenElk(nodos, aristas);
  const posiciones: Posicion[] = [];
  let x = 0;
  for (const capa of [...capas].sort((a, b) => a.orden - b.orden)) {
    const propias = nodos
      .filter((n) => n.capa === capa.id)
      .sort((a, b) => {
        const [ya, xa] = orden.get(a.id) ?? [0, 0];
        const [yb, xb] = orden.get(b.id) ?? [0, 0];
        return ya - yb || xa - xb || a.id.localeCompare(b.id);
      });
    if (propias.length === 0) continue;
    const subcolumnas = Math.ceil(propias.length / FILAS);
    const filas = Math.ceil(propias.length / subcolumnas);
    propias.forEach((n, i) => {
      const col = Math.floor(i / filas);
      posiciones.push({ id: n.id, x: x + col * (ANCHO + SEP_SUBCOLUMNA), y: (i % filas) * (ALTO + SEP_FILA) });
    });
    x += subcolumnas * ANCHO + (subcolumnas - 1) * SEP_SUBCOLUMNA + SEP_CARRIL;
  }
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
