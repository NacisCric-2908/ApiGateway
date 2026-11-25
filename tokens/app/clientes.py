"""Registro de clientes (los MID y la aplicación de la demostración) y verificación de sus secretos.

Los secretos NO se guardan: solo su hash con PBKDF2-SHA256 (`pbkdf2_sha256:iteraciones:sal:hash`; con «:» y no «$» para que Docker Compose no lo interprete como variable). Los secretos
generados por este proyecto son aleatorios de 256 bits, así que un número moderado de iteraciones basta.
"""

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass

ITERACIONES = 100_000


def hash_secreto(secreto: str, iteraciones: int = ITERACIONES) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", secreto.encode(), sal, iteraciones)
    return f"pbkdf2_sha256:{iteraciones}:{base64.b64encode(sal).decode()}:{base64.b64encode(h).decode()}"


def verificar_secreto(secreto: str, almacenado: str) -> bool:
    try:
        algoritmo, iteraciones, sal, esperado = almacenado.split(":")
        if algoritmo != "pbkdf2_sha256":
            return False
        h = hashlib.pbkdf2_hmac("sha256", secreto.encode(), base64.b64decode(sal), int(iteraciones))
        return hmac.compare_digest(h, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False


def generar_secreto() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class Cliente:
    client_id: str
    secret_hash: str
    alcances: frozenset[str]


class Registro:
    def __init__(self, clientes: list[Cliente]):
        ids = [c.client_id for c in clientes]
        if len(ids) != len(set(ids)):
            raise ValueError("Hay client_id repetidos en CLIENTES_JSON")
        self._por_id = {c.client_id: c for c in clientes}
        # Hash falso: al autenticar un cliente que no existe se calcula igual un hash, para que no se pueda
        # saber por el tiempo de respuesta si el client_id existe.
        self._falso = hash_secreto("no-existe")

    @classmethod
    def desde_json(cls, texto: str) -> "Registro":
        try:
            datos = json.loads(texto)
            return cls(
                [Cliente(d["client_id"], d["secret_hash"], frozenset(d["alcances"])) for d in datos]
            )
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError("CLIENTES_JSON no es una lista válida de {client_id, secret_hash, alcances}") from e

    def autenticar(self, client_id: str, secreto: str) -> Cliente | None:
        cliente = self._por_id.get(client_id)
        ok = verificar_secreto(secreto, cliente.secret_hash if cliente else self._falso)
        return cliente if (cliente and ok) else None

    def ids(self) -> list[str]:
        return sorted(self._por_id)
