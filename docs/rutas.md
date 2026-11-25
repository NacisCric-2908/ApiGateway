# Rutas, alcances y clientes del gateway

> Generado por `make docs` desde `gateway/settings/rutas.json` y `clientes.catalogo.json`. **No editar a mano.**

Todas las rutas (salvo `/token`, `/.well-known/jwks.json` y `/health`) exigen `Authorization: Bearer <token>` con el alcance indicado. Ver [consumo.md](consumo.md) para pedir el token.

## CRUD de Flota (vehículos y localidades)

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| GET | `/flota/vehiculos` | `vehiculos:leer` | Listar y buscar vehículos | `tipo`, `estado`, `localidad`, `bateriaMin`, `lat`, `lng`, `radioMetros`, `pagina`, `tamano` |
| POST | `/flota/vehiculos` | `vehiculos:escribir` | Crear un vehículo | — |
| GET | `/flota/vehiculos/{vehiculo_id}` | `vehiculos:leer` | Detalle de un vehículo | — |
| PUT | `/flota/vehiculos/{vehiculo_id}` | `vehiculos:escribir` | Reemplazar un vehículo | — |
| DELETE | `/flota/vehiculos/{vehiculo_id}` | `vehiculos:escribir` | Eliminar un vehículo | — |
| PATCH | `/flota/vehiculos/{vehiculo_id}/estado` | `vehiculos:escribir` | Cambiar el estado (reserva atómica) | — |
| GET | `/flota/vehiculos/{vehiculo_id}/clima` | `vehiculos:leer` | Clima en la ubicación del vehículo | — |
| GET | `/flota/vehiculos/{vehiculo_id}/direccion` | `vehiculos:leer` | Dirección de la ubicación del vehículo | — |
| GET | `/flota/localidades` | `vehiculos:leer` | Las 20 localidades con el conteo de vehículos | — |
| GET | `/flota/localidades/verificar` | `vehiculos:leer` | ¿En qué localidad está un punto? | `lat`, `lng` |
| GET | `/flota/localidades/{codigo}` | `vehiculos:leer` | Una localidad con su geometría | — |

## MID de Flota (recomendaciones y alertas)

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| GET | `/flota/recomendaciones/vehiculo` | `recomendaciones:leer` | Los 3 mejores vehículos cerca de un punto | `lat`, `lng`, `tipo` |
| GET | `/flota/alertas` | `alertas:leer` | Alertas operativas | — |

## CRUD de Viajes y zonas

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| GET | `/viajes` | `viajes:leer` | Listar viajes | `usuarioId`, `estado`, `desde`, `hasta`, `pagina`, `tamano` |
| POST | `/viajes` | `viajes:escribir` | Crear un viaje | — |
| GET | `/viajes/{viaje_id}` | `viajes:leer` | Detalle de un viaje | — |
| PATCH | `/viajes/{viaje_id}` | `viajes:escribir` | Actualizar un viaje | — |
| GET | `/viajes/zonas` | `zonas:leer` | Listar zonas | `tipo` |
| POST | `/viajes/zonas` | `zonas:escribir` | Crear una zona | — |
| GET | `/viajes/zonas/verificar` | `zonas:leer` | ¿En qué zonas cae un punto? (lo usa el MID de Flota) | `lat`, `lng` |
| GET | `/viajes/zonas/{zona_id}` | `zonas:leer` | Detalle de una zona | — |
| PUT | `/viajes/zonas/{zona_id}` | `zonas:escribir` | Reemplazar una zona | — |
| DELETE | `/viajes/zonas/{zona_id}` | `zonas:escribir` | Eliminar una zona | — |

## MID de Viajes y zonas (iniciar y finalizar viajes)

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| POST | `/viajes/iniciar` | `viajes:iniciar` | Iniciar un viaje | — |
| POST | `/viajes/{viaje_id}/finalizar` | `viajes:finalizar` | Finalizar un viaje | — |

## CRUD de Cuentas (usuarios y billetera)

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| GET | `/cuentas/usuarios` | `usuarios:leer` | Listar usuarios | `estado`, `correo`, `pagina`, `tamano` |
| POST | `/cuentas/usuarios` | `usuarios:escribir` | Crear un usuario | — |
| GET | `/cuentas/usuarios/{usuario_id}` | `usuarios:leer` | Detalle de un usuario | — |
| PUT | `/cuentas/usuarios/{usuario_id}` | `usuarios:escribir` | Actualizar un usuario | — |
| DELETE | `/cuentas/usuarios/{usuario_id}` | `usuarios:escribir` | Desactivar un usuario | — |
| GET | `/cuentas/usuarios/{usuario_id}/billetera` | `usuarios:leer` | Saldo de la billetera | — |
| GET | `/cuentas/billeteras/{usuario_id}/movimientos` | `billetera:leer` | Historial de movimientos | `pagina`, `tamano` |
| POST | `/cuentas/billeteras/{usuario_id}/movimientos` | `billetera:escribir` | Registrar una recarga o un débito | — |

