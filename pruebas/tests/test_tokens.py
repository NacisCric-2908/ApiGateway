"""El endpoint /token y el JWKS, a través del gateway."""

import base64

import jwt

from tests.conftest import CREDENCIALES, con_reintento, pedir_token


def form(cliente="mid-flota", **extra):
    return {"grant_type": "client_credentials", "client_id": cliente, "client_secret": CREDENCIALES["clientes"][cliente], **extra}


def test_demostracion_paso_1_credenciales_invalidas_responden_401(http):
    r = con_reintento(lambda: http.post("/token", data={**form(), "client_secret": "equivocado"}))
    assert r.status_code == 401 and r.json()["error"] == "invalid_client"


def test_el_token_pedido_por_el_gateway_trae_los_alcances_del_cliente(http):
    r = con_reintento(lambda: http.post("/token", data=form("mid-viajes")))
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["token_type"] == "Bearer" and cuerpo["expires_in"] == 900
    assert set(cuerpo["scope"].split()) == {"usuarios:leer", "billetera:escribir", "vehiculos:leer", "vehiculos:escribir"}
    datos = jwt.decode(cuerpo["access_token"], options={"verify_signature": False})
    assert datos["sub"] == "mid-viajes" and datos["iss"] == "rodar-gateway"


def test_las_cabeceras_de_cache_del_servicio_de_tokens_llegan_al_cliente(http):
    r = con_reintento(lambda: http.post("/token", data=form()))
    assert r.headers["cache-control"] == "no-store"  # un token nunca debe quedar en una caché


def test_se_puede_pedir_el_token_con_http_basic(http):
    basic = base64.b64encode(f"mid-flota:{CREDENCIALES['clientes']['mid-flota']}".encode()).decode()
    r = con_reintento(lambda: http.post("/token", data={"grant_type": "client_credentials"}, headers={"Authorization": f"Basic {basic}"}))
    assert r.status_code == 200 and r.json()["scope"] == "zonas:leer"


def test_se_puede_pedir_un_subconjunto_de_alcances_pero_no_uno_ajeno(http):
    parcial = con_reintento(lambda: http.post("/token", data=form("administrador", scope="vehiculos:leer")))
    assert parcial.json()["scope"] == "vehiculos:leer"
    ajeno = con_reintento(lambda: http.post("/token", data=form("mid-flota", scope="vehiculos:escribir")))
    assert ajeno.status_code == 400 and ajeno.json()["error"] == "invalid_scope"


def test_el_jwks_publico_se_sirve_por_el_gateway_y_corresponde_al_token(http):
    jwks = con_reintento(lambda: http.get("/.well-known/jwks.json")).json()
    assert len(jwks["keys"]) == 1 and "d" not in jwks["keys"][0]
    token = pedir_token(http, "mid-flota")
    assert jwt.get_unverified_header(token)["kid"] == jwks["keys"][0]["kid"]


def test_el_servicio_de_tokens_no_se_alcanza_por_otras_rutas(http):
    assert http.get("/health-tokens").status_code == 404
    assert http.post("/introspect").status_code == 404
