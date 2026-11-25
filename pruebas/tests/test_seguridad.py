"""Quién puede pasar: sin token, token falso o manipulado, y alcances."""

import pytest

from tests.conftest import IDS, RUTAS, auth, rellenar


def llamar(http, r, headers=None):
    return http.request(r["metodo"], rellenar(r["publica"]), headers=headers or {})


@pytest.mark.parametrize("r", RUTAS, ids=IDS)
def test_sin_token_responde_401(http, r):
    assert llamar(http, r).status_code == 401


@pytest.mark.parametrize("r", RUTAS, ids=IDS)
def test_con_un_token_inventado_responde_401(http, r):
    assert llamar(http, r, auth("abc.def.ghi")).status_code == 401


@pytest.mark.parametrize("r", RUTAS, ids=IDS)
def test_sin_el_alcance_de_la_ruta_responde_403_y_con_el_alcance_pasa(http, token_mid_flota, r):
    """mid-flota solo tiene `zonas:leer`: solo pasan las rutas que piden ese alcance."""
    esperado = 200 if "zonas:leer" in r["alcances"] else 403
    assert llamar(http, r, auth(token_mid_flota)).status_code == esperado


def test_un_token_de_un_alcance_no_sirve_para_otra_ruta_aunque_sea_del_mismo_servicio(http, fabricar):
    leer = fabricar(scope="vehiculos:leer")
    assert http.get("/flota/vehiculos", headers=auth(leer)).status_code == 200
    assert http.post("/flota/vehiculos", headers=auth(leer), json={}).status_code == 403


def test_un_token_sin_el_reclamo_scope_responde_403(http, fabricar):
    assert http.get("/flota/vehiculos", headers=auth(fabricar(scope=None))).status_code == 403


def test_un_token_valido_pasa(http, fabricar):
    assert http.get("/flota/vehiculos", headers=auth(fabricar())).status_code == 200


@pytest.mark.parametrize(
    ("nombre", "cambios"),
    [
        ("vencido", {"exp": 1_000_000_000}),
        ("audiencia ajena", {"aud": "otra-audiencia"}),
        ("emisor ajeno", {"iss": "otro-emisor"}),
        ("todavía no vigente", {"nbf": 4_000_000_000, "exp": 4_000_000_100}),
    ],
)
def test_un_token_firmado_bien_pero_con_reclamos_malos_responde_401(http, fabricar, nombre, cambios):
    assert http.get("/flota/vehiculos", headers=auth(fabricar(**cambios))).status_code == 401


def test_un_token_firmado_con_otra_llave_responde_401(http, fabricar, clave_ajena):
    assert http.get("/flota/vehiculos", headers=auth(fabricar(clave=clave_ajena))).status_code == 401


def test_un_token_con_un_kid_desconocido_responde_401(http, fabricar):
    assert http.get("/flota/vehiculos", headers=auth(fabricar(kid="no-existe"))).status_code == 401


def test_un_token_con_alg_none_responde_401(http, fabricar):
    import base64
    import json

    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    sin_firma = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'scope': 'vehiculos:leer', 'iss': 'rodar-gateway', 'aud': 'rodar'})}."
    assert http.get("/flota/vehiculos", headers=auth(sin_firma)).status_code == 401


def test_confusion_de_algoritmo_hs256_firmado_con_la_llave_publica_responde_401(http, jwk_publico):
    """Ataque clásico: firmar con HS256 usando como secreto el material público. KrakenD fija RS256."""
    import time

    import jwt

    ahora = int(time.time())
    token = jwt.encode(
        {"iss": "rodar-gateway", "aud": "rodar", "exp": ahora + 600, "scope": "vehiculos:leer vehiculos:escribir"},
        jwk_publico["n"],
        algorithm="HS256",
        headers={"kid": jwk_publico["kid"]},
    )
    assert http.get("/flota/vehiculos", headers=auth(token)).status_code == 401


def test_la_demostracion_paso_2_un_token_del_mid_de_flota_no_puede_iniciar_un_viaje(http, token_mid_flota):
    assert http.post("/viajes/iniciar", headers=auth(token_mid_flota), json={}).status_code == 403
