# This makefile helps build, push and run the jupyterhub

#################################################################################
# GLOBALS                                                                       #
#################################################################################
.DEFAULT_GOAL := help
.PHONY: help preflight build build_verbose rebuild rebuild_increment_version _rebuild_impl push pull start stop clean increment_version maybe_increment_version tag logs test test-functional

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

# ── Images ──
# The GPU-info sidecar is a compose service (gpuinfo-nvidia, gated behind the
# `gpuinfo` profile). build AND rebuild build it via compose by service name (the
# Dockerfile path lives in compose.yml, not duplicated here); push/pull handle it
# by image tag alongside the hub below.
HUB_IMAGE          := stellars/duoptimum-hub
GPUINFO_IMAGE      := stellars/duoptimum-gpuinfo-nvidia

# ── Version sync ──
# Every in-repo package baked into the hub image tracks the platform version -
# increment_version sets them all to the bumped root version in lockstep so the
# wheels + npm package never drift from the release tag. The gpuinfo-nvidia
# sidecar is a SEPARATE image with its own version and is intentionally excluded.
DUOPTIMUM_PYPROJECT       := services/jupyterhub/duoptimum-hub-web/pyproject.toml
DUOPTIMUM_PACKAGE_JSON    := services/jupyterhub/duoptimum-hub-web/package.json
DUOPTIMUM_PACKAGE_LOCK    := services/jupyterhub/duoptimum-hub-web/package-lock.json
HUB_SERVICES_PYPROJECT  := services/jupyterhub/duoptimum-hub-services/pyproject.toml
DOCKER_PROXY_PYPROJECT  := services/jupyterhub/duoptimum-docker-proxy/pyproject.toml
# [project] version lines set in lockstep (root + the three packages in the image)
VERSIONED_PYPROJECTS    := pyproject.toml $(DUOPTIMUM_PYPROJECT) $(HUB_SERVICES_PYPROJECT) $(DOCKER_PROXY_PYPROJECT)

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
# Build banner reports what actually got built, read from the BUILT IMAGE:
# - the UI version line (Duoptimum Hub vX build YYMMDD.hhmm-hash) grepped from the
#   SPA bundle - the same string the portal header shows; __BUILD_ID__ is baked
#   into the JS at vite build time, not an image label
# - the cuda/jh version label + short image id via docker inspect (provenance)
# Falls back to the inspect label, then to a not-found notice.
PRINT_BUILD_SUCCESS = @IMG="$(HUB_IMAGE):latest"; \
	BANNER=$$(docker run --rm --entrypoint sh "$$IMG" -c 'd=$$(python3 -c "import duoptimum_hub_web,os;print(os.path.dirname(duoptimum_hub_web.__file__))" 2>/dev/null); grep -rhoE "Duoptimum Hub v[0-9][^\"]*" "$$d"/static/assets/*.js 2>/dev/null | head -1' 2>/dev/null); \
	LBL=$$(docker inspect --format '{{ index .Config.Labels "version" }}' "$$IMG" 2>/dev/null); \
	IMGID=$$(docker inspect --format '{{ .Id }}' "$$IMG" 2>/dev/null | cut -d: -f2 | cut -c1-12); \
	if [ -n "$$BANNER" ]; then \
		printf '\n%s%s%s%s\n' "$(GREEN)" "$(BOLD)" "$$BANNER" "$(RESET)"; \
		printf '%s  image: %s  (%s, id %s)%s\n\n' "$(GREEN)" "$$IMG" "$${LBL:-?}" "$$IMGID" "$(RESET)"; \
	elif [ -n "$$LBL" ]; then \
		printf '\n%s%sBuild successful: %s  (%s, id %s)%s\n' "$(GREEN)" "$(BOLD)" "$$IMG" "$$LBL" "$$IMGID" "$(RESET)"; \
		printf '%s  (UI banner not readable from the bundle)%s\n\n' "$(GREEN)" "$(RESET)"; \
	else \
		printf '\n%s%sBuild step done, but image %s not found to inspect%s\n\n' "$(RED)" "$(BOLD)" "$$IMG" "$(RESET)"; \
	fi
PRINT_PUSH_SUCCESS  = @V=$$($(RUNTIME_TAG_PYTHON_CMD)); printf '\n%s%sPush successful:  stellars/duoptimum-hub:%s (also :latest)%s\n\n' "$(GREEN)" "$(BOLD)" "$$V" "$(RESET)"

# Build options (e.g., BUILD_OPTS='--no-cache' or BUILD_OPTS='--no-version-increment')
BUILD_OPTS ?=

# Check if --no-version-increment is in BUILD_OPTS
NO_VERSION_INCREMENT := $(findstring --no-version-increment,$(BUILD_OPTS))

