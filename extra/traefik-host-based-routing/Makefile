.PHONY: start stop pull logs status

COMPOSE_CMD = docker compose -f stellars-jupyterhub-ds/compose.yml -f compose_override.yml

start:
	$(COMPOSE_CMD) up -d

stop:
	$(COMPOSE_CMD) down

pull:
	git -C stellars-jupyterhub-ds pull origin main

logs:
	$(COMPOSE_CMD) logs -f jupyterhub

status:
	$(COMPOSE_CMD) ps
