# Operación del gateway (para el líder y quien lo mantiene)

## Cómo está hecho

```
cliente ──► KrakenD (gateway) ──► servicio (CRUD o MID de cualquier grupo)
              │   ▲
              │   └── JWKS (llaves públicas) ── generadas junto con la llave privada
              └──► servicio de tokens (POST /token)  ← único que tiene la llave privada
```

* **KrakenD 3 (edición comunitaria)**, configurado con plantillas (*Flexible Config*): `gateway/krakend.tmpl` + `gateway/settings/*.json`. **No hay que editar la plantilla para agregar una ruta, un servicio o cambiar un límite**: solo los JSON.
* **Servicio de tokens** propio (FastAPI, `tokens/`): OAuth2 *client credentials*, JWT RS256. KrakenD Community no emite tokens, y un proveedor externo (Keycloak, Auth0, Entra ID) añadiría costo o complejidad que el proyecto no necesita. Como el token es un JWT estándar, **se podría cambiar por uno de esos sin tocar el gateway**: solo cambian el JWKS, el emisor y la audiencia.
* **Local y Azure son lo mismo.** La misma imagen corre en ambos; lo único que cambia son las variables de entorno. Un token emitido por el servicio de tokens de Azure lo valida el KrakenD de Azure con las llaves públicas de Azure, igual que en local.

## Tareas frecuentes

### Agregar un cliente nuevo (una cuenta para un equipo)

1. Agréguelo en `clientes.catalogo.json` (`client_id`, `descripcion`, `alcances`). Los alcances válidos son los de [rutas.md](rutas.md).
2. `make docs` (actualiza la documentación).
3. Para generar su secreto sin tocar los demás: `make cliente ID=mid-nuevo ALCANCES=zonas:leer,viajes:leer`. Imprime el secreto (**se muestra una sola vez**) y la entrada con su hash.
4. Agregue esa entrada a `CLIENTES_JSON` (el secreto de GitHub del repositorio) y **redespliegue**. Entregue el secreto por un canal seguro.

### Quitar o cambiar los alcances de un cliente

Edite el catálogo, cambie la entrada en `CLIENTES_JSON` y redespliegue. Los tokens ya emitidos conservan sus alcances **hasta que venzan (15 minutos)**.

### Agregar una ruta

Agregue un objeto a `gateway/settings/rutas.json` (`servicio`, `metodo`, `publica`, `destino`, `alcances`, `descripcion`, opcionalmente `query` y `timeout`), ejecute `make docs` y `make test`. La prueba de recorrido completo (`pruebas/`) **genera un caso por cada ruta del catálogo**, así que la nueva queda probada sola.

Cuidado con el prefijo: `publica` y `destino` pueden diferir (el gateway reescribe). El de `/flota/*` se quita, salvo `/flota/alertas`; el de `/viajes/zonas*` se convierte en `/zonas*`; el de `/cuentas/*` se quita; el resto de `/viajes/*` se conserva.

### Conectar los servicios de otro grupo

1. En el repositorio del gateway, defina las **variables** `VIAJES_CRUD_URL`, `VIAJES_MID_URL`, `CUENTAS_CRUD_URL`, `CUENTAS_MID_URL` (**Settings → Secrets and variables → Actions → Variables**), con la URL **completa y con `https://`** de cada servicio.
2. El secreto que el gateway les envía (`VIAJES_CRUD_SECRET`, etc.) ya fue generado por `scripts/03-secretos-produccion.sh`: entréguelo a ese equipo para que lo configure como `GATEWAY_SECRET` de **su** servicio (cabecera `X-Gateway-Secret`).
3. Redespliegue el gateway. Mientras la URL de un servicio no esté definida, sus rutas dan `404` (así se despliega por partes).

### Rotar las llaves de firma

Cambiar la llave privada invalida **todos los tokens vigentes** (como mucho 15 minutos de impacto). Pasos: `make claves` → actualice `JWT_PRIVATE_KEY_B64` y `JWKS_JSON` (secretos de GitHub) → redespliegue. Para no cortar a nadie, se puede publicar primero un `JWKS_JSON` con **las dos llaves** (la vieja y la nueva), esperar 15 minutos y quitar la vieja.

### Cambiar un secreto de servicio (`X-Gateway-Secret`)

Regenere el secreto, actualice el secreto de GitHub **en el repositorio del gateway y en el del servicio**, y redespliegue ambos. Hasta que los dos estén al día, ese servicio responderá `401`.

### Cambiar límites o tiempos

`gateway/settings/limites.json`: peticiones por segundo del endpoint `/token` y globales, por cliente y totales; y el tiempo de espera por defecto (algunas rutas tienen uno propio de 15 s en `rutas.json`).

## Límites conocidos de KrakenD Community

* Un `401`, `403`, `429` o `500` generado por el gateway **no trae cuerpo**; la causa de un `403` o un `429` no se puede expresar en JSON.
* Si el servicio de atrás no responde, KrakenD devuelve `500` (no `503`).
* No admite rutas comodín (`/flota/*`): por eso las rutas se enumeran en `rutas.json`.
* El límite de peticiones se cuenta **por réplica**: con 2 réplicas el efectivo es el doble.
* Los tokens **no se pueden revocar** antes de vencer (15 minutos); se acorta con `TOKEN_TTL_S` si hace falta.

## Registro y diagnóstico

* Local: `make logs`. Azure: `az containerapp logs show -n rodar-gateway -g rg-rodar --follow` o el portal (Log Analytics).
* El gateway escribe cada petición en JSON (método, ruta, estado, duración). **Nunca registra el token ni las cabeceras secretas.**
* El gateway no arranca si falta `TOKENS_URL`, `JWKS_JSON` o hay una URL sin su secreto: el mensaje del primer error dice cuál.
