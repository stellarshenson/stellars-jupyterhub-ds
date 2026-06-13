# This makefile helps build, push and run the jupyterhub

#################################################################################
# GLOBALS                                                                       #
#################################################################################
.DEFAULT_GOAL := help
.PHONY: help preflight build build_verbose rebuild rebuild_increment_version _rebuild_impl push pull start stop clean increment_version maybe_increment_version tag logs test test-functional test-functional-env test-functional-clean

# ── Preflight: tools, services, and files required end-to-end ──
# Covers versioning (python3 + tomllib + awk + sed), build (docker), push (git),
# start/stop/logs (docker compose plugin + reachable daemon), and the project
# files those targets read. Run `make preflight` before build/push to catch
# missing prerequisites early; failures print OK / MISSING per item and exit 1.
PREFLIGHT_TOOLS := python3 awk sed bash docker git
PREFLIGHT_FILES := pyproject.toml compose.yml services/jupyterhub/Dockerfile.jupyterhub

# ── Project metadata extracted from pyproject.toml ──
# Parse-time extraction: the empty-string + $(error) idiom fails loud if any
# of the required tools or pyproject.toml are missing, instead of silently
# producing an empty VERSION/TAG that would show up later as a broken docker tag.
PROJECT_META := $(shell python3 -c 'import tomllib;d=tomllib.load(open("pyproject.toml","rb"));print(d["project"]["name"], d["project"]["version"], d["tool"]["stellars"]["cuda"], d["tool"]["stellars"]["jupyterhub"])' 2>/dev/null)
ifeq ($(PROJECT_META),)
$(error pyproject.toml read failed - need python3 >=3.11 with stdlib tomllib, plus a valid pyproject.toml at repo root)
endif
PROJECT_NAME    := $(word 1,$(PROJECT_META))
PROJECT_VERSION := $(word 2,$(PROJECT_META))
CUDA_VERSION    := $(word 3,$(PROJECT_META))
JH_VERSION      := $(word 4,$(PROJECT_META))
VERSION         := $(PROJECT_VERSION)_cuda-$(CUDA_VERSION)_jh-$(JH_VERSION)
TAG             := $(VERSION)

## verify tools, python tomllib, docker compose, docker daemon, and key project files
preflight:
	@rc=0; \
	printf "%-28s %s\n" "Tool" "Status"; \
	printf "%-28s %s\n" "----" "------"; \
	for t in $(PREFLIGHT_TOOLS); do \
		if p=$$(command -v $$t 2>/dev/null); then \
			printf "  %-26s OK   %s\n" "$$t" "$$p"; \
		else \
			printf "  %-26s MISSING\n" "$$t"; rc=1; \
		fi; \
	done; \
	if python3 -c 'import tomllib' 2>/dev/null; then \
		printf "  %-26s OK   %s\n" "python3 stdlib tomllib" "$$(python3 --version)"; \
	else \
		printf "  %-26s MISSING (need python3 >=3.11)\n" "python3 stdlib tomllib"; rc=1; \
	fi; \
	if v=$$(docker compose version --short 2>/dev/null); then \
		printf "  %-26s OK   v%s\n" "docker compose plugin" "$$v"; \
	else \
		printf "  %-26s MISSING (install docker-compose-plugin)\n" "docker compose plugin"; rc=1; \
	fi; \
	if docker info >/dev/null 2>&1; then \
		printf "  %-26s OK   reachable\n" "docker daemon"; \
	else \
		printf "  %-26s MISSING (daemon not reachable)\n" "docker daemon"; rc=1; \
	fi; \
	echo; \
	printf "%-28s %s\n" "File" "Status"; \
	printf "%-28s %s\n" "----" "------"; \
	for f in $(PREFLIGHT_FILES); do \
		if [ -f "$$f" ]; then \
			printf "  %-26s OK\n" "$$f"; \
		else \
			printf "  %-26s MISSING\n" "$$f"; rc=1; \
		fi; \
	done; \
	echo; \
	if [ $$rc -eq 0 ]; then \
		printf '%s%sPreflight passed%s - all required tools, services, and files are available.\n\n' "$(GREEN)" "$(BOLD)" "$(RESET)"; \
	else \
		printf '%s%sPreflight FAILED%s - install / start the missing items above.\n\n' "$(RED)" "$(BOLD)" "$(RESET)"; \
	fi; \
	exit $$rc

# ── Terminal colours (used for status banners; degrade to empty on `dumb` TERM) ──
CYAN  := $(shell tput setaf 6 2>/dev/null)
GREEN := $(shell tput setaf 2 2>/dev/null)
RED   := $(shell tput setaf 1 2>/dev/null)
BOLD  := $(shell tput bold   2>/dev/null)
RESET := $(shell tput sgr0   2>/dev/null)

