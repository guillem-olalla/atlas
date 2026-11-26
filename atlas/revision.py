"""Revision nocturna de desajustes entre el manifiesto y los repos.

Para cada repo del manifiesto compara sus piezas desplegables con los `cubre` de los nodos.
Ademas busca repos publicos del dueno sin nodo y, en el repo publico del Atlas, nombres que no
pueden salir: repos privados, clientes e IPs que aparecen en el manifiesto.

El cliente es cualquier objeto con json(url), crudo(url) y paginar(url) (ver github.Cliente).
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .github import ErrorGitHub
from .manifiesto import comparar, repos
from .piezas import es_candidata, piezas

PATRON_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
EXTENSIONES_TEXTO = (".md", ".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".toml", ".txt", ".html", ".css", ".sh", ".cfg", ".ini", "Dockerfile", ".example", ".ejemplo")
MAX_BYTES = 1_000_000


def _leer(cliente, repo: str, rama: str):
    return lambda ruta: cliente.crudo(f"/repos/{repo}/contents/{quote(ruta)}?ref={quote(rama)}")


def revisar_repo(cliente, m: dict, repo: str) -> tuple[list[str], dict | None]:
    """Desajustes de un repo y su info (o None si no se pudo leer)."""
    try:
        info = cliente.json(f"/repos/{repo}")
    except ErrorGitHub as e:
        return [f"`{repo}`: el token de revision no lo puede leer ({e.estado})."], None
    rama = info["default_branch"]
    arbol = cliente.json(f"/repos/{repo}/git/trees/{quote(rama)}?recursive=1")
    desajustes = []
    if arbol.get("truncated"):
        desajustes.append(f"`{repo}`: el arbol llega truncado; la revision puede no ver todas las piezas.")
    rutas = [t["path"] for t in arbol.get("tree", []) if t.get("type") == "blob" and es_candidata(t["path"])]
    encontradas = piezas(repo, rutas, _leer(cliente, repo, rama))
    sin_nodo, sin_pieza = comparar(m, repo, encontradas)
    desajustes += [f"Pieza sin nodo: `{p}`. Declárala en el `cubre` de su nodo." for p in sorted(sin_nodo)]
    desajustes += [f"`cubre` sin pieza: `{p}` no existe en `{repo}`." for p in sorted(sin_pieza)]
    return desajustes, info


def terminos_privados(m: dict, infos: dict[str, dict], repo_datos: str | None) -> set[str]:
    """Lo que no puede aparecer en el repo publico: repos privados, clientes e IPs del manifiesto."""
    terminos: set[str] = set()
    for repo, info in infos.items():
        if info and info.get("private"):
            terminos |= {repo, repo.split("/", 1)[1]}
    if repo_datos:
        terminos |= {repo_datos, repo_datos.split("/", 1)[1]}
    for n in m["nodos"]:
        if n.get("cliente"):
            terminos.add(str(n["cliente"]))
        terminos |= set(PATRON_IPV4.findall(str(n.get("donde", ""))))
        terminos |= set(PATRON_IPV4.findall(str(n.get("identidad", ""))))
    return {t for t in terminos if len(t) >= 4}


def revisar_privacidad(cliente, repo_publico: str, terminos: set[str]) -> list[str]:
    info = cliente.json(f"/repos/{repo_publico}")
    rama = info["default_branch"]
    arbol = cliente.json(f"/repos/{repo_publico}/git/trees/{quote(rama)}?recursive=1")
    hallazgos = []
    for t in arbol.get("tree", []):
        ruta = t.get("path", "")
        if t.get("type") != "blob" or t.get("size", 0) > MAX_BYTES or not ruta.endswith(EXTENSIONES_TEXTO):
            continue
        texto = cliente.crudo(f"/repos/{repo_publico}/contents/{quote(ruta)}?ref={quote(rama)}").lower()
        for termino in sorted(terminos):
            if termino.lower() in texto:
                hallazgos.append(f"Privacidad: `{repo_publico}:{ruta}` contiene un nombre privado del manifiesto (`{termino}`).")
    return hallazgos


def revisar(cliente, m: dict, repo_publico: str | None = None, repo_datos: str | None = None) -> list[str]:
    desajustes: list[str] = []
    infos: dict[str, dict] = {}
    repos_m = sorted(repos(m))
    for repo in repos_m:
        propios, info = revisar_repo(cliente, m, repo)
        desajustes += propios
        infos[repo] = info
    for dueno in sorted({r.split("/", 1)[0] for r in repos_m}):
        for r in cliente.paginar(f"/users/{quote(dueno)}/repos?type=owner&per_page=100"):
            if not r.get("fork") and not r.get("archived") and not r.get("private") and r["full_name"] not in repos_m:
                desajustes.append(f"Repo público sin nodo: `{r['full_name']}`.")
    if repo_publico:
        desajustes += revisar_privacidad(cliente, repo_publico, terminos_privados(m, infos, repo_datos))
    return desajustes


def informe(desajustes: list[str], fecha: str) -> str:
    if not desajustes:
        return f"Revisión del {fecha}: sin desajustes.\n"
    lineas = [
        f"Revisión nocturna del mapa, {fecha}: {len(desajustes)} desajustes.",
        "",
        "Cada línea es algo que el manifiesto no refleja. Se arregla en el manifiesto (nodo, `cubre`) o en el repo.",
        "",
    ]
    lineas += [f"- {d}" for d in desajustes]
    return "\n".join(lineas) + "\n"
