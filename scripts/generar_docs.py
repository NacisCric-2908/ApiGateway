"""Genera la documentación que depende del catálogo, para que nunca se desactualice:

    docs/rutas.md                                   tabla de rutas, alcances y clientes
    docs/rodar-gateway.postman_collection.json      colección de Postman con una petición por ruta

Fuentes: gateway/settings/rutas.json, gateway/settings/servicios.json y clientes.catalogo.json.
Se ejecuta con `make docs` (en Docker). Solo usa la biblioteca estándar.
"""

import json
import re
from collections import OrderedDict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
rutas = json.loads((RAIZ / "gateway/settings/rutas.json").read_text(encoding="utf-8"))["lista"]
servicios = json.loads((RAIZ / "gateway/settings/servicios.json").read_text(encoding="utf-8"))
clientes = json.loads((RAIZ / "clientes.catalogo.json").read_text(encoding="utf-8"))

EJEMPLOS = {  # valores de ejemplo para los parámetros de ruta y de consulta (coinciden con los datos semilla de Flota)
    "vehiculo_id": "veh-0001", "codigo": "11", "viaje_id": "via-0001", "zona_id": "zona-0001",
    "usuario_id": "usr-0001", "lat": "4.7110", "lng": "-74.0721", "tipo": "scooter", "radioMetros": "500",
    "estado": "disponible", "pagina": "1", "tamano": "20", "mes": "2026-11",
}
CUERPOS = {  # cuerpo de ejemplo de las peticiones que lo llevan (solo orientativo)
    ("POST", "/viajes/iniciar"): {"usuarioId": "usr-0001", "vehiculoId": "veh-0001", "origen": {"lat": 4.711, "lng": -74.0721}},
    ("POST", "/viajes/{viaje_id}/finalizar"): {"destino": {"lat": 4.7125, "lng": -74.07}},
    ("PATCH", "/flota/vehiculos/{vehiculo_id}/estado"): {"estado": "reservado"},
}


def limpiar(d: str) -> str:
    """Quita de la descripción las notas internas sobre el prefijo (importan al gateway, no a quien lo consume)."""
    return re.sub(r"\s*\((?:se QUITA|NO se quita)[^)]*\)", "", d)


def sustituir(ruta: str) -> str:
    for k, v in EJEMPLOS.items():
        ruta = ruta.replace("{" + k + "}", v)
    return ruta


def md() -> str:
    L = ["# Rutas, alcances y clientes del gateway", "",
         "> Generado por `make docs` desde `gateway/settings/rutas.json` y `clientes.catalogo.json`. **No editar a mano.**", "",
         "Todas las rutas (salvo `/token`, `/.well-known/jwks.json` y `/health`) exigen `Authorization: Bearer <token>` con el "
         "alcance indicado. Ver [consumo.md](consumo.md) para pedir el token.", ""]
    por_servicio: OrderedDict[str, list] = OrderedDict()
    for r in rutas:
        por_servicio.setdefault(r["servicio"], []).append(r)
    for s, lista in por_servicio.items():
        L += [f"## {servicios[s]['descripcion']}", "", "| Método | Ruta pública | Alcance | Qué hace | Parámetros de consulta |", "| --- | --- | --- | --- | --- |"]
        for r in lista:
            q = ", ".join(f"`{x}`" for x in r.get("query", [])) or "—"
            L.append(f"| {r['metodo']} | `{r['publica']}` | `{' '.join(r['alcances'])}` | {limpiar(r['descripcion'])} | {q} |")
        L.append("")
    todos = sorted({a for r in rutas for a in r["alcances"]})
    L += [f"## Alcances ({len(todos)})", "", "| Alcance | Rutas que habilita |", "| --- | --- |"]
    for a in todos:
        L.append(f"| `{a}` | {', '.join(f'{r['metodo']} `{r['publica']}`' for r in rutas if a in r['alcances'])} |")
    L += ["", "## Clientes (cuenta de servicio de cada quien)", "", "| `client_id` | Para qué | Alcances |", "| --- | --- | --- |"]
    for c in clientes:
        L.append(f"| `{c['client_id']}` | {c['descripcion']} | {' '.join(f'`{a}`' for a in c['alcances'])} |")
    L += ["", "Las contraseñas (`client_secret`) **no están en el repositorio**: las entrega el líder del gateway por un canal seguro.", ""]
    return "\n".join(L)


def postman() -> dict:
    def peticion(r: dict) -> dict:
        ruta = sustituir(r["publica"])
        item = {
            "name": f"{r['metodo']} {r['publica']}  ({limpiar(r['descripcion'])})",
            "request": {
                "method": r["metodo"],
                "header": [{"key": "Authorization", "value": "Bearer {{token}}"}],
                "url": {"raw": "{{baseUrl}}" + ruta, "host": ["{{baseUrl}}"], "path": ruta.strip("/").split("/")},
            },
        }
        if r.get("query"):
            consulta = [{"key": k, "value": EJEMPLOS[k], "disabled": k not in ("lat", "lng")} for k in r["query"] if k in EJEMPLOS]
            item["request"]["url"]["query"] = consulta
        cuerpo = CUERPOS.get((r["metodo"], r["publica"]))
        if cuerpo:
            item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
            item["request"]["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, indent=2, ensure_ascii=False)}
        return item

    carpetas: OrderedDict[str, list] = OrderedDict()
    for r in rutas:
        carpetas.setdefault(servicios[r["servicio"]]["descripcion"], []).append(peticion(r))
    token = {
        "name": "Pedir token (ejecute esta primero)",
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
            "const r = pm.response.json();",
            "if (r.access_token) { pm.collectionVariables.set('token', r.access_token); }",
            "pm.test('token emitido', () => pm.expect(r.access_token).to.be.a('string'));"]}}],
        "request": {
            "method": "POST", "header": [],
            "body": {"mode": "urlencoded", "urlencoded": [
                {"key": "grant_type", "value": "client_credentials"},
                {"key": "client_id", "value": "{{clientId}}"},
                {"key": "client_secret", "value": "{{clientSecret}}"},
                {"key": "scope", "value": "", "disabled": True, "description": "Opcional: un subconjunto de sus alcances, separados por espacio"}]},
            "url": {"raw": "{{baseUrl}}/token", "host": ["{{baseUrl}}"], "path": ["token"]},
        },
    }
    return {
        "info": {"name": "Gateway Rodar", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                 "description": "Generada por make docs desde rutas.json. Ponga baseUrl, clientId y clientSecret y ejecute primero «Pedir token»."},
        "variable": [{"key": "baseUrl", "value": "http://localhost:8080"}, {"key": "clientId", "value": "administrador"},
                     {"key": "clientSecret", "value": ""}, {"key": "token", "value": ""}],
        "item": [token] + [{"name": n, "item": items} for n, items in carpetas.items()],
    }


(RAIZ / "docs").mkdir(exist_ok=True)
(RAIZ / "docs/rutas.md").write_text(md(), encoding="utf-8")
(RAIZ / "docs/rodar-gateway.postman_collection.json").write_text(
    json.dumps(postman(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"docs/rutas.md y la colección de Postman generados ({len(rutas)} rutas, {len(clientes)} clientes)")
