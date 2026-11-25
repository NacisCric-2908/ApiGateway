# Despliegue en Azure del gateway y el servicio de tokens

La guía completa (plataforma compartida, acceso de GitHub por OIDC, costos, modo demostración, solución de problemas y qué se verificó) está en el repositorio **ApiFlota**: `docs/despliegue-azure.md`. Aquí lo propio del gateway.

## Qué se despliega

Dos aplicaciones de Container Apps, definidas en [`infra/app.bicep`](../infra/app.bicep) y desplegadas por [`.github/workflows/cd.yml`](../.github/workflows/cd.yml) al fusionar a `main`:

| Aplicación | Ingreso | Qué es |
| --- | --- | --- |
| `rodar-tokens` | interno | El servicio de tokens. Único con la **llave privada** |
| `rodar-gateway` | **público** (HTTPS lo pone Azure) | KrakenD. Solo tiene las llaves **públicas** |

La URL pública termina en `…azurecontainerapps.io`: el despliegue la imprime y la deja en el resumen de la ejecución. **Esa es la dirección que se publica a los demás equipos.** (Un dominio propio es opcional y se agrega después en el portal, sin tocar el código.)

## Los tokens funcionan igual que en local

La pregunta clave: *¿los tokens que se generan en local siguen funcionando en Azure?* Dos respuestas:

1. **Un token concreto no viaja entre entornos**, ni debe: cada entorno tiene sus propias llaves. El de local lo firma la llave de local y Azure lo rechaza (y viceversa). Eso es lo correcto.
2. **El mecanismo es idéntico**: la misma imagen de tokens y la misma de gateway corren en local y en Azure. Lo único que cambia son los valores de `JWT_PRIVATE_KEY_B64`, `JWKS_JSON`, `CLIENTES_JSON` y los secretos. Si algo funciona en local con `make test`, funciona en Azure con las variables de Azure.

Lo que sí hay que cuidar: `JWT_PRIVATE_KEY_B64` (servicio de tokens) y `JWKS_JSON` (gateway) deben salir **del mismo par de llaves**. Por eso `scripts/03-secretos-produccion.sh` genera ambos juntos.

## Una sola vez

1. Plataforma y acceso de GitHub: pasos 1 y 2 de la guía del repositorio ApiFlota.
2. Secretos de producción (desde este repositorio):

   ```bash
   DUENO=su-usuario-o-organizacion scripts/03-secretos-produccion.sh
   ```

   Genera llaves, secretos y las contraseñas de cada cliente en `secretos-produccion/` (ignorado por git), y publica en **los tres repositorios** los secretos que cada uno necesita. Léalo antes: explica qué hace y es seguro volver a ejecutarlo (solo regenera todo con `FORZAR=si`).

   **Guarde `secretos-produccion/` en un gestor de contraseñas**: ahí están, en claro, las contraseñas de los clientes, que **no se pueden recuperar** desde Azure ni GitHub.
3. Despliegue en el orden **ApiFlota → ApiFlotaMID → ApiWategay** (Actions → *Despliegue a Azure* → Run workflow, o fusionando a `main`).

## Secretos y variables de este repositorio

| Tipo | Nombre | Quién lo crea |
| --- | --- | --- |
| Variable | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP` | `02-acceso-github.sh` (no son secretas) |
| Secreto | `JWT_PRIVATE_KEY_B64`, `CLIENTES_JSON`, `JWKS_JSON` | `03-secretos-produccion.sh` |
| Secreto | `FLOTA_CRUD_SECRET`, `FLOTA_MID_SECRET` | `03-secretos-produccion.sh` |
| Secreto | `VIAJES_CRUD_SECRET`, `VIAJES_MID_SECRET`, `CUENTAS_CRUD_SECRET`, `CUENTAS_MID_SECRET` | `03-secretos-produccion.sh` (se entregan a los otros equipos) |
| Variable (opcional) | `VIAJES_CRUD_URL`, `VIAJES_MID_URL`, `CUENTAS_CRUD_URL`, `CUENTAS_MID_URL` | Usted, cuando el otro equipo despliegue (URL completa con `https://`) |

Los servicios de Flota se conectan solos: el gateway calcula las direcciones internas `https://flota-crud.internal.<dominio>` y `https://flota-mid.internal.<dominio>` del mismo entorno.

## Comprobar

```bash
GATEWAY=https://<la-url-que-imprime-el-despliegue>
curl -i $GATEWAY/health                                   # 200
curl -s $GATEWAY/.well-known/jwks.json                    # {"keys":[{"kty":"RSA",...}]}
curl -s -X POST $GATEWAY/token -d grant_type=client_credentials \
  -d client_id=administrador -d client_secret=<de credenciales.json>     # access_token
curl -i $GATEWAY/flota/vehiculos                          # 401 (sin token)
curl -i -H "Authorization: Bearer <token>" "$GATEWAY/flota/vehiculos?tamano=2"   # 200 con vehículos
```

Si el último da `500` justo después de desplegar o tras un rato sin uso: arranque en frío; reintente o use `modo-demo.sh encendido` (repositorio ApiFlota).

## Qué NO está verificado

* El despliegue real en Azure (ninguna de estas plantillas se ha ejecutado en una suscripción).
* Que KrakenD acepte el certificado de la dirección interna `*.internal.<dominio>` de Container Apps al llamar a los servicios. Si falla (`x509` en los logs del gateway), la salida es declarar la URL del servicio con `http://` y activar `allowInsecure` en su `app.bicep` (el tráfico no sale del entorno).
* El límite de peticiones por IP detrás del ingreso de Azure (se configuró la lectura de `X-Forwarded-For` desde redes privadas; en local no hay proxy).
