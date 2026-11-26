from atlas.piezas import piezas, piezas_locales

COMPOSE = "services:\n  web:\n    image: x\n  worker:\n    image: y\n"


def test_descubre_cada_tipo_de_pieza():
    rutas = [
        ".github/workflows/ci.yml",
        ".github/workflows/nocturno.yaml",
        "deploy/compose.yaml",
        "docker-compose.yml",
        "n8n/flujo.json",
        "deploy/copia.service",
        "deploy/copia.timer",
        "README.md",
        "src/app.py",
        ".github/dependabot.yml",
    ]
    leidas = []

    def leer(ruta):
        leidas.append(ruta)
        return COMPOSE

    encontradas = piezas("d/r", rutas, leer)
    assert encontradas == {
        "d/r:.github/workflows/ci.yml",
        "d/r:.github/workflows/nocturno.yaml",
        "d/r:deploy/compose.yaml#web",
        "d/r:deploy/compose.yaml#worker",
        "d/r:docker-compose.yml#web",
        "d/r:docker-compose.yml#worker",
        "d/r:n8n/flujo.json",
        "d/r:deploy/copia.service",
        "d/r:deploy/copia.timer",
    }
    assert sorted(leidas) == ["deploy/compose.yaml", "docker-compose.yml"]


def test_un_workflow_que_se_llama_compose_es_workflow():
    assert piezas("d/r", [".github/workflows/compose-check.yml"], lambda r: COMPOSE) == {"d/r:.github/workflows/compose-check.yml"}


def test_compose_sin_servicios_cuenta_entero():
    assert piezas("d/r", ["compose.yaml"], lambda r: "volumes: {}\n") == {"d/r:compose.yaml"}


def test_piezas_locales_ignora_git_y_node_modules(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    (tmp_path / "node_modules" / "x" / "n8n").mkdir(parents=True)
    (tmp_path / "node_modules" / "x" / "n8n" / "f.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".git" / "n8n").mkdir(parents=True)
    (tmp_path / ".git" / "n8n" / "g.json").write_text("{}", encoding="utf-8")
    assert piezas_locales("d/r", tmp_path) == {"d/r:.github/workflows/ci.yml"}
