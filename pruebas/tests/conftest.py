"""Pruebas de extremo a extremo: el gateway REAL (KrakenD + servicio de tokens) y seis servicios simulados."""

import base64
import json
import os
import re
import time
from pathlib import Path

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

GATEWAY = os.environ.get("GATEWAY_URL", "http://gateway:8080")
CREDENCIALES = json.loads(Path("/credenciales-locales.json").read_text())
RUTAS = json.loads(Path("/gateway-settings/rutas.json").read_text())["lista"]
SERVICIOS = json.loads(Path("/gateway-settings/servicios.json").read_text())
EMISOR = os.environ.get("JWT_ISSUER", "rodar-gateway")
AUDIENCIA = os.environ.get("JWT_AUDIENCE", "rodar")
CON_CUERPO = {"POST", "PUT", "PATCH"}


def id_ruta(r: dict) -> str:
    return f"{r['metodo']} {r['publica']}"


IDS = [id_ruta(r) for r in RUTAS]


def rellenar(ruta: str, valor: str = "abc-123") -> str:
    """Cambia cada {parametro} de una ruta por un valor de ejemplo."""
    return re.sub(r"\{[a-z_]+\}", valor, ruta)


def con_reintento(f, intentos: int = 8):
    """El límite de peticiones de /token puede dar 429 a ráfagas de pruebas: se espera y se reintenta."""
    for _ in range(intentos):
        r = f()
        if r.status_code != 429:
            return r
        time.sleep(0.4)
    return r


def pedir_token(http: httpx.Client, cliente: str, scope: str | None = None) -> str:
    form = {"grant_type": "client_credentials", "client_id": cliente, "client_secret": CREDENCIALES["clientes"][cliente]}
    if scope:
        form["scope"] = scope
    r = con_reintento(lambda: http.post("/token", data=form))
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def http():
    with httpx.Client(base_url=GATEWAY, timeout=20) as c:
        yield c


@pytest.fixture(scope="session")
def token_admin(http):
    return pedir_token(http, "administrador")


@pytest.fixture(scope="session")
def token_mid_flota(http):
    return pedir_token(http, "mid-flota")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- fabricación de tokens (para probar ataques) ----------
@pytest.fixture(scope="session")
def clave_privada():
    pem = base64.b64decode(os.environ["JWT_PRIVATE_KEY_B64"])
    return serialization.load_pem_private_key(pem, password=None)


@pytest.fixture(scope="session")
def jwk_publico(http):
    return con_reintento(lambda: http.get("/.well-known/jwks.json")).json()["keys"][0]


@pytest.fixture(scope="session")
def fabricar(clave_privada, jwk_publico):
    """fabricar(**cambios) -> token RS256 válido con la llave real, salvo lo que se cambie."""

    def _f(clave=None, kid=None, alg="RS256", **cambios) -> str:
        ahora = int(time.time())
        reclamos = {
            "iss": EMISOR, "aud": AUDIENCIA, "sub": "administrador", "client_id": "administrador",
            "iat": ahora, "nbf": ahora, "exp": ahora + 600, "scope": "vehiculos:leer vehiculos:escribir",
        }  # fmt: skip
        reclamos.update(cambios)
        reclamos = {k: v for k, v in reclamos.items() if v is not None}
        return jwt.encode(reclamos, clave or clave_privada, algorithm=alg, headers={"kid": kid or jwk_publico["kid"]})

    return _f


@pytest.fixture(scope="session")
def clave_ajena():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)
