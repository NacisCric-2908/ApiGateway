"""API del servicio de tokens: POST /token (OAuth2 client credentials), JWKS público y /health."""

import base64
import binascii
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

from app.claves import a_jwk, cargar_privada, kid_de
from app.clientes import Registro
from app.config import Settings, get_settings
from app.emision import AlcanceInvalido, emitir, resolver_alcances

log = logging.getLogger("tokens")
SIN_CACHE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _error(estado: int, codigo: str, descripcion: str, cabeceras: dict | None = None) -> JSONResponse:
    """Errores en el formato de OAuth2 (RFC 6749 §5.2), el que esperan las librerías cliente."""
    return JSONResponse(
        {"error": codigo, "error_description": descripcion}, status_code=estado, headers={**SIN_CACHE, **(cabeceras or {})}
    )


def _credenciales_basic(cabecera: str | None) -> tuple[str, str] | None:
    if not cabecera or not cabecera.lower().startswith("basic "):
        return None
    try:
        usuario, _, clave = base64.b64decode(cabecera[6:]).decode().partition(":")
    except (binascii.Error, UnicodeDecodeError):
        return None
    return usuario, clave


def crear_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        s = settings or get_settings()
        logging.basicConfig(level=s.log_level.upper())
        clave = cargar_privada(s.jwt_private_key_b64)
        app.state.s = s
        app.state.clave = clave
        app.state.kid = kid_de(clave.public_key())
        app.state.jwk = a_jwk(clave.public_key())
        app.state.registro = Registro.desde_json(s.clientes_json)
        log.info("Servicio de tokens listo: kid=%s clientes=%s", app.state.kid, app.state.registro.ids())
        yield

    app = FastAPI(title="Servicio de tokens del gateway Rodar", version="0.1.0", lifespan=lifespan)

    @app.post("/token", include_in_schema=True, summary="Pedir un token de acceso (OAuth2 client credentials)")
    async def token(
        request: Request,
        grant_type: Annotated[str | None, Form()] = None,
        client_id: Annotated[str | None, Form()] = None,
        client_secret: Annotated[str | None, Form()] = None,
        scope: Annotated[str | None, Form()] = None,
    ):
        # Las credenciales pueden venir en la cabecera Authorization: Basic (lo que usan por defecto muchas
        # librerías, como Spring) o en el formulario (lo que usa el MID de Flota). Se aceptan las dos.
        basic = _credenciales_basic(request.headers.get("authorization"))
        id_cliente, secreto = basic if basic else (client_id, client_secret)
        s: Settings = request.app.state.s
        if not id_cliente or secreto is None:
            return _error(401, "invalid_client", "Faltan las credenciales del cliente.", {"WWW-Authenticate": 'Basic realm="rodar"'})

        cliente = request.app.state.registro.autenticar(id_cliente, secreto)
        if cliente is None:
            log.warning("Credenciales inválidas para el cliente %r", id_cliente)
            return _error(401, "invalid_client", "Credenciales de cliente inválidas.", {"WWW-Authenticate": 'Basic realm="rodar"'})
        if grant_type != "client_credentials":
            return _error(400, "unsupported_grant_type" if grant_type else "invalid_request",
                          "Solo se admite grant_type=client_credentials.")
        try:
            alcances = resolver_alcances(cliente, scope)
        except AlcanceInvalido as e:
            return _error(400, "invalid_scope", f"Alcances no permitidos para este cliente: {', '.join(e.no_permitidos)}")

        respuesta = emitir(
            request.app.state.clave, request.app.state.kid, cliente, alcances,
            emisor=s.jwt_issuer, audiencia=s.jwt_audience, ttl_s=s.token_ttl_s,
        )  # fmt: skip
        log.info("Token emitido: client_id=%s alcances=%s", cliente.client_id, respuesta["scope"])
        return JSONResponse(respuesta, headers=SIN_CACHE)

    @app.get("/.well-known/jwks.json", summary="Llave pública con la que se verifican los tokens")
    async def jwks(request: Request):
        return JSONResponse({"keys": [request.app.state.jwk]}, headers={"Cache-Control": "public, max-age=300"})

    @app.get("/health", summary="Estado del servicio")
    async def health():
        return {"estado": "ok"}

    return app


def _app_por_defecto() -> FastAPI:
    return crear_app()


app = _app_por_defecto()
