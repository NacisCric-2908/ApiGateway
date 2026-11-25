"""Llaves RSA: cargar la privada, derivar la pública en formato JWK y generar un par nuevo."""

import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _b64url(n: int) -> str:
    return base64.urlsafe_b64encode(n.to_bytes((n.bit_length() + 7) // 8, "big")).rstrip(b"=").decode()


def cargar_privada(b64: str) -> rsa.RSAPrivateKey:
    try:
        clave = serialization.load_pem_private_key(base64.b64decode(b64), password=None)
    except Exception as e:  # PEM inválido, base64 inválido, llave con clave...
        raise ValueError("JWT_PRIVATE_KEY_B64 no es una llave privada PEM válida (en base64)") from e
    if not isinstance(clave, rsa.RSAPrivateKey):
        raise ValueError("La llave debe ser RSA")
    return clave


def pem_privada(clave: rsa.RSAPrivateKey) -> bytes:
    return clave.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def kid_de(publica: rsa.RSAPublicKey) -> str:
    """Identificador de la llave: su huella RFC 7638. Cambia si cambia la llave, así no hay confusiones al rotar."""
    n = publica.public_numbers()
    canonico = json.dumps({"e": _b64url(n.e), "kty": "RSA", "n": _b64url(n.n)}, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(hashlib.sha256(canonico.encode()).digest()).rstrip(b"=").decode()


def a_jwk(publica: rsa.RSAPublicKey) -> dict:
    n = publica.public_numbers()
    return {"kty": "RSA", "use": "sig", "alg": "RS256", "kid": kid_de(publica), "n": _b64url(n.n), "e": _b64url(n.e)}


def generar_par() -> tuple[str, dict]:
    """Devuelve (llave privada PEM en base64, conjunto JWKS con la pública)."""
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return base64.b64encode(pem_privada(clave)).decode(), {"keys": [a_jwk(clave.public_key())]}
