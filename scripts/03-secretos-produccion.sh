#!/usr/bin/env bash
# Genera las llaves y los secretos de PRODUCCIÓN y los guarda como secretos de GitHub en los tres repositorios.
# Es independiente de los de desarrollo (`make setup`): nada se reutiliza entre local y Azure.
#
# Qué hace:
#   1. Genera (con el CLI del servicio de tokens, dentro de Docker) la llave privada, las llaves públicas (JWKS), los
#      clientes con el hash de su secreto y un secreto por cada servicio. Quedan en secretos-produccion/ (ignorado por git,
#      permisos 600). AHÍ están, en claro, las credenciales de cada cliente: ENTRÉGUELAS por un canal seguro a quien
#      corresponda y no las suba a ningún lado.
#   2. Los publica con `gh secret set` en los repositorios que los necesitan.
#
# NO se puede ejecutar dos veces sin querer: si ya existe secretos-produccion/, solo vuelve a publicar lo que hay (los tokens
# y secretos ya entregados siguen valiendo). Para generar todo de nuevo (y invalidar lo anterior): FORZAR=si.
#
#   DUENO=su-usuario-de-github scripts/03-secretos-produccion.sh
#   DUENO=... REPO_CRUD=ApiFlota REPO_MID=ApiFlotaMID REPO_GATEWAY=ApiWategay scripts/03-secretos-produccion.sh
set -euo pipefail

: "${DUENO:?Defina DUENO con su usuario u organización de GitHub, p. ej. DUENO=NacisCric-2908}"
REPO_CRUD="${REPO_CRUD:-ApiFlota}"
REPO_MID="${REPO_MID:-ApiFlotaMID}"
REPO_GATEWAY="${REPO_GATEWAY:-ApiWategay}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SALIDA="$RAIZ/secretos-produccion"

command -v docker >/dev/null || { echo "Falta Docker." >&2; exit 1; }
command -v gh >/dev/null || { echo "Falta la CLI de GitHub (gh): https://cli.github.com y 'gh auth login'." >&2; exit 1; }

if [[ -f "$SALIDA/.env" && "${FORZAR:-}" != "si" ]]; then
  echo "Ya existen los secretos de producción en secretos-produccion/: solo se vuelven a publicar (FORZAR=si regenera todo)."
else
  [[ -f "$SALIDA/.env" ]] && echo "ATENCIÓN: se regeneran todos los secretos; los tokens y credenciales entregados dejarán de valer."
  mkdir -p "$SALIDA"
  chmod 700 "$SALIDA"
  docker build -q --target prod -t rodar-tokens-cli "$RAIZ/tokens" >/dev/null
  extra=()
  [[ "${FORZAR:-}" == "si" ]] && extra+=(--forzar)
  docker run --rm --user "$(id -u):$(id -g)" -v "$RAIZ:/raiz" -w /srv rodar-tokens-cli \
    python -m app.cli inicializar --catalogo /raiz/clientes.catalogo.json \
      --salida-env /raiz/secretos-produccion/.env \
      --salida-credenciales /raiz/secretos-produccion/credenciales.json \
      "${extra[@]}"
fi

# Lee NOMBRE=valor de un archivo .env y quita las comillas simples del valor.
valor() {
  local v
  v="$(grep -m1 "^$1=" "$SALIDA/.env" | cut -d= -f2-)"
  v="${v#\'}"; v="${v%\'}"
  [[ -n "$v" ]] || { echo "No encuentro $1 en secretos-produccion/.env" >&2; exit 1; }
  printf '%s' "$v"
}
secreto_cliente() {
  # Secreto en claro de un cliente, leído de credenciales.json sin depender de Python en su máquina.
  docker run --rm -v "$SALIDA:/s:ro" -e CLIENTE="$1" python:3.12-slim \
    python -c "import json,os; print(json.load(open('/s/credenciales.json'))['clientes'][os.environ['CLIENTE']], end='')"
}
publicar() {  # publicar REPO NOMBRE VALOR
  printf '%s' "$3" | gh secret set "$2" --repo "$DUENO/$1" --body -
  echo "  $DUENO/$1: secreto $2"
}

echo "Publicando secretos…"
# CRUD de Flota
publicar "$REPO_CRUD" FLOTA_CRUD_SECRET "$(valor FLOTA_CRUD_SECRET)"
# MID de Flota
publicar "$REPO_MID" FLOTA_MID_SECRET "$(valor FLOTA_MID_SECRET)"
publicar "$REPO_MID" FLOTA_CRUD_SECRET "$(valor FLOTA_CRUD_SECRET)"
publicar "$REPO_MID" MID_FLOTA_CLIENT_SECRET "$(secreto_cliente mid-flota)"
# Servicio de tokens y gateway
for nombre in JWT_PRIVATE_KEY_B64 CLIENTES_JSON JWKS_JSON FLOTA_CRUD_SECRET FLOTA_MID_SECRET \
              VIAJES_CRUD_SECRET VIAJES_MID_SECRET CUENTAS_CRUD_SECRET CUENTAS_MID_SECRET; do
  publicar "$REPO_GATEWAY" "$nombre" "$(valor "$nombre")"
done

cat <<TXT

Listo.
 • Las credenciales de cada cliente (client_id y secreto en claro) están en secretos-produccion/credenciales.json.
   Entregue a cada equipo SOLO la suya, por un canal seguro (no por el chat del grupo ni por correo sin cifrar).
 • Los secretos de VIAJES_* y CUENTAS_* son para que los otros equipos configuren en SU servicio el mismo
   GATEWAY_SECRET (el valor que el gateway les envía en X-Gateway-Secret). Entréguelos igual, por canal seguro.
 • Haga una copia de secretos-produccion/ en un gestor de contraseñas: si se pierde, hay que regenerar todo.
TXT
