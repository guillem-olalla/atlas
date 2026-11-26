"""Descubre las piezas desplegables de un repo: lo que tiene que tener nodo en el mapa.

Una pieza es un workflow de GitHub Actions, un servicio de Compose, un flujo de n8n exportado o
una unidad de systemd. Se nombra como en `cubre`: `repo:ruta` o `repo:ruta#servicio`.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import yaml

PATRON_WORKFLOW = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
PATRON_COMPOSE = re.compile(r"(^|/)(docker-)?compose[^/]*\.ya?ml$")
PATRON_N8N = re.compile(r"(^|/)n8n/.+\.json$")
PATRON_SYSTEMD = re.compile(r"\.(service|timer)$")
IGNORAR_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__"}


def es_candidata(ruta: str) -> bool:
    return any(p.search(ruta) for p in (PATRON_WORKFLOW, PATRON_COMPOSE, PATRON_N8N, PATRON_SYSTEMD))


def piezas(repo: str, rutas: Iterable[str], leer: Callable[[str], str]) -> set[str]:
    """rutas: archivos del repo con '/' como separador. leer(ruta) solo se llama para los compose."""
    salida: set[str] = set()
    for ruta in rutas:
        if PATRON_WORKFLOW.search(ruta) or PATRON_N8N.search(ruta) or PATRON_SYSTEMD.search(ruta):
            salida.add(f"{repo}:{ruta}")
        elif PATRON_COMPOSE.search(ruta):
            datos = yaml.safe_load(leer(ruta)) or {}
            servicios = datos.get("services") if isinstance(datos, dict) else None
            if not servicios:
                salida.add(f"{repo}:{ruta}")
            else:
                salida |= {f"{repo}:{ruta}#{s}" for s in servicios}
    return salida


def rutas_locales(raiz: str | Path) -> list[str]:
    raiz = Path(raiz)
    salida = []
    for actual, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in IGNORAR_DIRS]
        for nombre in archivos:
            salida.append((Path(actual) / nombre).relative_to(raiz).as_posix())
    return sorted(salida)


def piezas_locales(repo: str, raiz: str | Path) -> set[str]:
    raiz = Path(raiz)
    return piezas(repo, rutas_locales(raiz), lambda r: (raiz / r).read_text(encoding="utf-8"))
