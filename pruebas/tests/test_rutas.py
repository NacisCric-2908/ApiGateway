"""Cada ruta del catálogo: qué recibe exactamente el servicio de destino."""

import json
from urllib.parse import parse_qs

import pytest

from tests.conftest import CON_CUERPO, CREDENCIALES, IDS, RUTAS, SERVICIOS, auth, rellenar


@pytest.mark.parametrize("r", RUTAS, ids=IDS)
def test_reenvia_a_la_ruta_y_al_servicio_correctos(http, token_admin, r):
    consulta = {q: "1" for q in r.get("query", [])} | {"parametro_no_permitido": "x"}
    cuerpo = {"dato": "valor", "numero": 7} if r["metodo"] in CON_CUERPO else None
    resp = http.request(
        r["metodo"], rellenar(r["publica"]), params=consulta, json=cuerpo,
        headers={**auth(token_admin), "X-Gateway-Secret": "falsificado-por-el-cliente", "X-Client-Id": "falsificado"},
    )  # fmt: skip
    assert resp.status_code == 200, resp.text
    eco = resp.json()

    assert eco["servicio"] == r["servicio"]  # fue al servicio que corresponde
    assert eco["metodo"] == r["metodo"]
    assert eco["ruta"] == rellenar(r["destino"])  # se reescribió el prefijo según el catálogo
    assert set(parse_qs(eco["consulta"])) == set(r.get("query", []))  # solo pasan las consultas permitidas

    cab = eco["cabeceras"]
    secreto_esperado = CREDENCIALES["secretos_de_servicios"][SERVICIOS[r["servicio"]]["secreto_env"]]
    assert cab["x-gateway-secret"] == secreto_esperado  # se inyectó el secreto DEL SERVICIO, no el del cliente
    assert "authorization" not in cab  # el token del cliente no llega a los servicios
    assert cab["x-client-id"] == "administrador"  # quién llama sale del TOKEN, no de lo que diga el cliente
    if cuerpo:
        assert json.loads(eco["cuerpo"]) == cuerpo and cab["content-type"].startswith("application/json")


def test_el_catalogo_tiene_las_rutas_clave_del_enunciado():
    publicas = {(r["metodo"], r["publica"]) for r in RUTAS}
    assert ("GET", "/flota/recomendaciones/vehiculo") in publicas
    assert ("POST", "/viajes/iniciar") in publicas
    assert ("GET", "/viajes/zonas/verificar") in publicas  # la que usa el MID de Flota
    assert ("PATCH", "/flota/vehiculos/{vehiculo_id}/estado") in publicas
    assert ("POST", "/cuentas/liquidaciones") in publicas


def test_las_dos_rutas_del_mid_de_flota_tienen_reglas_de_prefijo_distintas(http, token_admin):
    a = http.get("/flota/recomendaciones/vehiculo", headers=auth(token_admin)).json()
    b = http.get("/flota/alertas", headers=auth(token_admin)).json()
    assert a["ruta"] == "/recomendaciones/vehiculo"  # se quita /flota
    assert b["ruta"] == "/flota/alertas"  # no se quita
