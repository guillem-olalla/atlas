"""Genera el catalogo de agentes (markdown) desde el manifiesto.

Entran los nodos de tipo agente y los que gastan modelo (`ejecuta: modelo` o `mixto`).
"""
from __future__ import annotations


def _estado(n: dict, url_issues: str) -> str:
    if "issue" in n:
        return f"según [#{n['issue']}]({url_issues}{n['issue']})"
    return "hecho" if n["existe"] else "pendiente"


def generar(m: dict, url_issues: str, origen: str) -> str:
    capas = {c["id"]: c["nombre"] for c in m["capas"]}
    filas = [n for n in m["nodos"] if n["tipo"] == "agente" or n["ejecuta"] in ("modelo", "mixto")]
    filas.sort(key=lambda n: (n["fase"], n["capa"], n["id"]))
    lineas = [
        "# Catálogo de agentes",
        "",
        f"> **Generado desde `{origen}`. No se edita a mano.** Lo regenera el CI en cada cambio del manifiesto.",
        "",
        f"Manifiesto versión {m['version']}, actualizado el {m['actualizado']}. Entran los nodos de tipo agente y los que"
        " gastan modelo (`ejecuta: modelo` o `mixto`). Estado: con issue, el de la issue; sin issue, hecho si ya existe.",
        "",
        "| Id | Nombre | Capa | Fase | Estado | Riesgo | Ejecuta | Identidad | Marcas | Cliente |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n in filas:
        lineas.append(
            f"| `{n['id']}` | {n['nombre']} | {capas[n['capa']]} | {n['fase']} | {_estado(n, url_issues)} | {n['riesgo']} | "
            f"{n['ejecuta']} | {n['identidad']} | {', '.join(n.get('marcas', [])) or '-'} | {n.get('cliente', '-')} |"
        )
    lineas += ["", f"{len(filas)} piezas. Los nodos marcados `personal` son del dueño del harness y no son de clientes."]
    return "\n".join(lineas) + "\n"
