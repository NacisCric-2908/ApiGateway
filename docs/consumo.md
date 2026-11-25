# Cómo consumir las APIs a través del gateway

Para los equipos que **usan** los servicios de Rodar. No hay que clonar nada ni conocer cómo funcionan por dentro: todo se pide a una sola dirección, con un token.

> **Datos que le entrega el líder del gateway** (por un canal seguro): la URL del gateway, su `client_id` y su `client_secret`. Se completan aquí cuando el gateway esté desplegado:
>
> | Dato | Valor |
> | --- | --- |
> | URL del gateway | _pendiente: la imprime el despliegue (`https://rodar-gateway.<…>.azurecontainerapps.io`)_ |
> | `client_id` / `client_secret` | _se entregan por separado a cada equipo_ |

## 1. Pedir un token

OAuth2, flujo *client credentials*. El token dura **15 minutos**; pida uno nuevo cuando venza (o cuando reciba `401`).

```bash
curl -s -X POST "$GATEWAY/token" \
  -d grant_type=client_credentials \
  -d client_id=mid-flota -d client_secret="$CLIENT_SECRET" \
  -d scope="zonas:leer"          # opcional: si se omite, recibe todos los alcances de su cuenta
```

```json
{ "access_token": "eyJhbGciOiJSUzI1NiIs…", "token_type": "Bearer", "expires_in": 900, "scope": "zonas:leer" }
```

* Las credenciales pueden ir en el formulario (como arriba) **o** en `Authorization: Basic base64(client_id:client_secret)`: las librerías de Spring (`spring-security-oauth2-client`) y de Python (`requests-oauthlib`, `authlib`) usan lo segundo por defecto y funcionan sin cambios.
* `scope` es opcional y va separado por espacios. Solo se puede pedir **un subconjunto** de los alcances de su cuenta; otro da `400 invalid_scope`.
* Errores en el formato estándar de OAuth2: `401 invalid_client` (credenciales malas), `400 invalid_request`, `400 unsupported_grant_type`, `400 invalid_scope`.
* Límite: 10 peticiones/s por dirección IP al endpoint `/token` (500/s en el resto del gateway). **Guarde el token y reutilícelo** hasta que venza; no pida uno por petición.

### El token por dentro (por si lo valida usted)

JWT firmado con **RS256**. Cabecera con `kid`. Reclamos: `iss=rodar-gateway`, `aud=rodar`, `sub`/`client_id` (su cuenta), `scope` (alcances separados por espacio), `iat`, `nbf`, `exp`, `jti`. Las llaves públicas están en `GET /.well-known/jwks.json`. **No tiene que validarlo**: el gateway ya lo hace antes de reenviarle nada.

## 2. Llamar a un servicio

```bash
curl -H "Authorization: Bearer $TOKEN" "$GATEWAY/flota/recomendaciones/vehiculo?lat=4.711&lng=-74.0721"
```

Las rutas disponibles, con el alcance que exige cada una, están en [rutas.md](rutas.md). Una colección de **Postman** con una petición por ruta está en [rodar-gateway.postman_collection.json](rodar-gateway.postman_collection.json) (importela, ponga `baseUrl`, `clientId` y `clientSecret`, y ejecute primero «Pedir token»).

El gateway **no cambia** lo que responde el servicio: mismos códigos, mismo cuerpo, mismo formato de error. Las referencias detalladas de cada servicio las publica su equipo (la de Flota está en `docs/integracion.md` del repositorio ApiFlota).

## 3. Errores que produce el propio gateway

| Código | Cuándo | Cuerpo |
| --- | --- | --- |
| `401` | Falta el token, es inválido, está vencido o es de otro emisor | **vacío**, con `WWW-Authenticate` |
| `403` | El token es válido pero le falta el alcance de esa ruta | **vacío** |
| `404` | La ruta no existe (o el servicio de esa ruta aún no está conectado) | `{"codigo":"no_encontrado","mensaje":"…","detalle":{}}` |
| `405` | Método no permitido en esa ruta | `{"codigo":"metodo_no_permitido","mensaje":"…","detalle":{}}` |
| `429` | Superó el límite de peticiones | **vacío** |
| `500` | El servicio de atrás no responde (caído o despertando) | **vacío** |

* **`401`/`403`/`429`/`500` generados por el gateway no traen cuerpo JSON** (es una limitación de KrakenD Community). Dependa del código de estado, no del cuerpo. Los errores **del servicio** (`400`, `404`, `409`…) sí pasan completos.
* Un `500` sin cuerpo justo después de un rato sin usar el sistema suele ser el **arranque en frío** de los servicios (ahorran dinero apagándose). Reintente a los pocos segundos.
* Las peticiones deben llevar `Content-Type: application/json` cuando tienen cuerpo.

## 4. Lo que el gateway hace por usted (y lo que no)

* Agrega a la petición la cabecera secreta que el servicio exige; **usted no la envía** y, si la envía, se descarta.
* Agrega `X-Client-Id` con su cuenta (del token) para que el servicio sepa quién llama. No se puede falsear.
* Solo pasan las cabeceras `Content-Type`, `Accept` y los parámetros de consulta que cada ruta declara; los demás se descartan.
* **Los servicios no se llaman entre sí por fuera del gateway**, salvo cada MID con su CRUD. Si su MID necesita datos de otro grupo, los pide **al gateway con el token de su MID**, no directo al servicio.

## 5. Para quien construye un MID

* Cada MID tiene su cuenta (`mid-flota`, `mid-viajes`, `mid-cuentas`) con solo los alcances que necesita. Si le falta uno, pídalo al líder del gateway: se agrega al catálogo `clientes.catalogo.json` y se regenera.
* Guarde el `client_secret` como **secreto** de su plataforma (variable de entorno de Azure, secreto de GitHub), nunca en el código.
* Cachee el token y renuévelo ~1 minuto antes de que venza.
