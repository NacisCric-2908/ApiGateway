#!/bin/sh
# Arranque del gateway: valida la configuración mínima, escribe las llaves públicas y levanta KrakenD.
set -eu

faltan=""
for var in TOKENS_URL JWKS_JSON; do
  eval "valor=\${$var:-}"
  [ -n "$valor" ] || faltan="$faltan $var"
done
if [ -n "$faltan" ]; then
  echo "[GATEWAY] Faltan variables de entorno obligatorias:$faltan" >&2
  exit 1
fi

# Las llaves PÚBLICAS con las que se validan los tokens (formato JWKS). Las emite el servicio de tokens.
export JWKS_PATH="${JWKS_PATH:-/tmp/jwks.json}"
printf '%s' "$JWKS_JSON" > "$JWKS_PATH"

# Una ruta se activa solo si la URL de su servicio está definida; se avisa de cuáles quedan apagadas.
for par in FLOTA_CRUD FLOTA_MID VIAJES_CRUD VIAJES_MID CUENTAS_CRUD CUENTAS_MID; do
  eval "url=\${${par}_URL:-}"; eval "secreto=\${${par}_SECRET:-}"
  if [ -z "$url" ]; then
    echo "[GATEWAY] ${par}_URL sin definir: sus rutas quedan desactivadas." >&2
  elif [ -z "$secreto" ]; then
    echo "[GATEWAY] ${par}_URL está definida pero falta ${par}_SECRET: el servicio rechazaría las peticiones (401)." >&2
    exit 1
  fi
done

export FC_ENABLE=1 FC_SETTINGS=/etc/krakend/settings
krakend check -c /etc/krakend/krakend.tmpl >/dev/null || { krakend check -c /etc/krakend/krakend.tmpl; exit 1; }
exec krakend run -c /etc/krakend/krakend.tmpl
