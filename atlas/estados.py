"""Estado de cada nodo, sacado de las issues del repo de datos.

Regla (decidida el 2026-11-26): cerrada = hecho; abierta con `bloqueado` = bloqueado; abierta con
`en-curso` = en curso; el resto de abiertas = pendiente. Si lleva las dos etiquetas, gana
`bloqueado`. Un nodo sin issue esta hecho si `existe` es true y pendiente si no. Un nodo cuya
issue no aparece queda `desconocido`, para que se vea y no se pinte como pendiente.
"""
from __future__ import annotations

ETIQUETA_BLOQUEADO = "bloqueado"
ETIQUETA_EN_CURSO = "en-curso"
ESTADOS = ("hecho", "en_curso", "bloqueado", "pendiente", "desconocido")


def estado_issue(issue: dict) -> str:
    if issue["cerrada"]:
        return "hecho"
    if ETIQUETA_BLOQUEADO in issue["etiquetas"]:
        return "bloqueado"
    if ETIQUETA_EN_CURSO in issue["etiquetas"]:
        return "en_curso"
    return "pendiente"


def estado_nodo(nodo: dict, por_numero: dict[int, dict]) -> str:
    if isinstance(nodo.get("issue"), int):
        issue = por_numero.get(nodo["issue"])
        return estado_issue(issue) if issue else "desconocido"
    return "hecho" if nodo.get("existe") else "pendiente"
