import { Background, Controls, Handle, MiniMap, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";
import { ALTO, ANCHO, disponer, type Disposicion } from "./disposicion";
import {
  alternar,
  avisos,
  ESTADOS,
  filtrosIniciales,
  marcado,
  NOMBRE_ESTADO,
  nodosDeRepo,
  recuento,
  repos,
  SIN_CLIENTE,
  visibles,
  type Filtros,
  type Mapa,
  type Nodo,
} from "./modelo";

const REFRESCO_MS = 60_000;
const RELOJ_MS = 30_000;

type DatosPieza = { nodo: Nodo; elegido: boolean };
type DatosCarril = { nombre: string; ancho: number; alto: number };

function Pieza({ data }: NodeProps<Node<DatosPieza>>) {
  const n = data.nodo;
  return (
    <div className={`pieza estado-${n.estado}${data.elegido ? " elegida" : ""}`} title={`${n.id}: ${NOMBRE_ESTADO[n.estado]}`}>
      <Handle type="target" position={Position.Left} />
      <div className="pieza-nombre">{n.nombre}</div>
      <div className="pieza-meta">
        {n.tipo} · {n.fase} · {NOMBRE_ESTADO[n.estado]}
        {(n.marcas ?? []).includes("personal") ? " · personal" : ""}
      </div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

function CarrilVista({ data }: NodeProps<Node<DatosCarril>>) {
  return (
    <div className="carril" style={{ width: data.ancho, height: data.alto }}>
      <div className="carril-nombre">{data.nombre}</div>
    </div>
  );
}

const tiposNodo = { pieza: Pieza, carril: CarrilVista };

function Casillas({ titulo, valores, nombres, seleccion, cambiar }: {
  titulo: string;
  valores: string[];
  nombres?: Record<string, string>;
  seleccion: Set<string>;
  cambiar: (s: Set<string>) => void;
}) {
  return (
    <fieldset>
      <legend>{titulo}</legend>
      {valores.map((v) => (
        <label key={v}>
          <input type="checkbox" checked={marcado(seleccion, v)} onChange={() => cambiar(alternar(seleccion, v, valores))} />
          {nombres?.[v] ?? v}
        </label>
      ))}
    </fieldset>
  );
}

export function App() {
  const [mapa, setMapa] = useState<Mapa | null>(null);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<Filtros | null>(null);
  const [elegido, setElegido] = useState<string | null>(null);
  const [ahora, setAhora] = useState(() => new Date());
  const [disposicion, setDisposicion] = useState<Disposicion | null>(null);

  useEffect(() => {
    let vivo = true;
    async function cargar() {
      try {
        const r = await fetch("/api/mapa", { cache: "no-store" });
        const datos = await r.json();
        if (!r.ok) throw new Error(datos.error ?? `HTTP ${r.status}`);
        if (!vivo) return;
        setMapa(datos as Mapa);
        setErrorCarga(null);
        setFiltros((f) => f ?? filtrosIniciales((datos as Mapa).fases));
      } catch (e) {
        if (vivo) setErrorCarga(e instanceof Error ? e.message : String(e));
      }
    }
    cargar();
    const t1 = setInterval(cargar, REFRESCO_MS);
    const t2 = setInterval(() => setAhora(new Date()), RELOJ_MS);
    return () => {
      vivo = false;
      clearInterval(t1);
      clearInterval(t2);
    };
  }, []);

  const vista = useMemo(() => (mapa && filtros ? visibles(mapa, filtros) : null), [mapa, filtros]);
  const claveVista = vista ? vista.nodos.map((n) => n.id).join(",") + "|" + vista.aristas.length : "";

  useEffect(() => {
    if (!mapa || !vista) return;
    let vivo = true;
    disponer(mapa.capas, vista.nodos, vista.aristas).then((d) => vivo && setDisposicion(d));
    return () => {
      vivo = false;
    };
    // Solo se recoloca cuando cambia lo que se ve, no en cada refresco de estados.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claveVista]);

  const flujo = useMemo(() => {
    if (!vista || !disposicion) return { nodes: [] as Node[], edges: [] as Edge[] };
    const porId = new Map(vista.nodos.map((n) => [n.id, n]));
    const carriles: Node[] = disposicion.carriles.map((c) => ({
      id: `carril-${c.capa.id}`,
      type: "carril",
      position: { x: c.x, y: c.y },
      data: { nombre: `${c.capa.orden}. ${c.capa.nombre}`, ancho: c.ancho, alto: c.alto },
      selectable: false,
      draggable: false,
      zIndex: -1,
    }));
    const piezas: Node[] = disposicion.posiciones
      .filter((p) => porId.has(p.id))
      .map((p) => ({
        id: p.id,
        type: "pieza",
        position: { x: p.x, y: p.y },
        data: { nodo: porId.get(p.id)!, elegido: p.id === elegido },
        width: ANCHO,
        height: ALTO,
      }));
    const edges: Edge[] = vista.aristas.map((a, i) => ({
      id: `${a.de}->${a.a}#${i}`,
      source: a.de,
      target: a.a,
      label: elegido && (a.de === elegido || a.a === elegido) ? `${a.tipo}: ${a.protocolo}` : undefined,
      className: `arista-${a.tipo}${elegido && (a.de === elegido || a.a === elegido) ? " arista-elegida" : ""}`,
    }));
    return { nodes: [...carriles, ...piezas], edges };
  }, [vista, disposicion, elegido]);

  if (!mapa || !filtros || !vista) {
    return <div className="cargando">{errorCarga ? `No se pudo cargar el mapa: ${errorCarga}` : "Cargando el mapa…"}</div>;
  }

  const lista = avisos(mapa, ahora, errorCarga);
  const cuenta = recuento(vista.nodos);
  const nodoElegido = mapa.nodos.find((n) => n.id === elegido) ?? null;
  const tipos = [...new Set(mapa.nodos.map((n) => n.tipo))].sort();
  const clientes = [...new Set(mapa.nodos.map((n) => n.cliente ?? SIN_CLIENTE))].sort();
  const nombresClientes = { [SIN_CLIENTE]: "sin cliente" };
  const poner = (cambio: Partial<Filtros>) => setFiltros({ ...filtros, ...cambio });

  return (
    <div className="app">
      <header>
        <h1>Atlas</h1>
        <span className="cuenta">
          {vista.nodos.length} de {mapa.nodos.length} piezas ·{" "}
          {ESTADOS.filter((e) => cuenta[e] > 0).map((e) => (
            <span key={e} className={`chip estado-${e}`}>
              {NOMBRE_ESTADO[e]} {cuenta[e]}
            </span>
          ))}
        </span>
        <span className="sello">
          Manifiesto v{mapa.version} del {mapa.actualizado} · datos de {new Date(mapa.generado_en).toLocaleString("es-ES")}
        </span>
      </header>
      {lista.length > 0 && (
        <div className="avisos" role="alert">
          {lista.map((a) => (
            <div key={a.tipo} className={`aviso aviso-${a.tipo}`}>
              {a.texto}
            </div>
          ))}
        </div>
      )}
      <main>
        <aside className="filtros">
          <label>
            Fase hasta{" "}
            <select value={filtros.faseMax} onChange={(e) => poner({ faseMax: e.target.value })}>
              {mapa.fases.map((f) => (
                <option key={f}>{f}</option>
              ))}
            </select>
          </label>
          <Casillas
            titulo="Capas"
            valores={mapa.capas.map((c) => c.id)}
            nombres={Object.fromEntries(mapa.capas.map((c) => [c.id, c.nombre]))}
            seleccion={filtros.capas}
            cambiar={(s) => poner({ capas: s })}
          />
          <Casillas titulo="Estado" valores={ESTADOS} nombres={NOMBRE_ESTADO} seleccion={filtros.estados} cambiar={(s) => poner({ estados: s })} />
          <Casillas titulo="Tipo (agente, servicio…)" valores={tipos} seleccion={filtros.tipos} cambiar={(s) => poner({ tipos: s })} />
          <Casillas titulo="Cliente" valores={clientes} nombres={nombresClientes} seleccion={filtros.clientes} cambiar={(s) => poner({ clientes: s })} />
          <fieldset>
            <legend>Marca personal</legend>
            {(["todos", "solo", "sin"] as const).map((v) => (
              <label key={v}>
                <input type="radio" name="personal" checked={filtros.personal === v} onChange={() => poner({ personal: v })} />
                {{ todos: "todas las piezas", solo: "solo personales", sin: "sin personales" }[v]}
              </label>
            ))}
          </fieldset>
          <fieldset>
            <legend>Aislar</legend>
            <label>
              Proyecto{" "}
              <select value="" onChange={(e) => e.target.value && poner({ aislar: nodosDeRepo(mapa.nodos, e.target.value) })}>
                <option value="">elige un repo…</option>
                {repos(mapa.nodos).map((r) => (
                  <option key={r} value={r}>
                    {r.split("/")[1]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Vecinos a{" "}
              <input type="number" min={0} max={6} value={filtros.saltos} onChange={(e) => poner({ saltos: Math.max(0, Number(e.target.value) || 0) })} />{" "}
              saltos
            </label>
            {filtros.aislar.size > 0 && (
              <>
                <div className="aislados">{[...filtros.aislar].sort().join(", ")}</div>
                <button onClick={() => poner({ aislar: new Set() })}>Quitar aislamiento</button>
              </>
            )}
          </fieldset>
          <button onClick={() => setFiltros(filtrosIniciales(mapa.fases))}>Quitar todos los filtros</button>
        </aside>
        <section className="lienzo">
          <ReactFlow
            key={claveVista}
            nodes={flujo.nodes}
            edges={flujo.edges}
            nodeTypes={tiposNodo}
            nodesDraggable={false}
            nodesConnectable={false}
            fitView
            minZoom={0.05}
            onNodeClick={(_, n) => n.type === "pieza" && setElegido(n.id)}
            onPaneClick={() => setElegido(null)}
          >
            <Background />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeClassName={(n) => (n.type === "pieza" ? `mini-${(n.data as DatosPieza).nodo.estado}` : "mini-carril")} />
          </ReactFlow>
        </section>
        {nodoElegido && (
          <aside className="detalle">
            <button className="cerrar" onClick={() => setElegido(null)}>
              ×
            </button>
            <h2>{nodoElegido.nombre}</h2>
            <p className={`chip estado-${nodoElegido.estado}`}>{NOMBRE_ESTADO[nodoElegido.estado]}</p>
            <dl>
              {(["id", "capa", "tipo", "fase", "riesgo", "ejecuta", "identidad", "donde", "dueno"] as const).map((k) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd>{String(nodoElegido[k])}</dd>
                </div>
              ))}
              {nodoElegido.issue_url && (
                <div>
                  <dt>issue</dt>
                  <dd>
                    <a href={nodoElegido.issue_url} target="_blank" rel="noreferrer">
                      #{nodoElegido.issue}
                    </a>
                  </dd>
                </div>
              )}
              {(nodoElegido.mejoras ?? []).length > 0 && (
                <div>
                  <dt>mejoras</dt>
                  <dd>{nodoElegido.mejoras!.map((x) => `#${x}`).join(", ")}</dd>
                </div>
              )}
              {nodoElegido.enlaces?.repo && (
                <div>
                  <dt>repo</dt>
                  <dd>{nodoElegido.enlaces.repo}</dd>
                </div>
              )}
              {(nodoElegido.cubre ?? []).length > 0 && (
                <div>
                  <dt>cubre</dt>
                  <dd>
                    {nodoElegido.cubre!.map((c) => (
                      <div key={c}>{c}</div>
                    ))}
                  </dd>
                </div>
              )}
            </dl>
            <h3>Llamadas</h3>
            <ul className="llamadas">
              {mapa.aristas
                .filter((a) => a.de === nodoElegido.id || a.a === nodoElegido.id)
                .map((a, i) => {
                  const otro = a.de === nodoElegido.id ? a.a : a.de;
                  return (
                    <li key={i}>
                      {a.de === nodoElegido.id ? "→" : "←"} <button onClick={() => setElegido(otro)}>{otro}</button> ({a.tipo}: {a.protocolo})
                    </li>
                  );
                })}
            </ul>
            <button onClick={() => poner({ aislar: new Set([...filtros.aislar, nodoElegido.id]) })}>Añadir al aislamiento</button>{" "}
            <button onClick={() => poner({ aislar: new Set([nodoElegido.id]) })}>Aislar solo esta</button>
          </aside>
        )}
      </main>
    </div>
  );
}
