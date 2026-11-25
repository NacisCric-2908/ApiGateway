# Atajos. Todo corre dentro de Docker: no hace falta instalar KrakenD, Python ni uv.
.PHONY: setup up down logs test test-unidad test-e2e cliente claves

setup:    ## Genera .env (llaves y secretos) y credenciales-locales.json. No sobrescribe si ya existen
	@if [ -f .env ]; then echo ".env ya existe: no se toca (use 'make setup-forzar' para regenerar todo)"; else \
	docker compose run --rm --no-deps --user $$(id -u):$$(id -g) -v $(CURDIR):/salida tokens \
	  python -m app.cli inicializar --catalogo /salida/clientes.catalogo.json \
	  --salida-env /salida/.env --salida-credenciales /salida/credenciales-locales.json; fi

setup-forzar: ## Regenera .env y las credenciales (invalida los tokens y secretos anteriores)
	docker compose run --rm --no-deps --user $$(id -u):$$(id -g) -v $(CURDIR):/salida tokens \
	  python -m app.cli inicializar --catalogo /salida/clientes.catalogo.json \
	  --salida-env /salida/.env --salida-credenciales /salida/credenciales-locales.json --forzar

up: setup ## Levanta tokens + gateway + los seis servicios simulados en http://localhost:8080
	docker compose --profile simulado up -d --build

down:     ## Detiene todo
	docker compose --profile simulado --profile test down

logs:
	docker compose logs -f gateway tokens

test: test-unidad test-e2e ## Todas las pruebas

test-unidad: ## Pruebas del servicio de tokens
	docker compose --profile test-unit run --rm --build tokens-pruebas

test-e2e: setup ## Pruebas de extremo a extremo contra el gateway real y servicios simulados
	docker compose --profile test run --rm --build pruebas; code=$$?; docker compose --profile test down >/dev/null 2>&1; exit $$code

cliente:  ## Crea un cliente nuevo: make cliente ID=mid-nuevo ALCANCES=zonas:leer,viajes:leer
	docker compose run --rm --no-deps tokens python -m app.cli cliente $(ID) --alcances $(ALCANCES)

claves:   ## Genera un par de llaves nuevo (para rotarlas)
	docker compose run --rm --no-deps tokens python -m app.cli claves
