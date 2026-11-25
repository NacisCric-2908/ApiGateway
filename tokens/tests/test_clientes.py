import pytest

from app.clientes import Registro, hash_secreto, verificar_secreto


def test_el_hash_no_contiene_el_secreto_y_se_verifica():
    h = hash_secreto("mi-secreto", 1000)
    assert "mi-secreto" not in h and h.startswith("pbkdf2_sha256:1000:")
    assert verificar_secreto("mi-secreto", h)
    assert not verificar_secreto("otro", h)


def test_dos_hashes_del_mismo_secreto_son_distintos_por_la_sal():
    assert hash_secreto("x", 1000) != hash_secreto("x", 1000)


def test_el_hash_no_usa_dolar_para_que_compose_no_lo_interprete():
    assert "$" not in hash_secreto("x", 1000)


@pytest.mark.parametrize("basura", ["", "abc", "pbkdf2_sha256:x:y:z", "md5:1:2:3", "a:b:c"])
def test_un_hash_mal_formado_nunca_verifica(basura):
    assert not verificar_secreto("x", basura)


def test_el_registro_autentica_solo_con_id_y_secreto_correctos():
    h = hash_secreto("s", 1000)
    r = Registro.desde_json(f'[{{"client_id":"a","secret_hash":"{h}","alcances":["x:leer"]}}]')
    assert r.autenticar("a", "s").alcances == {"x:leer"}
    assert r.autenticar("a", "mal") is None
    assert r.autenticar("no-existe", "s") is None


def test_clientes_repetidos_o_json_invalido_se_rechazan():
    with pytest.raises(ValueError):
        Registro.desde_json("no es json")
    with pytest.raises(ValueError):
        Registro.desde_json('[{"client_id":"a"}]')
    h = hash_secreto("s", 1000)
    entrada = f'{{"client_id":"a","secret_hash":"{h}","alcances":[]}}'
    with pytest.raises(ValueError):
        Registro.desde_json(f"[{entrada},{entrada}]")
