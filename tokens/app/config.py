from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración desde variables de entorno. Los secretos no tienen valor por defecto: si faltan, no arranca."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Llave privada RSA en formato PEM, codificada en base64 (así cabe en una variable de entorno de una línea).
    jwt_private_key_b64: str
    # Lista JSON de clientes: [{"client_id": ..., "secret_hash": ..., "alcances": [...]}]. Ver app/cli.py.
    clientes_json: str

    jwt_issuer: str = "rodar-gateway"  # claim `iss`; el gateway rechaza tokens de otro emisor
    jwt_audience: str = "rodar"  # claim `aud`; el gateway rechaza tokens para otra audiencia
    token_ttl_s: int = 900  # vigencia del token: 15 minutos
    log_level: str = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
