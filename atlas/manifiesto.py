"""Carga y valida el manifiesto del harness.

El manifiesto es la unica fuente del mapa: nodos (piezas) y aristas (llamadas). Este modulo
comprueba su forma, que cada issue del repo de datos tenga su nodo y, si se le da una copia
local de un repo, que cada pieza desplegable de ese repo este declarada en algun `cubre`.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import yaml

OBLIGATORIOS = ("id", "nombre", "capa", "tipo", "fase", "dueno", "riesgo", "ejecuta", "identidad", "donde", "existe")
OPCIONALES = ("marcas", "cliente", "issue", "mejoras", "enlaces", "cubre")
EJECUTA = ("modelo", "script", "humano", "mixto")
CAMPOS_ARISTA = ("de", "a", "tipo", "protocolo")
CAMPOS_ENLACES = ("repo", "doc")
SECCIONES = ("capas", "tipos_nodo", "tipos_arista", "fases", "riesgos", "marcas", "nodos", "aristas")
ETIQUETA_FUERA = "fuera-del-camino-critico"

# repo:ruta o repo:ruta#servicio. El repo es dueno/nombre, como en enlaces.repo.
PATRON_CUBRE = re.compile(r"^(?P<repo>[\w.-]+/[\w.-]+):(?P<ruta>[^#\s]+)(?:#(?P<servicio>[\w.-]+))?$")


def cargar(ruta: str | Path) -> dict:
    return yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))


def repos(m: dict) -> set[str]:
    """Repos que aparecen en el manifiesto (enlaces.repo de algun nodo)."""
    return {n["enlaces"]["repo"] for n in m.get("nodos", []) if isinstance(n.get("enlaces"), dict) and n["enlaces"].get("repo")}


def declaradas(m: dict, repo: str) -> set[str]:
    """Entradas de `cubre` de todos los nodos que apuntan a `repo`."""
    return {c for n in m.get("nodos", []) for c in n.get("cubre", []) or [] if isinstance(c, str) and c.split(":", 1)[0] == repo}


def normalizar_issues(crudas: list[dict]) -> list[dict]:
    """Acepta issues de la API REST o de `gh issue list --json number,state,labels`.

    Devuelve [{number, cerrada, etiquetas}] sin pull requests (la API REST las mezcla).
    """
    salida = []
    for i in crudas:
        if "pull_request" in i:
            continue
        etiquetas = {(e["name"] if isinstance(e, dict) else str(e)) for e in i.get("labels", [])}
        salida.append({"number": int(i["number"]), "cerrada": str(i.get("state", "")).lower() == "closed", "etiquetas": etiquetas})
    return salida


def _validar_nodo(n: dict, m: dict, capas: set, repos_m: set, vistos_cubre: dict, errores: list) -> None:
    nid = n.get("id")
    for campo in sorted(set(n) - set(OBLIGATORIOS) - set(OPCIONALES)):
        # Una coma sin comillas en flujo YAML parte el valor en una clave suelta.
        errores.append(f"{nid}: clave desconocida {campo!r}")
    for campo in OBLIGATORIOS:
        if campo not in n:
            errores.append(f"{nid}: falta {campo}")
    if n.get("capa") not in capas:
        errores.append(f"{nid}: capa {n.get('capa')}")
    if n.get("tipo") not in m["tipos_nodo"]:
        errores.append(f"{nid}: tipo {n.get('tipo')}")
    if n.get("fase") not in m["fases"]:
        errores.append(f"{nid}: fase {n.get('fase')}")
    if n.get("riesgo") not in m["riesgos"]:
        errores.append(f"{nid}: riesgo {n.get('riesgo')}")
    if n.get("ejecuta") not in EJECUTA:
        errores.append(f"{nid}: ejecuta {n.get('ejecuta')}")
    if "existe" in n and not isinstance(n["existe"], bool):
        errores.append(f"{nid}: existe tiene que ser true o false")
    for marca in n.get("marcas", []) or []:
        if marca not in m["marcas"]:
            errores.append(f"{nid}: marca {marca}")
    if "issue" in n and (not isinstance(n["issue"], int) or isinstance(n["issue"], bool)):
        errores.append(f"{nid}: issue tiene que ser un numero")
    mejoras = n.get("mejoras", [])
    if not isinstance(mejoras, list) or any(not isinstance(x, int) or isinstance(x, bool) for x in mejoras):
        errores.append(f"{nid}: mejoras tiene que ser una lista de numeros")
    enlaces = n.get("enlaces", {})
    if not isinstance(enlaces, dict):
        errores.append(f"{nid}: enlaces tiene que ser un mapa")
    else:
        for campo in sorted(set(enlaces) - set(CAMPOS_ENLACES)):
            errores.append(f"{nid}: enlace desconocido {campo!r}")
    cubre = n.get("cubre", [])
    if not isinstance(cubre, list):
        errores.append(f"{nid}: cubre tiene que ser una lista")
        return
    for entrada in cubre:
        coincide = PATRON_CUBRE.match(entrada) if isinstance(entrada, str) else None
        if not coincide:
            errores.append(f"{nid}: cubre {entrada!r} no tiene la forma repo:ruta o repo:ruta#servicio")
            continue
        if coincide["repo"] not in repos_m:
            errores.append(f"{nid}: cubre {entrada!r} apunta a un repo que ningun nodo enlaza")
        if entrada in vistos_cubre:
            errores.append(f"{nid}: cubre {entrada!r} ya lo declara {vistos_cubre[entrada]}")
        vistos_cubre.setdefault(entrada, nid)


def validar(m: dict, issues: list[dict] | None = None, locales: dict[str, set[str]] | None = None) -> list[str]:
    """Devuelve la lista de errores; vacia si el manifiesto es valido.

    issues: salida de normalizar_issues. Si se da, cada issue tiene que estar enlazada por algun
        nodo (como `issue` o en `mejoras`) o llevar la etiqueta fuera-del-camino-critico, y cada
        numero que cita un nodo tiene que existir.
    locales: {repo: piezas encontradas en una copia local}. Cada pieza tiene que estar en algun
        `cubre` y cada `cubre` de ese repo tiene que existir.
    """
    if not isinstance(m, dict):
        return ["el manifiesto no es un mapa YAML"]
    faltan = [s for s in SECCIONES if not isinstance(m.get(s), list)]
    if faltan:
        return [f"falta la seccion {s} (o no es una lista)" for s in faltan]

    errores: list[str] = []
    capas = {c.get("id") for c in m["capas"]}
    ids = [n.get("id") for n in m["nodos"]]
    for i, k in Counter(ids).items():
        if k > 1:
            errores.append(f"id repetido: {i}")
    repos_m = repos(m)
    vistos_cubre: dict[str, str] = {}
    for n in m["nodos"]:
        _validar_nodo(n, m, capas, repos_m, vistos_cubre, errores)

    conjunto = set(ids)
    for a in m["aristas"]:
        nombre = f"arista {a.get('de')}->{a.get('a')}"
        for campo in sorted(set(a) - set(CAMPOS_ARISTA)):
            errores.append(f"{nombre}: clave desconocida {campo!r}")
        for extremo in ("de", "a"):
            if a.get(extremo) not in conjunto:
                errores.append(f"{nombre}: {extremo} no existe")
        if a.get("tipo") not in m["tipos_arista"]:
            errores.append(f"{nombre}: tipo {a.get('tipo')}")

    if issues is not None:
        errores += _validar_issues(m, issues)
    for repo, encontradas in (locales or {}).items():
        sin_nodo, sin_pieza = comparar(m, repo, encontradas)
        errores += [f"pieza sin nodo: {p} (declarala en el cubre de su nodo)" for p in sorted(sin_nodo)]
        errores += [f"cubre sin pieza: {p} (no existe en el repo)" for p in sorted(sin_pieza)]
    return errores


def _validar_issues(m: dict, issues: list[dict]) -> list[str]:
    errores = []
    enlazadas = {n["issue"] for n in m["nodos"] if isinstance(n.get("issue"), int)}
    enlazadas |= {x for n in m["nodos"] for x in (n.get("mejoras") or []) if isinstance(x, int)}
    existentes = {i["number"] for i in issues}
    for i in sorted(issues, key=lambda i: i["number"]):
        if i["number"] not in enlazadas and ETIQUETA_FUERA not in i["etiquetas"]:
            errores.append(f"issue #{i['number']} sin nodo: enlazala con issue o mejoras, o ponle la etiqueta {ETIQUETA_FUERA}")
    for n in m["nodos"]:
        citadas = ([n["issue"]] if isinstance(n.get("issue"), int) else []) + [x for x in n.get("mejoras") or [] if isinstance(x, int)]
        for num in citadas:
            if num not in existentes:
                errores.append(f"{n.get('id')}: la issue #{num} no existe")
    return errores


def comparar(m: dict, repo: str, encontradas: set[str]) -> tuple[set[str], set[str]]:
    """(piezas del repo sin nodo, entradas de cubre del repo que no existen)."""
    decl = declaradas(m, repo)
    return set(encontradas) - decl, decl - set(encontradas)


def resumen(m: dict) -> list[str]:
    ids = [n["id"] for n in m["nodos"]]
    con_arista = {a["de"] for a in m["aristas"]} | {a["a"] for a in m["aristas"]}
    return [
        f"nodos {len(ids)} aristas {len(m['aristas'])}",
        f"por capa {dict(Counter(n['capa'] for n in m['nodos']))}",
        f"por fase {dict(sorted(Counter(n['fase'] for n in m['nodos']).items()))}",
        f"existen hoy {sum(1 for n in m['nodos'] if n.get('existe'))} personales "
        f"{sum(1 for n in m['nodos'] if 'personal' in (n.get('marcas') or []))}",
        f"con cubre {sum(1 for n in m['nodos'] if n.get('cubre'))} entradas {sum(len(n.get('cubre') or []) for n in m['nodos'])}",
        f"sin aristas {sorted(set(ids) - con_arista)}",
    ]
