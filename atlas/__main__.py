"""Linea de comandos del Atlas.

    python -m atlas validar MANIFIESTO [--issues issues.json] [--local REPO=CARPETA ...]
    python -m atlas catalogo MANIFIESTO SALIDA --url-issues URL [--origen TEXTO]
    python -m atlas revision MANIFIESTO --salida INFORME [--publico REPO] [--datos REPO]

`revision` lee el token del archivo que diga ATLAS_TOKEN_REVISION_FILE o de la variable
ATLAS_TOKEN_REVISION. Sale con 0 aunque haya desajustes (el informe dice cuantos) y escribe
`hay_desajustes=true|false` en GITHUB_OUTPUT si existe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import catalogo, manifiesto, revision
from .fuente import leer_token
from .github import Cliente
from .piezas import piezas_locales


def _validar(args) -> int:
    m = manifiesto.cargar(args.manifiesto)
    issues = None
    if args.issues:
        issues = manifiesto.normalizar_issues(json.loads(Path(args.issues).read_text(encoding="utf-8")))
    locales = {}
    for par in args.local or []:
        repo, _, carpeta = par.partition("=")
        locales[repo] = piezas_locales(repo, carpeta)
    errores = manifiesto.validar(m, issues, locales)
    if isinstance(m, dict) and isinstance(m.get("nodos"), list) and isinstance(m.get("aristas"), list) and not errores:
        print("\n".join(manifiesto.resumen(m)))
    if issues is not None:
        print(f"issues comprobadas {len(issues)}")
    for repo, encontradas in locales.items():
        print(f"piezas locales de {repo}: {len(encontradas)}")
    print("\n".join(errores) or "OK")
    return 1 if errores else 0


def _catalogo(args) -> int:
    m = manifiesto.cargar(args.manifiesto)
    texto = catalogo.generar(m, args.url_issues, args.origen or args.manifiesto)
    Path(args.salida).write_text(texto, encoding="utf-8", newline="\n")
    print("filas", texto.count("\n| `"))
    return 0


def _revision(args) -> int:
    ruta_token = os.environ.get("ATLAS_TOKEN_REVISION_FILE")
    token = leer_token(ruta_token) if ruta_token else os.environ.get("ATLAS_TOKEN_REVISION", "").strip()
    if not token:
        print("falta el token de revision (ATLAS_TOKEN_REVISION)", file=sys.stderr)
        return 2
    m = manifiesto.cargar(args.manifiesto)
    desajustes = revision.revisar(Cliente(token), m, args.publico, args.datos)
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    Path(args.salida).write_text(revision.informe(desajustes, fecha), encoding="utf-8")
    print(f"desajustes {len(desajustes)}")
    salida_gh = os.environ.get("GITHUB_OUTPUT")
    if salida_gh:
        with open(salida_gh, "a", encoding="utf-8") as f:
            f.write(f"hay_desajustes={'true' if desajustes else 'false'}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="atlas")
    sub = p.add_subparsers(dest="orden", required=True)
    v = sub.add_parser("validar")
    v.add_argument("manifiesto")
    v.add_argument("--issues")
    v.add_argument("--local", action="append", help="REPO=CARPETA, repetible")
    v.set_defaults(f=_validar)
    c = sub.add_parser("catalogo")
    c.add_argument("manifiesto")
    c.add_argument("salida")
    c.add_argument("--url-issues", required=True)
    c.add_argument("--origen")
    c.set_defaults(f=_catalogo)
    r = sub.add_parser("revision")
    r.add_argument("manifiesto")
    r.add_argument("--salida", required=True)
    r.add_argument("--publico")
    r.add_argument("--datos")
    r.set_defaults(f=_revision)
    args = p.parse_args(argv)
    return args.f(args)


if __name__ == "__main__":
    sys.exit(main())
