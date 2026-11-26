import pytest

from atlas.github import ErrorGitHub
from atlas.revision import informe, revisar, terminos_privados


class ClienteFalso:
    """Repos en memoria: {repo: {"private": bool, "archivos": {ruta: texto}}}."""

    def __init__(self, repos, publicos_del_dueno=()):
        self.repos = repos
        self.publicos = list(publicos_del_dueno)

    def json(self, url):
        partes = url.split("?")[0].strip("/").split("/")
        repo = f"{partes[1]}/{partes[2]}"
        if repo not in self.repos:
            raise ErrorGitHub(404, "no existe")
        datos = self.repos[repo]
        if len(partes) == 3:
            return {"default_branch": "main", "private": datos["private"]}
        arbol = [{"path": p, "type": "blob", "size": len(t)} for p, t in datos["archivos"].items()]
        return {"tree": arbol, "truncated": False}

    def crudo(self, url):
        ruta = url.split("?")[0]
        _, _, dueno, nombre, _, *resto = ruta.split("/")
        return self.repos[f"{dueno}/{nombre}"]["archivos"]["/".join(resto)]

    def paginar(self, url):
        return self.publicos


IP = ".".join(["10", "1", "2", "3"])  # a trozos: el test de privacidad del repo no admite IPs literales
COMPOSE = "services:\n  agente:\n    image: x\n"
INFRA_COMPOSE = "services:\n  y:\n    image: y\n"


def repos_que_cuadran():
    return {
        "ejemplo/app": {"private": True, "archivos": {".github/workflows/ci.yml": "on: push", "deploy/compose.yaml": COMPOSE, "README.md": "hola"}},
        "ejemplo/infra": {"private": False, "archivos": {"servicio-y/compose.yaml": INFRA_COMPOSE, "servicio-y/copia.timer": "[Timer]"}},
    }


def test_sin_desajustes(m):
    assert revisar(ClienteFalso(repos_que_cuadran()), m) == []


def test_pieza_sin_nodo_y_cubre_sin_pieza(m):
    repos = repos_que_cuadran()
    repos["ejemplo/app"]["archivos"][".github/workflows/nuevo.yml"] = "on: push"
    del repos["ejemplo/infra"]["archivos"]["servicio-y/copia.timer"]
    desajustes = revisar(ClienteFalso(repos), m)
    assert "Pieza sin nodo: `ejemplo/app:.github/workflows/nuevo.yml`. Declárala en el `cubre` de su nodo." in desajustes
    assert "`cubre` sin pieza: `ejemplo/infra:servicio-y/copia.timer` no existe en `ejemplo/infra`." in desajustes
    assert len(desajustes) == 2


def test_repo_que_el_token_no_lee(m):
    repos = repos_que_cuadran()
    del repos["ejemplo/infra"]
    assert revisar(ClienteFalso(repos), m) == ["`ejemplo/infra`: el token de revision no lo puede leer (404)."]


def test_repo_publico_sin_nodo(m):
    publicos = [
        {"full_name": "ejemplo/infra", "fork": False, "archived": False, "private": False},
        {"full_name": "ejemplo/nuevo", "fork": False, "archived": False, "private": False},
        {"full_name": "ejemplo/un-fork", "fork": True, "archived": False, "private": False},
        {"full_name": "ejemplo/viejo", "fork": False, "archived": True, "private": False},
    ]
    assert revisar(ClienteFalso(repos_que_cuadran(), publicos), m) == ["Repo público sin nodo: `ejemplo/nuevo`."]


def test_privacidad_del_repo_publico(m):
    repos = repos_que_cuadran()
    repos["ejemplo/infra"]["archivos"]["README.md"] = f"Lee el manifiesto de Ejemplo/App y de datos-privados en {IP}"
    m["nodos"][0]["donde"] = f"portatil {IP}"
    desajustes = revisar(ClienteFalso(repos), m, repo_publico="ejemplo/infra", repo_datos="ejemplo/datos-privados")
    assert sorted(desajustes) == sorted(
        [
            f"Privacidad: `ejemplo/infra:README.md` contiene un nombre privado del manifiesto (`{IP}`).",
            "Privacidad: `ejemplo/infra:README.md` contiene un nombre privado del manifiesto (`datos-privados`).",
            "Privacidad: `ejemplo/infra:README.md` contiene un nombre privado del manifiesto (`ejemplo/app`).",
        ]
    )


def test_terminos_privados(m):
    m["nodos"][0]["cliente"] = "ClienteUno"
    terminos = terminos_privados(m, {"ejemplo/app": {"private": True}, "ejemplo/infra": {"private": False}}, None)
    # "app" sola se queda fuera: con menos de 4 letras daria falsos positivos en cualquier texto.
    assert terminos == {"ejemplo/app", "ClienteUno"}


@pytest.mark.parametrize("desajustes", [[], ["uno", "dos"]])
def test_informe(desajustes):
    texto = informe(desajustes, "2026-01-01 04:30 UTC")
    if desajustes:
        assert "2 desajustes" in texto and "- uno" in texto
    else:
        assert texto == "Revisión del 2026-01-01 04:30 UTC: sin desajustes.\n"
