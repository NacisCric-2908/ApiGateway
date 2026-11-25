import base64

import jwt
import pytest

from app import claves
from tests.conftest import SECRETO_ADMIN, SECRETO_MID

FORM = {"grant_type": "client_credentials", "client_id": "mid-flota", "client_secret": SECRETO_MID}


def verificar(token: str, jwks: dict, **kw) -> dict:
    jwk = jwks["keys"][0]
    clave = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    return jwt.decode(token, clave, algorithms=["RS256"], audience="rodar", issuer="rodar-gateway", **kw)


def test_emite_un_token_con_las_credenciales_en_el_formulario(cliente_http):
    r = cliente_http.post("/token", data=FORM)
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    cuerpo = r.json()
    assert cuerpo["token_type"] == "Bearer" and cuerpo["expires_in"] == 900 and cuerpo["scope"] == "zonas:leer"
    assert cuerpo["access_token"].count(".") == 2


def test_el_token_se_verifica_con_el_jwks_publico_y_trae_los_reclamos_esperados(cliente_http):
    token = cliente_http.post("/token", data=FORM).json()["access_token"]
    jwks = cliente_http.get("/.well-known/jwks.json").json()
    datos = verificar(token, jwks)
    assert datos["iss"] == "rodar-gateway" and datos["aud"] == "rodar"
    assert datos["sub"] == datos["client_id"] == "mid-flota"
    assert datos["scope"] == "zonas:leer"
    assert datos["exp"] - datos["iat"] == 900
    assert datos["jti"]
    cabecera = jwt.get_unverified_header(token)
    assert cabecera["alg"] == "RS256" and cabecera["kid"] == jwks["keys"][0]["kid"]  # KrakenD exige alg y kid


def test_acepta_las_credenciales_por_http_basic(cliente_http):
    basic = base64.b64encode(f"mid-flota:{SECRETO_MID}".encode()).decode()
    r = cliente_http.post("/token", data={"grant_type": "client_credentials"}, headers={"Authorization": f"Basic {basic}"})
    assert r.status_code == 200 and r.json()["scope"] == "zonas:leer"


def test_sin_scope_concede_todos_los_del_cliente_y_con_scope_solo_un_subconjunto(cliente_http):
    admin = {"grant_type": "client_credentials", "client_id": "admin", "client_secret": SECRETO_ADMIN}
    assert cliente_http.post("/token", data=admin).json()["scope"] == "vehiculos:escribir vehiculos:leer zonas:leer"
    parcial = cliente_http.post("/token", data={**admin, "scope": "vehiculos:leer"}).json()
    assert parcial["scope"] == "vehiculos:leer"


def test_pedir_un_alcance_que_el_cliente_no_tiene_es_invalid_scope(cliente_http):
    r = cliente_http.post("/token", data={**FORM, "scope": "zonas:leer vehiculos:escribir"})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_scope" and "vehiculos:escribir" in r.json()["error_description"]


@pytest.mark.parametrize(
    "form",
    [
        {**FORM, "client_secret": "equivocado"},
        {**FORM, "client_id": "no-existe"},
        {"grant_type": "client_credentials"},
        {"grant_type": "client_credentials", "client_id": "mid-flota"},
    ],
)
def test_credenciales_malas_o_ausentes_responden_401_invalid_client(cliente_http, form):
    r = cliente_http.post("/token", data=form)
    assert r.status_code == 401
    assert r.json()["error"] == "invalid_client"
    assert "Basic" in r.headers["www-authenticate"]


def test_el_error_no_revela_si_el_cliente_existe(cliente_http):
    a = cliente_http.post("/token", data={**FORM, "client_secret": "mal"}).json()
    b = cliente_http.post("/token", data={**FORM, "client_id": "no-existe"}).json()
    assert a == b


@pytest.mark.parametrize(("grant", "error"), [("password", "unsupported_grant_type"), (None, "invalid_request")])
def test_solo_se_admite_client_credentials(cliente_http, grant, error):
    form = {k: v for k, v in {**FORM, "grant_type": grant}.items() if v is not None}
    r = cliente_http.post("/token", data=form)
    assert r.status_code == 400 and r.json()["error"] == error


def test_el_jwks_publico_coincide_con_la_llave_privada(cliente_http, par):
    jwks = cliente_http.get("/.well-known/jwks.json").json()
    assert jwks == par[1]
    assert "d" not in jwks["keys"][0] and "p" not in jwks["keys"][0]  # nunca la parte privada


def test_un_token_firmado_con_otra_llave_no_se_verifica(cliente_http):
    token = cliente_http.post("/token", data=FORM).json()["access_token"]
    _, otro = claves.generar_par()
    with pytest.raises(jwt.InvalidSignatureError):
        verificar(token, otro)


def test_health_es_publico(cliente_http):
    assert cliente_http.get("/health").json() == {"estado": "ok"}


def test_no_se_pueden_pedir_tokens_con_get(cliente_http):
    assert cliente_http.get("/token").status_code == 405
