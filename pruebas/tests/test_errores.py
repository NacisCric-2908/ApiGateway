"""Lo que el gateway deja pasar tal cual y lo que responde él mismo."""

from tests.conftest import auth


def test_un_error_del_servicio_pasa_intacto_con_su_estado_y_su_cuerpo(http, token_admin):
    r = http.patch("/flota/vehiculos/conflicto/estado", headers=auth(token_admin), json={"estado": "en_viaje"})
    assert r.status_code == 409
    assert r.json() == {"codigo": "transicion_invalida", "mensaje": "Conflicto simulado.", "detalle": {}}
    n = http.get("/flota/vehiculos/inexistente", headers=auth(token_admin))
    assert n.status_code == 404 and n.json()["codigo"] == "no_encontrado"


def test_una_ruta_inexistente_responde_404_en_el_formato_comun(http):
    r = http.get("/no/existe")
    assert r.status_code == 404
    assert r.json() == {"codigo": "no_encontrado", "mensaje": "La ruta no existe en el gateway.", "detalle": {}}


def test_un_metodo_no_permitido_responde_405_en_el_formato_comun(http):
    r = http.delete("/flota/localidades")
    assert r.status_code == 405 and r.json()["codigo"] == "metodo_no_permitido"


def test_health_es_publico(http):
    r = http.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_no_revela_la_version_de_krakend(http):
    assert "x-krakend" not in {k.lower() for k in http.get("/health").headers}
