"""Junta el manifiesto y los estados de las issues en el mapa que sirve la web.

Todo se lee en tiempo de ejecucion con un token de solo lectura: ni el manifiesto real ni los
estados pasan por el repo, el CI o la imagen.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import yaml

from .estados import estado_nodo
from .github import Cliente, caducidad_token
from .manifiesto import normalizar_issues, validar


def leer_token(ruta: str | Path) -> str:
    token = Path(ruta).read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError(f"el archivo del token esta vacio: {ruta}")
    return token


def construir_mapa(m: dict, issues: list[dict], url_issues: str, token_caduca: datetime | None, generado_en: datetime) -> dict:
    por_numero = {i["number"]: i for i in issues}
    nodos = []
    for n in m["nodos"]:
        nodo = dict(n)
        nodo["estado"] = estado_nodo(n, por_numero)
        if isinstance(n.get("issue"), int):
            nodo["issue_url"] = f"{url_issues}{n['issue']}"
        nodos.append(nodo)
    return {
        "version": m.get("version"),
        "actualizado": str(m.get("actualizado", "")),
        "capas": sorted(m["capas"], key=lambda c: c["orden"]),
        "fases": m["fases"],
        "nodos": nodos,
        "aristas": m["aristas"],
        "errores_manifiesto": validar(m),
        "generado_en": generado_en.astimezone(timezone.utc).isoformat(),
        "token_caduca": token_caduca.isoformat() if token_caduca else None,
    }


def obtener_mapa(repo: str, ruta_manifiesto: str, token: str) -> dict:
    cliente = Cliente(token)
    r = cliente.pedir(f"/repos/{repo}/contents/{quote(ruta_manifiesto)}", aceptar="application/vnd.github.raw+json")
    m = yaml.safe_load(r.datos)
    issues = normalizar_issues(cliente.paginar(f"/repos/{repo}/issues?state=all&per_page=100"))
    return construir_mapa(m, issues, f"https://github.com/{repo}/issues/", caducidad_token(r.cabeceras), datetime.now(timezone.utc))