# Reads pyproject.toml at recipe-shell time so the printed tag reflects the
# file as-of right now (post-bump if maybe_increment_version ran in this
# invocation). Shared by the build/push success banners below.
RUNTIME_TAG_PYTHON_CMD := python3 -c 'import tomllib;d=tomllib.load(open("pyproject.toml","rb"));print(d["project"]["version"]+"_cuda-"+d["tool"]["stellars"]["cuda"]+"_jh-"+d["tool"]["stellars"]["jupyterhub"])'

# Reusable green/bold success banners. Trailing blank line separates the
# banner from any subsequent shell output for visual breathing room.
PRINT_BUILD_SUCCESS = @V=$$($(RUNTIME_TAG_PYTHON_CMD)); printf '\n%s%sBuild successful: stellars/stellars-jupyterhub-ds:%s%s\n\n' "$(GREEN)" "$(BOLD)" "$$V" "$(RESET)"
PRINT_PUSH_SUCCESS  = @V=$$($(RUNTIME_TAG_PYTHON_CMD)); printf '\n%s%sPush successful:  stellars/stellars-jupyterhub-ds:%s (also :latest)%s\n\n' "$(GREEN)" "$(BOLD)" "$$V" "$(RESET)"

# Build options (e.g., BUILD_OPTS='--no-cache' or BUILD_OPTS='--no-version-increment')
BUILD_OPTS ?=

# Check if --no-version-increment is in BUILD_OPTS
NO_VERSION_INCREMENT := $(findstring --no-version-increment,$(BUILD_OPTS))

# Filter out --no-version-increment from opts passed to docker
DOCKER_BUILD_OPTS := $(filter-out --no-version-increment,$(BUILD_OPTS))

# Conditional version increment target
maybe_increment_version: preflight
ifeq ($(NO_VERSION_INCREMENT),)
	@$(MAKE) increment_version
else
	@printf '%s%sVersion unchanged: %s (--no-version-increment)%s\n' "$(CYAN)" "$(BOLD)" "$(PROJECT_VERSION)" "$(RESET)"
endif

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## increment patch version in pyproject.toml
increment_version: preflight
	@CURRENT='$(PROJECT_VERSION)'; \
	NEW=$$(echo "$$CURRENT" | awk 'BEGIN{FS=OFS="."} {$$NF += 1; print}'); \
	printf '%s%sVersion bumped: %s -> %s%s\n' "$(CYAN)" "$(BOLD)" "$$CURRENT" "$$NEW" "$(RESET)"; \
	sed -i 's/^version = "'"$$CURRENT"'"$$/version = "'"$$NEW"'"/' pyproject.toml

## build docker containers (BUILD_OPTS='--no-version-increment --no-cache')
build: preflight maybe_increment_version
	@cd ./scripts && ./build.sh $(DOCKER_BUILD_OPTS)
	$(PRINT_BUILD_SUCCESS)

## build with verbose output (BUILD_OPTS='--no-version-increment --no-cache')
build_verbose: preflight maybe_increment_version
	@cd ./scripts && ./build_verbose.sh $(DOCKER_BUILD_OPTS)
	$(PRINT_BUILD_SUCCESS)

## rebuild 'target' stage without bumping version (default; safe for dev iteration)
rebuild: preflight _rebuild_impl

## rebuild 'target' stage and bump patch version
rebuild_increment_version: preflight maybe_increment_version _rebuild_impl

# Internal: actual `target` stage rebuild. Reads CURRENT_VERSION at recipe time
# so a preceding maybe_increment_version bump (when invoked via
# rebuild_increment_version) is reflected in the docker tag.
_rebuild_impl:
	$(eval CURRENT_VERSION := $(shell python3 -c 'import tomllib;d=tomllib.load(open("pyproject.toml","rb"));print(d["project"]["version"]+"_cuda-"+d["tool"]["stellars"]["cuda"]+"_jh-"+d["tool"]["stellars"]["jupyterhub"])'))
	@echo "Rebuilding 'target' stage (version: $(CURRENT_VERSION))..."
	@docker build \
		--network=host \
		--platform linux/amd64 \
		--target target \
		--build-arg VERSION=$(CURRENT_VERSION) \
		--build-arg CACHEBUST=$$(date +%s) \
		$(DOCKER_BUILD_OPTS) \
		--tag stellars/stellars-jupyterhub-ds:latest \
		-f services/jupyterhub/Dockerfile.jupyterhub \
		.
	$(PRINT_BUILD_SUCCESS)

## pull docker image from dockerhub
pull: preflight
	docker pull stellars/stellars-jupyterhub-ds:latest

## push docker containers to repo
push: preflight tag
	docker push stellars/stellars-jupyterhub-ds:latest
	docker push stellars/stellars-jupyterhub-ds:$(TAG)
	$(PRINT_PUSH_SUCCESS)

tag: preflight
	@if git tag -l | grep -q "^$(TAG)$$"; then \
		echo "Git tag $(TAG) already exists, skipping tagging"; \
	else \
		echo "Creating git tag: $(TAG)"; \
		git tag $(TAG); \
	fi
	@echo "Creating docker tag: $(TAG)"
	@docker tag stellars/stellars-jupyterhub-ds:latest stellars/stellars-jupyterhub-ds:$(TAG)

