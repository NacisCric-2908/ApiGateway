"""Emisión del token de acceso (JWT firmado con RS256)."""

import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from app.clientes import Cliente


class AlcanceInvalido(Exception):
    def __init__(self, no_permitidos: list[str]):
        super().__init__(", ".join(no_permitidos))
        self.no_permitidos = no_permitidos


def resolver_alcances(cliente: Cliente, pedidos: str | None) -> list[str]:
    """Sin `scope` en la petición se conceden todos los del cliente; con `scope` solo un subconjunto de ellos."""
    if not pedidos or not pedidos.strip():
        return sorted(cliente.alcances)
    solicitados = pedidos.split()
    no_permitidos = [a for a in solicitados if a not in cliente.alcances]
    if no_permitidos:
        raise AlcanceInvalido(no_permitidos)
    return sorted(set(solicitados))


def emitir(
    clave: rsa.RSAPrivateKey, kid: str, cliente: Cliente, alcances: list[str], *, emisor: str, audiencia: str, ttl_s: int,
    ahora: int | None = None,
) -> dict:
    t = int(ahora if ahora is not None else time.time())
    reclamos = {
        "iss": emisor,
        "sub": cliente.client_id,
        "aud": audiencia,
        "iat": t,
        "nbf": t,
        "exp": t + ttl_s,
        "jti": str(uuid.uuid4()),
        "client_id": cliente.client_id,
        "scope": " ".join(alcances),  # el estándar OAuth2: alcances separados por espacio
    }
    token = jwt.encode(reclamos, clave, algorithm="RS256", headers={"kid": kid, "typ": "JWT"})
    return {"access_token": token, "token_type": "Bearer", "expires_in": ttl_s, "scope": reclamos["scope"]}
