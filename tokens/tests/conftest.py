import json

import pytest
from fastapi.testclient import TestClient

from app import claves, clientes
from app.config import Settings
from app.main import crear_app

SECRETO_MID = "secreto-de-prueba-del-mid"
SECRETO_ADMIN = "secreto-de-prueba-del-admin"


@pytest.fixture(scope="session")
def par():
    return claves.generar_par()  # (privada en base64, JWKS)


@pytest.fixture
def ajustes(par):
    registro = [
        {"client_id": "mid-flota", "secret_hash": clientes.hash_secreto(SECRETO_MID, 1000), "alcances": ["zonas:leer"]},
        {
            "client_id": "admin",
            "secret_hash": clientes.hash_secreto(SECRETO_ADMIN, 1000),
            "alcances": ["vehiculos:leer", "vehiculos:escribir", "zonas:leer"],
        },
    ]
    return Settings(jwt_private_key_b64=par[0], clientes_json=json.dumps(registro), token_ttl_s=900)


@pytest.fixture
def cliente_http(ajustes):
    with TestClient(crear_app(ajustes)) as c:
        yield c
