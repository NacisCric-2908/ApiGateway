import json
import subprocess
import sys

import pytest

from app import claves, clientes
from app.cli import SERVICIOS

CATALOGO = [
    {"client_id": "mid-flota", "alcances": ["zonas:leer"]},
    {"client_id": "demo", "alcances": ["recomendaciones:leer", "alertas:leer"]},
]


def _cli(*args, cwd):
    return subprocess.run([sys.executable, "-m", "app.cli", *args], capture_output=True, text=True, cwd=cwd, env={"PYTHONPATH": "/srv"})


def _env(texto: str) -> dict:
    return dict(l.split("=", 1) for l in texto.splitlines() if l and not l.startswith("#"))


@pytest.fixture
def catalogo(tmp_path):
    (tmp_path / "catalogo.json").write_text(json.dumps(CATALOGO))
    return tmp_path


def test_inicializar_genera_un_env_coherente_con_las_credenciales(catalogo):
    r = _cli("inicializar", "--catalogo", "catalogo.json", cwd=catalogo)
    assert r.returncode == 0, r.stderr
    env = _env((catalogo / ".env").read_text())
    creds = json.loads((catalogo / "credenciales-locales.json").read_text())

    # los secretos en claro de los clientes verifican contra los hashes del .env
    registro = clientes.Registro.desde_json(env["CLIENTES_JSON"].strip("'"))
    assert registro.autenticar("demo", creds["clientes"]["demo"]).alcances == {"recomendaciones:leer", "alertas:leer"}
    assert registro.autenticar("mid-flota", creds["clientes"]["demo"]) is None

    # el JWKS de KrakenD corresponde a la llave privada del servicio de tokens
    jwks = json.loads(env["JWKS_JSON"].strip("'"))
    assert jwks == {"keys": [claves.a_jwk(claves.cargar_privada(env["JWT_PRIVATE_KEY_B64"]).public_key())]}

    # un secreto por servicio, todos distintos
    secretos = [env[f"{s}_SECRET"] for s in SERVICIOS]
    assert len(set(secretos)) == len(SERVICIOS)
    assert set(creds["secretos_de_servicios"].values()) == set(secretos)
    assert oct((catalogo / ".env").stat().st_mode & 0o777) == "0o600"


def test_el_env_no_contiene_dolares_que_compose_interpretaria(catalogo):
    _cli("inicializar", "--catalogo", "catalogo.json", cwd=catalogo)
    assert "$" not in (catalogo / ".env").read_text()


def test_no_sobrescribe_un_env_existente_sin_forzar(catalogo):
    (catalogo / ".env").write_text("SECRETOS_VIEJOS=1\n")
    r = _cli("inicializar", "--catalogo", "catalogo.json", cwd=catalogo)
    assert r.returncode != 0 and "ya existe" in r.stderr
    assert (catalogo / ".env").read_text() == "SECRETOS_VIEJOS=1\n"
    assert _cli("inicializar", "--catalogo", "catalogo.json", "--forzar", cwd=catalogo).returncode == 0


def test_cliente_muestra_el_secreto_una_vez_y_una_entrada_con_hash(tmp_path):
    r = _cli("cliente", "nuevo", "--alcances", "b:leer,a:leer", cwd=tmp_path)
    salida = dict(l.split("=", 1) for l in r.stdout.splitlines())
    secreto = salida["CLIENT_SECRET"].split("  #")[0]
    entrada = json.loads(salida["ENTRADA"])
    assert entrada["alcances"] == ["a:leer", "b:leer"] and secreto not in salida["ENTRADA"]
    assert clientes.verificar_secreto(secreto, entrada["secret_hash"])
