from datetime import datetime, timezone

import pytest

from atlas.fuente import construir_mapa, leer_token


def test_mapa_con_estados_y_enlaces(m, issues):
    ahora = datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc)
    caduca = datetime(2026, 12, 31, tzinfo=timezone.utc)
    mapa = construir_mapa(m, issues, "https://example.invalid/issues/", caduca, ahora)
    por_id = {n["id"]: n for n in mapa["nodos"]}
    assert por_id["agente-x"]["estado"] == "en_curso"
    assert por_id["agente-x"]["issue_url"] == "https://example.invalid/issues/1"
    assert por_id["tarea-z"]["estado"] == "pendiente"
    assert por_id["persona-a"]["estado"] == "hecho"
    assert "issue_url" not in por_id["persona-a"]
    assert [c["id"] for c in mapa["capas"]] == ["personas", "codigo", "servidor"]
    assert mapa["generado_en"] == "2026-01-02T03:04:00+00:00"
    assert mapa["token_caduca"] == "2026-12-31T00:00:00+00:00"
    assert mapa["errores_manifiesto"] == []


def test_leer_token_quita_saltos_y_rechaza_vacio(tmp_path):
    archivo = tmp_path / "token"
    archivo.write_text("abc\n", encoding="utf-8")
    assert leer_token(archivo) == "abc"
    archivo.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError):
        leer_token(archivo)
