"""Cliente minimo de la API REST de GitHub, solo lectura y solo biblioteca estandar.

El token nunca sale en errores ni en logs: los errores llevan el codigo HTTP y el motivo.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

API = "https://api.github.com"
JSON = "application/vnd.github+json"
RAW = "application/vnd.github.raw+json"
CABECERA_CADUCIDAD = "github-authentication-token-expiration"


class ErrorGitHub(Exception):
    def __init__(self, estado: int, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado


@dataclass
class Respuesta:
    datos: object
    cabeceras: dict[str, str]


class Cliente:
    def __init__(self, token: str, timeout: float = 20.0):
        if not token:
            raise ValueError("token vacio")
        self._token = token
        self._timeout = timeout

    def pedir(self, url: str, aceptar: str = JSON) -> Respuesta:
        if not url.startswith("http"):
            url = API + url
        peticion = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": aceptar,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "atlas",
            },
        )
        try:
            with urllib.request.urlopen(peticion, timeout=self._timeout) as r:
                cuerpo = r.read()
                cabeceras = {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            raise ErrorGitHub(e.code, f"GitHub respondio {e.code} {e.reason} en {url.split('?')[0]}") from None
        except urllib.error.URLError as e:
            raise ErrorGitHub(0, f"sin conexion con GitHub: {e.reason}") from None
        texto = cuerpo.decode("utf-8")
        return Respuesta(json.loads(texto) if aceptar == JSON else texto, cabeceras)

    def json(self, url: str) -> object:
        return self.pedir(url).datos

    def crudo(self, url: str) -> str:
        return self.pedir(url, RAW).datos

    def paginar(self, url: str) -> list:
        salida: list = []
        while url:
            r = self.pedir(url)
            salida += r.datos
            url = siguiente_pagina(r.cabeceras.get("link", ""))
        return salida


def siguiente_pagina(link: str) -> str | None:
    for parte in link.split(","):
        coincide = re.search(r'<([^>]+)>\s*;\s*rel="next"', parte)
        if coincide:
            return coincide.group(1)
    return None


def caducidad_token(cabeceras: dict[str, str]) -> datetime | None:
    """Fecha de caducidad del token que GitHub manda en cada respuesta, si la tiene.

    Formatos vistos: '2027-11-26 10:00:00 UTC' y '2027-11-26 10:00:00 -0700'.
    """
    valor = (cabeceras.get(CABECERA_CADUCIDAD) or "").strip()
    if not valor:
        return None
    if valor.endswith(" UTC"):
        return datetime.strptime(valor[:-4], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    try:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc)
    except ValueError:
        return None
