"""Servicio del Atlas: sirve la web y el mapa en /api/mapa.

En la v1 refresca el mapa cada ATLAS_INTERVALO segundos (300 por defecto). En la v2 este mismo
servicio suma el recolector de eventos (POST /evento, GET /flujo por SSE y GET /estado).

Variables de entorno:
    ATLAS_REPO          dueno/nombre del repo de datos (manifiesto e issues).
    ATLAS_MANIFIESTO    ruta del manifiesto dentro de ese repo.
    ATLAS_TOKEN_FILE    archivo con el token de solo lectura (secreto de Compose).
    ATLAS_INTERVALO     segundos entre lecturas (300).
    ATLAS_WEB           carpeta de la web construida (/app/web).
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .fuente import leer_token, obtener_mapa

log = logging.getLogger("atlas")
SIN_CACHE = {"Cache-Control": "no-store"}


def crear_app(obtener: Callable[[], dict], intervalo: float = 300, dir_web: str | Path | None = None) -> Starlette:
    estado: dict = {"mapa": None, "error": None}

    async def refrescar() -> None:
        try:
            estado["mapa"] = await asyncio.to_thread(obtener)
            estado["error"] = None
            log.info("mapa refrescado: %s nodos", len(estado["mapa"]["nodos"]))
        except Exception as e:  # el servicio sigue sirviendo el ultimo mapa bueno
            estado["error"] = f"{type(e).__name__}: {e}"
            log.warning("no se pudo refrescar el mapa: %s", estado["error"])

    async def bucle() -> None:
        while True:
            await asyncio.sleep(intervalo)
            await refrescar()

    @asynccontextmanager
    async def lifespan(app):
        await refrescar()
        tarea = asyncio.create_task(bucle())
        try:
            yield
        finally:
            tarea.cancel()

    async def mapa(request: Request) -> JSONResponse:
        if estado["mapa"] is None:
            return JSONResponse({"error": estado["error"] or "cargando"}, status_code=503, headers=SIN_CACHE)
        return JSONResponse({**estado["mapa"], "error": estado["error"]}, headers=SIN_CACHE)

    async def salud(request: Request) -> JSONResponse:
        hay = estado["mapa"] is not None
        cuerpo = {"ok": hay, "generado_en": estado["mapa"]["generado_en"] if hay else None, "error": estado["error"]}
        return JSONResponse(cuerpo, status_code=200 if hay else 503, headers=SIN_CACHE)

    rutas = [Route("/api/mapa", mapa), Route("/salud", salud)]
    if dir_web and Path(dir_web).is_dir():
        rutas.append(Mount("/", StaticFiles(directory=str(dir_web), html=True)))
    return Starlette(routes=rutas, lifespan=lifespan)


def crear_desde_entorno() -> Starlette:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    repo = os.environ["ATLAS_REPO"]
    ruta = os.environ["ATLAS_MANIFIESTO"]
    archivo_token = os.environ.get("ATLAS_TOKEN_FILE", "/run/secrets/github_token")
    intervalo = float(os.environ.get("ATLAS_INTERVALO", "300"))
    dir_web = os.environ.get("ATLAS_WEB", "/app/web")

    def obtener() -> dict:
        # El token se lee en cada vuelta: rotarlo no exige reiniciar.
        return obtener_mapa(repo, ruta, leer_token(archivo_token))

    return crear_app(obtener, intervalo, dir_web)
