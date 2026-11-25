# Gateway Rodar (KrakenD + servicio de tokens)

Puerta de entrada de las APIs del clúster **Rodar** (scooters y bicicletas compartidas, Bogotá): emite tokens de acceso, los valida, comprueba el alcance de cada ruta, limita las peticiones y reenvía al servicio de cada grupo (Flota, Viajes y zonas, Cuentas).

```
cliente ──Bearer──► rodar-gateway (KrakenD) ──X-Gateway-Secret──► CRUD / MID de cada grupo
   │                      │ valida el JWT (RS256) con las llaves públicas
   └─POST /token─────────►│──► rodar-tokens (OAuth2 client credentials, firma con la llave privada)
```

**Repositorio público: aquí no hay secretos.** Las llaves y contraseñas se generan al configurar (`make setup` en local, `scripts/03-secretos-produccion.sh` para Azure) y viven fuera de git.

## Quiero…

| Quiero… | Vaya a |
| --- | --- |
| **Usar las APIs** (soy de otro equipo) | [docs/consumo.md](docs/consumo.md) · [rutas](docs/rutas.md) · [Postman](docs/rodar-gateway.postman_collection.json) |
| **Ver qué es y quién lo lleva** | [GATEWAY.md](GATEWAY.md) |
| **Mantenerlo** (clientes, rutas, llaves) | [docs/operacion.md](docs/operacion.md) |
| **Desplegarlo en Azure** | [docs/despliegue-azure.md](docs/despliegue-azure.md) y la guía de ApiFlota |
| **Probarlo en mi computador** | abajo |

## Probar en local (solo Docker)

```bash
make up        # genera .env con llaves y secretos (la primera vez) y levanta tokens + gateway + 6 servicios simulados
# El gateway queda en http://localhost:8080. Las credenciales de prueba están en credenciales-locales.json
TOKEN=$(curl -s -X POST localhost:8080/token -d grant_type=client_credentials \
  -d client_id=administrador -d client_secret=<de credenciales-locales.json> | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $TOKEN" "localhost:8080/flota/vehiculos"   # lo contesta el servicio simulado
make test      # 30 pruebas del servicio de tokens + 168 de recorrido completo por el gateway
make down
```

Para probarlo con los servicios **reales** de Flota, defina en `.env` `FLOTA_CRUD_URL`/`FLOTA_MID_URL` (y sus `*_SECRET`) apuntando a ellos.

## Estructura

| Ruta | Qué es |
| --- | --- |
| `gateway/` | KrakenD: plantilla (`krakend.tmpl`), catálogo de rutas, servicios y límites (`settings/`), arranque |
| `tokens/` | Servicio de tokens (FastAPI, uv) y sus pruebas |
| `simuladores/` | Los seis servicios de atrás, simulados, para desarrollo y pruebas |
| `pruebas/` | Pruebas de recorrido completo (un caso por cada ruta del catálogo, matriz 401/403, tokens falsificados/vencidos) |
| `clientes.catalogo.json` | Las cuentas (quién puede qué). Sin secretos |
| `infra/`, `scripts/`, `.github/` | Despliegue en Azure (Bicep), secretos de producción, CI/CD |
| `docs/` | Documentación |

## Comandos

`make up | down | logs | test | setup | docs | cliente ID=… ALCANCES=… | claves`. `make docs` regenera `docs/rutas.md` y la colección de Postman desde el catálogo.

## Flujo de trabajo

`feature/*` → pull request a `develop` (CI verde) → pull request de `develop` a `main` (despliega a Azure). Commits pequeños en español (Conventional Commits).
