"""Servicio simulado para probar el gateway sin los servicios reales. SOLO desarrollo y pruebas.

Se comporta como un servicio del clúster detrás del gateway: exige su cabecera X-Gateway-Secret (401 si falta o es
incorrecta) y responde con un JSON que describe exactamente lo que recibió, para comprobar que el gateway reenvía
lo correcto: qué ruta, qué método, qué consulta, qué cabeceras y qué cuerpo.

Variables: NOMBRE (cuál servicio es) y SECRETO (el valor de X-Gateway-Secret que acepta).
Ids especiales para probar el paso de errores: «conflicto» responde 409 y «inexistente» responde 404.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NOMBRE = os.environ.get("NOMBRE", "servicio")
SECRETO = os.environ.get("SECRETO", "")


class Manejador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cuerpo(self) -> str:
        if (self.headers.get("transfer-encoding") or "").lower() == "chunked":
            partes = b""
            while True:
                tam = int(self.rfile.readline().strip() or b"0", 16)
                if tam == 0:
                    self.rfile.readline()
                    break
                partes += self.rfile.read(tam)
                self.rfile.readline()
            return partes.decode()
        n = int(self.headers.get("content-length") or 0)
        return self.rfile.read(n).decode() if n else ""

    def _responder(self, estado: int, datos: dict, extra: dict | None = None) -> None:
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(estado)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(cuerpo)

    def _atender(self) -> None:
        cuerpo = self._cuerpo()
        if self.path == "/health":
            return self._responder(200, {"estado": "ok"})
        if self.headers.get("X-Gateway-Secret") != SECRETO:
            return self._responder(401, {"codigo": "gateway_no_autorizado", "mensaje": "Falta la cabecera secreta.", "detalle": {}})
        if "/conflicto" in self.path:
            return self._responder(409, {"codigo": "transicion_invalida", "mensaje": "Conflicto simulado.", "detalle": {}})
        if "/inexistente" in self.path:
            return self._responder(404, {"codigo": "no_encontrado", "mensaje": "No existe (simulado).", "detalle": {}})
        self._responder(
            200,
            {
                "servicio": NOMBRE,
                "metodo": self.command,
                "ruta": self.path.split("?")[0],
                "consulta": self.path.split("?", 1)[1] if "?" in self.path else "",
                "cabeceras": {k.lower(): v for k, v in self.headers.items()},
                "cuerpo": cuerpo,
            },
            {"X-Servicio": NOMBRE},
        )

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _atender

    def log_message(self, *args) -> None:  # silencioso
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Manejador).serve_forever()
