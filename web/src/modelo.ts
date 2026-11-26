// Modelo del mapa: tipos, filtros, aislar y avisos. Todo puro, para poder probarlo sin navegador.

export type Estado = "hecho" | "en_curso" | "bloqueado" | "pendiente" | "desconocido";

export interface Capa {
  id: string;
  orden: number;
  nombre: string;
}

export interface Nodo {
  id: string;
  nombre: string;
  capa: string;
  tipo: string;
  fase: string;
  dueno: string;
  riesgo: string;
  ejecuta: string;
  identidad: string;
  donde: string;
  existe: boolean;
  estado: Estado;
  marcas?: string[];
  cliente?: string;
  issue?: number;
  issue_url?: string;
  mejoras?: number[];
  enlaces?: { repo?: string; doc?: string };
  cubre?: string[];
}

export interface Arista {
  de: string;
  a: string;
  tipo: string;
  protocolo: string;
}

export interface Mapa {
  version: number;
  actualizado: string;
  capas: Capa[];
  fases: string[];
  nodos: Nodo[];
  aristas: Arista[];
  errores_manifiesto: string[];
  generado_en: string;
  token_caduca: string | null;
  error: string | null;
}

export const ESTADOS: Estado[] = ["hecho", "en_curso", "bloqueado", "pendiente", "desconocido"];

export const NOMBRE_ESTADO: Record<Estado, string> = {
  hecho: "Hecho",
  en_curso: "En curso",
  bloqueado: "Bloqueado",
  pendiente: "Pendiente",
  desconocido: "Desconocido",
};

export const SIN_CLIENTE = "-";

export interface Filtros {
  faseMax: string; // se ven las piezas de esa fase y de las anteriores
  capas: Set<string>; // vacio = todas
  tipos: Set<string>;
  estados: Set<string>;
  clientes: Set<string>; // SIN_CLIENTE para las piezas sin cliente
  personal: "todos" | "solo" | "sin";
  aislar: Set<string>; // vacio = sin aislar
  saltos: number;
}

export function filtrosIniciales(fases: string[]): Filtros {
  return {
    faseMax: fases[fases.length - 1] ?? "",
    capas: new Set(),
    tipos: new Set(),
    estados: new Set(),
    clientes: new Set(),
    personal: "todos",
    aislar: new Set(),
    saltos: 1,
  };
}

/** Marca o desmarca `valor` en un filtro donde el conjunto vacio significa "todos". */
export function alternar(seleccion: Set<string>, valor: string, todos: string[]): Set<string> {
  const actual = seleccion.size === 0 ? new Set(todos) : new Set(seleccion);
  if (actual.has(valor)) actual.delete(valor);
  else actual.add(valor);
  return actual.size === todos.length ? new Set() : actual;
}

export function marcado(seleccion: Set<string>, valor: string): boolean {
  return seleccion.size === 0 || seleccion.has(valor);
}

/** Nodos a `saltos` o menos de las semillas, recorriendo las aristas en los dos sentidos. */
export function vecinos(aristas: Arista[], semillas: Set<string>, saltos: number, dentro?: Set<string>): Set<string> {
  const adyacentes = new Map<string, string[]>();
  for (const a of aristas) {
    if (dentro && (!dentro.has(a.de) || !dentro.has(a.a))) continue;
    adyacentes.set(a.de, [...(adyacentes.get(a.de) ?? []), a.a]);
    adyacentes.set(a.a, [...(adyacentes.get(a.a) ?? []), a.de]);
  }
  const vistos = new Set(semillas);
  let frontera = [...semillas];
  for (let i = 0; i < saltos && frontera.length > 0; i++) {
    const siguiente: string[] = [];
    for (const id of frontera) {
      for (const otro of adyacentes.get(id) ?? []) {
        if (!vistos.has(otro)) {
          vistos.add(otro);
          siguiente.push(otro);
        }
      }
    }
    frontera = siguiente;
  }
  return vistos;
}

