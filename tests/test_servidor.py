import time

from starlette.testclient import TestClient

from atlas.servidor import crear_app

MAPA = {"nodos": [{"id": "a", "estado": "hecho"}], "aristas": [], "generado_en": "2026-01-01T00:00:00+00:00"}


def test_sirve_el_mapa_y_la_salud():
    with TestClient(crear_app(lambda: MAPA, intervalo=3600)) as c:
        r = c.get("/api/mapa")
        assert r.status_code == 200
        assert r.json()["nodos"] == MAPA["nodos"]
        assert r.json()["error"] is None
        assert r.headers["cache-control"] == "no-store"
        assert c.get("/salud").json() == {"ok": True, "generado_en": MAPA["generado_en"], "error": None}


def test_sin_datos_responde_503_con_el_error():
    def falla():
        raise RuntimeError("GitHub caido")

    with TestClient(crear_app(falla, intervalo=3600)) as c:
        r = c.get("/api/mapa")
        assert r.status_code == 503
        assert r.json() == {"error": "RuntimeError: GitHub caido"}
        assert c.get("/salud").status_code == 503


def test_si_falla_despues_sigue_sirviendo_el_ultimo_mapa():
    llamadas = []

    def obtener():
        llamadas.append(1)
        if len(llamadas) > 1:
            raise RuntimeError("sin red")
        return MAPA

    app = crear_app(obtener, intervalo=0.01)
    with TestClient(app) as c:
        for _ in range(200):
            if len(llamadas) > 1 and c.get("/api/mapa").json().get("error"):
                break
            time.sleep(0.01)  # el bucle del servicio corre en el hilo del portal de TestClient
        r = c.get("/api/mapa")
        assert r.status_code == 200
        assert r.json()["nodos"] == MAPA["nodos"]
        assert r.json()["error"] == "RuntimeError: sin red"


def test_sirve_la_web(tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>Atlas</title>", encoding="utf-8")
    with TestClient(crear_app(lambda: MAPA, intervalo=3600, dir_web=tmp_path)) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert "<title>Atlas</title>" in r.text
        assert c.get("/api/mapa").status_code == 200
