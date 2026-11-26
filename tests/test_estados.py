import pytest
from conftest import issue

from atlas.estados import estado_issue, estado_nodo


@pytest.mark.parametrize(
    ("cerrada", "etiquetas", "esperado"),
    [
        (True, [], "hecho"),
        (True, ["bloqueado", "en-curso"], "hecho"),
        (False, ["en-curso"], "en_curso"),
        (False, ["bloqueado"], "bloqueado"),
        (False, ["bloqueado", "en-curso"], "bloqueado"),
        (False, ["riesgo:alto"], "pendiente"),
        (False, [], "pendiente"),
    ],
)
def test_estado_de_una_issue(cerrada, etiquetas, esperado):
    assert estado_issue(issue(1, cerrada, etiquetas)) == esperado


def test_nodo_con_issue_toma_su_estado():
    assert estado_nodo({"issue": 7, "existe": True}, {7: issue(7)}) == "pendiente"


def test_nodo_con_issue_que_no_aparece_es_desconocido():
    assert estado_nodo({"issue": 7, "existe": True}, {}) == "desconocido"


def test_nodo_sin_issue_sale_de_existe():
    assert estado_nodo({"existe": True}, {}) == "hecho"
    assert estado_nodo({"existe": False}, {}) == "pendiente"


def test_las_mejoras_no_cambian_el_estado():
    assert estado_nodo({"existe": True, "mejoras": [7]}, {7: issue(7, etiquetas=["bloqueado"])}) == "hecho"
