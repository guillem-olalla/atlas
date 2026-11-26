from datetime import datetime, timezone

import pytest

from atlas.github import Cliente, caducidad_token, siguiente_pagina


def test_caducidad_en_utc():
    assert caducidad_token({"github-authentication-token-expiration": "2027-11-26 10:00:00 UTC"}) == datetime(
        2027, 11, 26, 10, 0, tzinfo=timezone.utc
    )


def test_caducidad_con_desfase():
    assert caducidad_token({"github-authentication-token-expiration": "2027-11-26 03:00:00 -0700"}) == datetime(
        2027, 11, 26, 10, 0, tzinfo=timezone.utc
    )


def test_sin_cabecera_o_ilegible():
    assert caducidad_token({}) is None
    assert caducidad_token({"github-authentication-token-expiration": "mañana"}) is None


def test_siguiente_pagina():
    link = '<https://api.github.com/x?page=2>; rel="next", <https://api.github.com/x?page=5>; rel="last"'
    assert siguiente_pagina(link) == "https://api.github.com/x?page=2"
    assert siguiente_pagina('<https://api.github.com/x?page=1>; rel="prev"') is None
    assert siguiente_pagina("") is None


def test_cliente_sin_token_no_arranca():
    with pytest.raises(ValueError):
        Cliente("")
