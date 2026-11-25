"""Va al final (zz): satura el límite de /token y las demás pruebas no deben verse afectadas antes."""

import time

import httpx

from tests.conftest import GATEWAY


def test_pedir_tokens_en_rafaga_se_limita_con_429():
    with httpx.Client(base_url=GATEWAY, timeout=10) as c:
        estados = [c.post("/token", data={"grant_type": "client_credentials", "client_id": "x", "client_secret": "y"}).status_code for _ in range(80)]
    assert 429 in estados, "el límite de peticiones a /token no se aplicó"
    assert 401 in estados  # y las que pasaron fueron rechazadas por credenciales malas
    time.sleep(1.5)  # deja que el límite se libere
