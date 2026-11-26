from atlas.catalogo import generar


def test_entran_agentes_y_piezas_con_modelo_ordenadas(m):
    texto = generar(m, "https://example.invalid/issues/", "manifiesto.yaml")
    filas = [l for l in texto.splitlines() if l.startswith("| `")]
    # agente-x (agente, modelo, F1) y tarea-z (proceso, mixto, F2); el resto es script o humano.
    assert [f.split("`")[1] for f in filas] == ["agente-x", "tarea-z"]
    assert "según [#1](https://example.invalid/issues/1)" in filas[0]
    assert "| personal |" in filas[0]
    assert "Generado desde `manifiesto.yaml`" in texto
    assert texto.endswith("2 piezas. Los nodos marcados `personal` son del dueño del harness y no son de clientes.\n")


def test_es_determinista(m):
    assert generar(m, "u/", "o") == generar(m, "u/", "o")
