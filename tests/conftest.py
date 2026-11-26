import copy
from pathlib import Path

import pytest

from atlas.manifiesto import cargar

DATOS = Path(__file__).parent / "datos"


@pytest.fixture(scope="session")
def _base():
    return cargar(DATOS / "harness.yaml")


@pytest.fixture
def m(_base):
    """Copia fresca del manifiesto de ejemplo: cada test puede romperla."""
    return copy.deepcopy(_base)


def issue(numero, cerrada=False, etiquetas=()):
    return {"number": numero, "cerrada": cerrada, "etiquetas": set(etiquetas)}


@pytest.fixture
def issues():
    return [issue(1, etiquetas=["en-curso"]), issue(2, cerrada=True), issue(3)]
