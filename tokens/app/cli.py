"""Herramientas de línea de comandos (se ejecutan dentro de Docker, ver el Makefile del repositorio).

    python -m app.cli claves                        un par de llaves nuevo (privada en base64 + JWKS público)
    python -m app.cli cliente ID --alcances a,b     un cliente nuevo: secreto (se muestra UNA vez) y su entrada con hash
    python -m app.cli inicializar --catalogo ...    todo lo de desarrollo: llaves, clientes, secretos de los servicios
"""

import argparse
import json
import sys
from pathlib import Path

from app import claves, clientes

# Un secreto por servicio detrás del gateway: es el valor de X-Gateway-Secret que el gateway agrega al reenviar.
SERVICIOS = ["FLOTA_CRUD", "FLOTA_MID", "VIAJES_CRUD", "VIAJES_MID", "CUENTAS_CRUD", "CUENTAS_MID"]


def _json(datos) -> str:
    return json.dumps(datos, separators=(",", ":"), ensure_ascii=False)


def cmd_claves(_: argparse.Namespace) -> None:
    privada, jwks = claves.generar_par()
    print(f"JWT_PRIVATE_KEY_B64={privada}")
    print(f"JWKS_JSON='{_json(jwks)}'")


def _entrada(client_id: str, secreto: str, alcances: list[str]) -> dict:
    return {"client_id": client_id, "secret_hash": clientes.hash_secreto(secreto), "alcances": sorted(alcances)}


def cmd_cliente(args: argparse.Namespace) -> None:
    secreto = clientes.generar_secreto()
    print(f"CLIENT_ID={args.client_id}")
    print(f"CLIENT_SECRET={secreto}  # se muestra una sola vez; guárdelo en un lugar seguro")
    print(f"ENTRADA={_json(_entrada(args.client_id, secreto, args.alcances.split(',')))}")


def cmd_inicializar(args: argparse.Namespace) -> None:
    salida_env, salida_cred = Path(args.salida_env), Path(args.salida_credenciales)
    if salida_env.exists() and not args.forzar:
        sys.exit(f"{salida_env} ya existe: no se sobrescribe (se perderían los secretos). Use --forzar para regenerarlo.")
    catalogo = json.loads(Path(args.catalogo).read_text(encoding="utf-8"))

    privada, jwks = claves.generar_par()
    secretos_clientes = {c["client_id"]: clientes.generar_secreto() for c in catalogo}
    entradas = [_entrada(c["client_id"], secretos_clientes[c["client_id"]], c["alcances"]) for c in catalogo]
    secretos_servicios = {f"{s}_SECRET": clientes.generar_secreto() for s in SERVICIOS}

    lineas = [
        "# Generado por `make setup`. Contiene secretos: NO se sube a git.",
        f"JWT_PRIVATE_KEY_B64={privada}",
        f"JWKS_JSON='{_json(jwks)}'",
        f"CLIENTES_JSON='{_json(entradas)}'",
        *(f"{k}={v}" for k, v in secretos_servicios.items()),
    ]
    salida_env.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    salida_env.chmod(0o600)
    salida_cred.write_text(
        json.dumps({"clientes": secretos_clientes, "secretos_de_servicios": secretos_servicios}, indent=2) + "\n",
        encoding="utf-8",
    )
    salida_cred.chmod(0o600)
    print(f"Listo: {salida_env} (configuración) y {salida_cred} (secretos de los clientes, en claro).")
    print("Clientes creados: " + ", ".join(secretos_clientes))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="app.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("claves").set_defaults(f=cmd_claves)
    c = sub.add_parser("cliente")
    c.add_argument("client_id")
    c.add_argument("--alcances", required=True, help="separados por coma")
    c.set_defaults(f=cmd_cliente)
    i = sub.add_parser("inicializar")
    i.add_argument("--catalogo", required=True)
    i.add_argument("--salida-env", default=".env")
    i.add_argument("--salida-credenciales", default="credenciales-locales.json")
    i.add_argument("--forzar", action="store_true")
    i.set_defaults(f=cmd_inicializar)
    args = p.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