# Filter out --no-version-increment from opts passed to docker
DOCKER_BUILD_OPTS := $(filter-out --no-version-increment,$(BUILD_OPTS))

# Conditional version increment target. When bumping is on, increment_version is
# a real prerequisite - deduped with preflight in the SAME make process, so
# preflight runs once. (The old `$(MAKE) increment_version` recipe spawned a
# sub-make that re-ran preflight a second time.)
ifeq ($(NO_VERSION_INCREMENT),)
maybe_increment_version: preflight increment_version
	@:
else
maybe_increment_version: preflight
	@printf '%s%sVersion unchanged: %s (--no-version-increment)%s\n' "$(CYAN)" "$(BOLD)" "$(PROJECT_VERSION)" "$(RESET)"
endif

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## increment patch version in pyproject.toml (propagated to all in-image packages)
# Sets the [project] version absolutely (not a CURRENT-string match) so a drifted
# subpackage is pulled back into lockstep rather than silently skipped.
increment_version: preflight
	@CURRENT='$(PROJECT_VERSION)'; \
	NEW=$$(echo "$$CURRENT" | awk 'BEGIN{FS=OFS="."} {$$NF += 1; print}'); \
	printf '%s%sVersion bumped: %s -> %s (hub + duoptimum-hub-web + hub-services + docker-proxy)%s\n' "$(CYAN)" "$(BOLD)" "$$CURRENT" "$$NEW" "$(RESET)"; \
	for f in $(VERSIONED_PYPROJECTS); do \
		sed -i 's/^version = "[^"]*"$$/version = "'"$$NEW"'"/' "$$f"; \
	done; \
	sed -i 's/"version": "[^"]*"/"version": "'"$$NEW"'"/' $(DUOPTIMUM_PACKAGE_JSON); \
	awk -v v="$$NEW" 'BEGIN{n=0} /"version":/ && n<2 {sub(/"version": "[^"]*"/, "\"version\": \"" v "\""); n++} {print}' $(DUOPTIMUM_PACKAGE_LOCK) > $(DUOPTIMUM_PACKAGE_LOCK).tmp && mv $(DUOPTIMUM_PACKAGE_LOCK).tmp $(DUOPTIMUM_PACKAGE_LOCK)

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
		--tag stellars/duoptimum-hub:latest \
		-f services/jupyterhub/Dockerfile.jupyterhub \
		.
	@echo "Rebuilding GPU-info sidecar ($(GPUINFO_IMAGE):latest)..."
	@DOCKER_DEFAULT_PLATFORM=linux/amd64 COMPOSE_BAKE=false \
		docker compose -f compose.yml --profile gpuinfo build $(DOCKER_BUILD_OPTS) gpuinfo-nvidia
	$(PRINT_BUILD_SUCCESS)

## pull docker images from dockerhub (hub + GPU-info sidecar)
pull: preflight
	docker pull $(HUB_IMAGE):latest
	docker pull $(GPUINFO_IMAGE):latest

## push docker containers to repo (hub + GPU-info sidecar)
push: preflight tag
	docker push $(HUB_IMAGE):latest
	docker push $(HUB_IMAGE):$(TAG)
	docker push $(GPUINFO_IMAGE):latest
	$(PRINT_PUSH_SUCCESS)

tag: preflight
	@if git tag -l | grep -q "^$(TAG)$$"; then \
		echo "Git tag $(TAG) already exists, skipping tagging"; \
	else \
		echo "Creating git tag: $(TAG)"; \
		git tag $(TAG); \
	fi
	@echo "Creating docker tag: $(TAG)"
	@docker tag stellars/duoptimum-hub:latest stellars/duoptimum-hub:$(TAG)

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
# ONE target, ALL regimes. Orchestration (regimes, boot, run, teardown) lives in
# tests/functional/run.sh - kept out of make so the recipe stays a one-liner (a
# multi-line recipe with $(MAKE) in it ALSO runs under `make -n`, silently executing
# the suite). Run a single regime or just clean up with the script directly:
#   tests/functional/run.sh <signup|gpu|env|signup-open|signup-bootstrap|all|clean>

## run the python unit test suites locally (duoptimum-hub-services + duoptimum-docker-proxy)
test:
	@cd services/jupyterhub/duoptimum-hub-services && python3 -m pytest tests/ -q
	@cd services/jupyterhub/duoptimum-docker-proxy && python3 -m pytest tests/ -q

## run the FULL functional UI/scenario harness - every regime (signup, gpu, env, signup-open, signup-bootstrap, traefik), cleaning between each (LOCAL ONLY; single regime/cleanup: tests/functional/run.sh <regime>; PYTEST_ARGS=... selects tests, REMOVE_IMAGES=1 drops pulled images)
test-functional:
	@tests/functional/run.sh all

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