export function visibles(mapa: Pick<Mapa, "fases" | "nodos" | "aristas">, f: Filtros): { nodos: Nodo[]; aristas: Arista[] } {
  const tope = mapa.fases.indexOf(f.faseMax);
  const pasa = (n: Nodo): boolean => {
    if (tope >= 0 && mapa.fases.indexOf(n.fase) > tope) return false;
    if (!marcado(f.capas, n.capa) || !marcado(f.tipos, n.tipo) || !marcado(f.estados, n.estado)) return false;
    if (!marcado(f.clientes, n.cliente ?? SIN_CLIENTE)) return false;
    const personal = (n.marcas ?? []).includes("personal");
    if (f.personal === "solo" && !personal) return false;
    if (f.personal === "sin" && personal) return false;
    return true;
  };
  let ids = new Set(mapa.nodos.filter(pasa).map((n) => n.id));
  if (f.aislar.size > 0) {
    const semillas = new Set([...f.aislar].filter((id) => ids.has(id)));
    ids = vecinos(mapa.aristas, semillas, f.saltos, ids);
  }
  return {
    nodos: mapa.nodos.filter((n) => ids.has(n.id)),
    aristas: mapa.aristas.filter((a) => ids.has(a.de) && ids.has(a.a)),
  };
}

export function repos(nodos: Nodo[]): string[] {
  return [...new Set(nodos.map((n) => n.enlaces?.repo).filter((r): r is string => !!r))].sort();
}

/** Las piezas de un proyecto: los nodos que enlazan su repo. */
export function nodosDeRepo(nodos: Nodo[], repo: string): Set<string> {
  return new Set(nodos.filter((n) => n.enlaces?.repo === repo).map((n) => n.id));
}

export function recuento(nodos: Nodo[]): Record<Estado, number> {
  const r = Object.fromEntries(ESTADOS.map((e) => [e, 0])) as Record<Estado, number>;
  for (const n of nodos) r[n.estado] = (r[n.estado] ?? 0) + 1;
  return r;
}

export const MAX_EDAD_MINUTOS = 15;
export const DIAS_AVISO_TOKEN = 14;

export interface Aviso {
  tipo: "datos_viejos" | "token" | "error" | "manifiesto";
  texto: string;
}

type DatosAviso = Pick<Mapa, "generado_en" | "token_caduca" | "error" | "errores_manifiesto">;

const MINUTO = 60_000;
const DIA = 86_400_000;

function fecha(iso: string): string {
  return iso.slice(0, 10);
}

/** Avisos visibles: datos de mas de 15 minutos, token a menos de 14 dias, errores de lectura o del manifiesto. */
export function avisos(m: DatosAviso, ahora: Date, errorCarga: string | null = null): Aviso[] {
  const salida: Aviso[] = [];
  const edad = (ahora.getTime() - Date.parse(m.generado_en)) / MINUTO;
  if (!Number.isFinite(edad) || edad > MAX_EDAD_MINUTOS) {
    const minutos = Number.isFinite(edad) ? Math.floor(edad) : "?";
    salida.push({ tipo: "datos_viejos", texto: `Los datos tienen ${minutos} minutos (más de ${MAX_EDAD_MINUTOS}): no se están refrescando.` });
  }
  if (!m.token_caduca) {
    salida.push({ tipo: "token", texto: "GitHub no ha dado la fecha de caducidad del token de lectura: compruébala." });
  } else {
    const dias = (Date.parse(m.token_caduca) - ahora.getTime()) / DIA;
    if (dias <= 0) {
      salida.push({ tipo: "token", texto: `El token de lectura caducó el ${fecha(m.token_caduca)}.` });
    } else if (dias < DIAS_AVISO_TOKEN) {
      salida.push({
        tipo: "token",
        texto: `El token de lectura caduca en ${Math.ceil(dias)} días (el ${fecha(m.token_caduca)}): renuévalo.`,
      });
    }
  }
  const error = errorCarga ?? m.error;
  if (error) salida.push({ tipo: "error", texto: `La última lectura falló: ${error}` });
  if (m.errores_manifiesto.length > 0) {
    salida.push({ tipo: "manifiesto", texto: `El manifiesto tiene ${m.errores_manifiesto.length} errores de validación.` });
  }
  return salida;
}