## start jupyterhub (fg)
start: preflight
	@./start.sh

## stop and remove containers
stop: preflight
	@echo 'stopping and removing containers'
	@if [ -f './compose_override.yml' ]; then \
		docker compose --env-file .env -f compose.yml -f compose_override.yml down; \
	else \
		docker compose --env-file .env -f compose.yml down; \
	fi

## follow container logs to docker.log
logs: preflight
	@echo 'following container logs to docker.log (press Ctrl+C to stop)'
	@if [ -f './compose_override.yml' ]; then \
		docker compose --env-file .env -f compose.yml -f compose_override.yml logs -f 2>&1 | tee docker.log; \
	else \
		docker compose --env-file .env -f compose.yml logs -f 2>&1 | tee docker.log; \
	fi

# ── Functional test harness (LOCAL ONLY - isolated throwaway deployment) ──
FUNCTEST_PROJECT := stellars-functest
FUNCTEST_COMPOSE := tests/functional/compose.functional.yml
FUNCTEST_ENV_COMPOSE := tests/functional/compose.functional-env.yml
FUNCTEST_IMAGES  := quay.io/jupyterhub/singleuser:latest mcr.microsoft.com/playwright/python:v1.49.0-noble

## run the python unit test suites locally (stellars-hub-services + stellars-docker-proxy)
test:
	@cd services/jupyterhub/stellars-hub-services && python3 -m pytest tests/ -q
	@cd services/jupyterhub/stellars-docker-proxy && python3 -m pytest tests/ -q

## run the functional UI/scenario harness in an isolated throwaway deployment, then clean containers/network/volumes (LOCAL ONLY; pulled images kept to avoid re-pull - REMOVE_IMAGES=1 to also remove them)
test-functional:
	@if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then gpumode=2; else gpumode=0; fi; \
	echo "[functional] booting isolated deployment ($(FUNCTEST_PROJECT)) [GPU auto-detect mode=$$gpumode]..."; \
	start=$$(date +%s); \
	FUNCTEST_GPU_ENABLED=$$gpumode docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) up --abort-on-container-exit --exit-code-from tests; \
	rc=$$?; \
	$(MAKE) --no-print-directory test-functional-clean; \
	end=$$(date +%s); \
	echo "[functional] total time (boot + tests + teardown): $$((end-start))s; test-suite total is the pytest 'in Xs' line above"; \
	exit $$rc

## run the functional harness in auth mode 2 (signup disabled + env-password admin; restart-to-provision on a fresh DB), then clean up
test-functional-env:
	@echo "[functional/env] booting hub (first boot creates the DB + tables)..."
	@docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) -f $(FUNCTEST_ENV_COMPOSE) up -d --wait jupyterhub
	@echo "[functional/env] restarting hub to provision the env-password admin..."
	@docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) -f $(FUNCTEST_ENV_COMPOSE) restart jupyterhub
	@docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) -f $(FUNCTEST_ENV_COMPOSE) up -d --wait jupyterhub
	@start=$$(date +%s); \
	docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) -f $(FUNCTEST_ENV_COMPOSE) run --rm tests; \
	rc=$$?; \
	$(MAKE) --no-print-directory test-functional-clean; \
	end=$$(date +%s); \
	echo "[functional/env] total time: $$((end-start))s"; \
	exit $$rc

## remove the functional-test harness - containers, spawned labs, network, volumes (idempotent; pulled images kept - REMOVE_IMAGES=1 also removes them)
test-functional-clean:
	@echo "[functional] cleaning harness (containers, network, volumes)..."
	@docker compose -p $(FUNCTEST_PROJECT) -f $(FUNCTEST_COMPOSE) down -v --remove-orphans >/dev/null 2>&1 || true
	@docker ps -aq --filter "label=com.docker.compose.project=$(FUNCTEST_PROJECT)" | xargs -r docker rm -f >/dev/null 2>&1 || true
	@docker volume ls -q --filter "name=^$(FUNCTEST_PROJECT)_" | xargs -r docker volume rm >/dev/null 2>&1 || true
	@docker volume rm jupyterlab-functestadmin_home jupyterlab-functestadmin_workspace jupyterlab-functestadmin_cache >/dev/null 2>&1 || true
	@docker network rm $(FUNCTEST_PROJECT)_network >/dev/null 2>&1 || true
ifdef REMOVE_IMAGES
	@docker rmi $(FUNCTEST_IMAGES) >/dev/null 2>&1 || true
endif
	@echo "[functional] cleanup complete (pulled images kept)"

## clean orphaned containers
clean: preflight
	@echo 'removing dangling and unused images, containers, nets and volumes'
	@docker compose --env-file .env -f compose.yml down --remove-orphans
	@yes | docker image prune
	@yes | docker network prune
	@echo ""

## prints the list of available commands
help:
	@echo ""
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' 


# EOF
