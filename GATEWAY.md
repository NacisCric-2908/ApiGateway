# Gateway del clúster Rodar

> Documento de equipo. Complete los campos marcados con _pendiente_.

| | |
| --- | --- |
| **Líder del gateway** | _pendiente: nombre y contacto_ |
| **Integrantes** | _pendiente_ |
| **URL pública (Azure)** | _pendiente: la imprime el primer despliegue_ |
| **Entregar credenciales a** | _pendiente: una persona por equipo (líder del MID)_ |

## Qué es y por qué se hizo así

Es la única puerta de entrada de todas las APIs de Rodar: autentica con tokens, comprueba que cada cuenta tenga el alcance de la ruta, limita las peticiones y reenvía al servicio correcto agregando el secreto que ese servicio exige.

| Decisión | Razón |
| --- | --- |
| **KrakenD** (lo sugerido por el profesor) | Se configura con archivos, no con código; corre igual en local y en Azure |
| **Servicio de tokens propio** (FastAPI) | KrakenD Community valida tokens pero no los emite. Es pequeño (30 pruebas) y estándar (OAuth2 + JWT RS256), reemplazable por Keycloak/Entra ID sin tocar el gateway |
| **Rutas enumeradas** en `rutas.json` | KrakenD Community no admite comodines; además así cada ruta lleva su alcance y se prueba sola |
| **Contenedores en Azure Container Apps** | Escalan a cero (cuestan solo si se usan), HTTPS incluido |
| Los servicios **no son públicos** | Solo se llega a ellos por el gateway (más el MID→CRUD interno) |

## Cómo se usa

* Quien **consume** las APIs: [docs/consumo.md](docs/consumo.md) y la colección de Postman.
* Rutas, alcances y clientes: [docs/rutas.md](docs/rutas.md).
* Quien **mantiene** el gateway: [docs/operacion.md](docs/operacion.md).
* Despliegue: [docs/despliegue-azure.md](docs/despliegue-azure.md).

## Responsabilidades

| Quién | Qué |
| --- | --- |
| Líder del gateway | Entrega credenciales (`client_id` y `client_secret`) a cada equipo; mantiene `clientes.catalogo.json`; publica la URL |
| Cada equipo | Configura en SU servicio el `GATEWAY_SECRET` que recibe, y conecta su URL (variable del repositorio del gateway) cuando despliega |
| Cada MID | Pide su token al gateway y llama a otros grupos **solo por el gateway** |
