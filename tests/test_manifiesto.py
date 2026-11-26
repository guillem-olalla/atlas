from conftest import issue

from atlas.manifiesto import comparar, normalizar_issues, validar


def test_el_ejemplo_es_valido(m, issues):
    assert validar(m, issues) == []


def test_id_repetido(m):
    m["nodos"].append(dict(m["nodos"][0]))
    assert "id repetido: persona-a" in validar(m)


def test_clave_desconocida_por_coma_sin_comillas(m):
    m["nodos"][0]["identidad"] = "cuenta"
    m["nodos"][0][" propia"] = None
    assert "persona-a: clave desconocida ' propia'" in validar(m)


def test_falta_campo_obligatorio(m):
    del m["nodos"][0]["riesgo"]
    errores = validar(m)
    assert "persona-a: falta riesgo" in errores


def test_capa_tipo_fase_riesgo_y_ejecuta_invalidos(m):
    n = m["nodos"][0]
    n.update(capa="nube", tipo="robot", fase="F9", riesgo="extremo", ejecuta="magia")
    errores = validar(m)
    for esperado in ("capa nube", "tipo robot", "fase F9", "riesgo extremo", "ejecuta magia"):
        assert f"persona-a: {esperado}" in errores


def test_arista_a_nodo_que_no_existe(m):
    m["aristas"].append({"de": "persona-a", "a": "fantasma", "tipo": "lee", "protocolo": "x"})
    assert "arista persona-a->fantasma: a no existe" in validar(m)


def test_arista_con_tipo_invalido_y_clave_desconocida(m):
    m["aristas"].append({"de": "persona-a", "a": "repo-app", "tipo": "teletransporta", "protocolo": "x", "extra": 1})
    errores = validar(m)
    assert "arista persona-a->repo-app: tipo teletransporta" in errores
    assert "arista persona-a->repo-app: clave desconocida 'extra'" in errores


def test_falta_una_seccion():
    assert validar({"nodos": []})[0].startswith("falta la seccion")


def test_cubre_mal_formado(m):
    m["nodos"][1]["cubre"] = ["sin-dos-puntos"]
    assert any("no tiene la forma repo:ruta" in e for e in validar(m))


def test_cubre_a_repo_fuera_del_manifiesto(m):
    m["nodos"][1]["cubre"] = ["otro/repo:.github/workflows/x.yml"]
    assert any("apunta a un repo que ningun nodo enlaza" in e for e in validar(m))


def test_cubre_repetido_en_dos_nodos(m):
    m["nodos"][2]["cubre"] = ["ejemplo/app:.github/workflows/ci.yml"]
    assert "repo-infra: cubre 'ejemplo/app:.github/workflows/ci.yml' ya lo declara repo-app" in validar(m)


def test_issue_sin_nodo_falla(m, issues):
    issues.append(issue(9))
    assert any(e.startswith("issue #9 sin nodo") for e in validar(m, issues))


def test_issue_sin_nodo_con_fuera_del_camino_critico_pasa(m, issues):
    issues.append(issue(9, etiquetas=["fuera-del-camino-critico"]))
    assert validar(m, issues) == []


def test_nodo_que_cita_una_issue_que_no_existe(m, issues):
    issues = [i for i in issues if i["number"] != 3]
    assert "tarea-z: la issue #3 no existe" in validar(m, issues)


def test_mejora_cuenta_como_enlace(m, issues):
    # La #2 solo aparece en mejoras de servicio-y.
    assert not any("#2" in e for e in validar(m, issues))


def test_normalizar_issues_de_rest_y_de_gh():
    rest = [
        {"number": 1, "state": "open", "labels": [{"name": "en-curso"}]},
        {"number": 2, "state": "closed", "labels": []},
        {"number": 3, "state": "open", "labels": [], "pull_request": {}},
    ]
    gh = [{"number": 4, "state": "OPEN", "labels": [{"name": "bloqueado"}]}, {"number": 5, "state": "CLOSED", "labels": []}]
    salida = normalizar_issues(rest + gh)
    assert [i["number"] for i in salida] == [1, 2, 4, 5]
    assert [i["cerrada"] for i in salida] == [False, True, False, True]
    assert salida[0]["etiquetas"] == {"en-curso"}


def test_pr_de_prueba_que_anade_un_workflow_sin_nodo_falla(m):
    encontradas = {"ejemplo/app:.github/workflows/ci.yml", "ejemplo/app:deploy/compose.yaml#agente", "ejemplo/app:.github/workflows/nuevo.yml"}
    errores = validar(m, locales={"ejemplo/app": encontradas})
    assert errores == ["pieza sin nodo: ejemplo/app:.github/workflows/nuevo.yml (declarala en el cubre de su nodo)"]


def test_cubre_que_ya_no_existe_en_el_repo(m):
    errores = validar(m, locales={"ejemplo/app": {"ejemplo/app:.github/workflows/ci.yml"}})
    assert errores == ["cubre sin pieza: ejemplo/app:deploy/compose.yaml#agente (no existe en el repo)"]


def test_comparar():
    m = {"nodos": [{"id": "a", "cubre": ["r/x:a.yml", "r/y:b.yml"]}]}
    assert comparar(m, "r/x", {"r/x:a.yml", "r/x:c.yml"}) == ({"r/x:c.yml"}, set())