## MID de Cuentas (liquidación y resumen)

| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |
| --- | --- | --- | --- | --- |
| POST | `/cuentas/liquidaciones` | `billetera:escribir` | Liquidar un viaje (lo dispara el MID de Viajes) | — |
| GET | `/cuentas/usuarios/{usuario_id}/resumen-gasto` | `resumen:leer` | Resumen de gasto mensual | `mes` |

## Alcances (15)

| Alcance | Rutas que habilita |
| --- | --- |
| `alertas:leer` | GET `/flota/alertas` |
| `billetera:escribir` | POST `/cuentas/billeteras/{usuario_id}/movimientos`, POST `/cuentas/liquidaciones` |
| `billetera:leer` | GET `/cuentas/billeteras/{usuario_id}/movimientos` |
| `recomendaciones:leer` | GET `/flota/recomendaciones/vehiculo` |
| `resumen:leer` | GET `/cuentas/usuarios/{usuario_id}/resumen-gasto` |
| `usuarios:escribir` | POST `/cuentas/usuarios`, PUT `/cuentas/usuarios/{usuario_id}`, DELETE `/cuentas/usuarios/{usuario_id}` |
| `usuarios:leer` | GET `/cuentas/usuarios`, GET `/cuentas/usuarios/{usuario_id}`, GET `/cuentas/usuarios/{usuario_id}/billetera` |
| `vehiculos:escribir` | POST `/flota/vehiculos`, PUT `/flota/vehiculos/{vehiculo_id}`, DELETE `/flota/vehiculos/{vehiculo_id}`, PATCH `/flota/vehiculos/{vehiculo_id}/estado` |
| `vehiculos:leer` | GET `/flota/vehiculos`, GET `/flota/vehiculos/{vehiculo_id}`, GET `/flota/vehiculos/{vehiculo_id}/clima`, GET `/flota/vehiculos/{vehiculo_id}/direccion`, GET `/flota/localidades`, GET `/flota/localidades/verificar`, GET `/flota/localidades/{codigo}` |
| `viajes:escribir` | POST `/viajes`, PATCH `/viajes/{viaje_id}` |
| `viajes:finalizar` | POST `/viajes/{viaje_id}/finalizar` |
| `viajes:iniciar` | POST `/viajes/iniciar` |
| `viajes:leer` | GET `/viajes`, GET `/viajes/{viaje_id}` |
| `zonas:escribir` | POST `/viajes/zonas`, PUT `/viajes/zonas/{zona_id}`, DELETE `/viajes/zonas/{zona_id}` |
| `zonas:leer` | GET `/viajes/zonas`, GET `/viajes/zonas/verificar`, GET `/viajes/zonas/{zona_id}` |

## Clientes (cuenta de servicio de cada quien)

| `client_id` | Para qué | Alcances |
| --- | --- | --- |
| `mid-flota` | MID de Flota: consulta las zonas de Viajes y zonas para recomendar vehículos y generar alertas | `zonas:leer` |
| `mid-viajes` | MID de Viajes y zonas: consulta saldo y cobra en Cuentas; consulta y reserva vehículos en Flota | `usuarios:leer` `billetera:escribir` `vehiculos:leer` `vehiculos:escribir` |
| `mid-cuentas` | MID de Cuentas: consulta viajes y zonas para liquidar | `viajes:leer` `zonas:leer` |
| `cliente-demo` | Cliente de la demostración: lo que haría la aplicación del usuario | `recomendaciones:leer` `alertas:leer` `viajes:iniciar` `viajes:finalizar` `resumen:leer` |
| `administrador` | Administración y pruebas de integración: TODOS los alcances. No usar en una aplicación | `vehiculos:leer` `vehiculos:escribir` `recomendaciones:leer` `alertas:leer` `viajes:leer` `viajes:escribir` `viajes:iniciar` `viajes:finalizar` `zonas:leer` `zonas:escribir` `usuarios:leer` `usuarios:escribir` `billetera:leer` `billetera:escribir` `resumen:leer` |

Las contraseñas (`client_secret`) **no están en el repositorio**: las entrega el líder del gateway por un canal seguro.
