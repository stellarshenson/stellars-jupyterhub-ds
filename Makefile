# This makefile helps build, push and run the jupyterhub

#################################################################################
# GLOBALS                                                                       #
#################################################################################
.DEFAULT_GOAL := help
.PHONY: help build rebuild rebuild_no_version_increment push start stop clean increment_version maybe_increment_version check_versioning_deps tag logs

# ── Required tools (versioning + extraction) ──
# python3 (>=3.11 for stdlib tomllib) reads pyproject.toml; awk + sed handle
# the inline version bump. Both are POSIX-standard except for python3 + tomllib.
REQUIRED_TOOLS := python3 awk sed

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

# Recipe-time check: any rule that mutates state (increment, push, tag) depends
# on this so missing tools fail with a clear message before anything runs.
check_versioning_deps:
	@for tool in $(REQUIRED_TOOLS); do \
		command -v $$tool >/dev/null 2>&1 || { echo "ERROR: '$$tool' not in PATH; required by the Makefile's versioning targets"; exit 1; }; \
	done
	@python3 -c 'import tomllib' 2>/dev/null || { echo "ERROR: python3 is too old (need >=3.11 for stdlib tomllib)"; exit 1; }

# Build options (e.g., BUILD_OPTS='--no-cache' or BUILD_OPTS='--no-version-increment')
BUILD_OPTS ?=

# Check if --no-version-increment is in BUILD_OPTS
NO_VERSION_INCREMENT := $(findstring --no-version-increment,$(BUILD_OPTS))

# Filter out --no-version-increment from opts passed to docker
DOCKER_BUILD_OPTS := $(filter-out --no-version-increment,$(BUILD_OPTS))

# Conditional version increment target
maybe_increment_version:
ifeq ($(NO_VERSION_INCREMENT),)
	@$(MAKE) increment_version
else
	@echo "Skipping version increment (--no-version-increment)"
endif

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## increment patch version in pyproject.toml
increment_version: check_versioning_deps
	@CURRENT='$(PROJECT_VERSION)'; \
	NEW=$$(echo "$$CURRENT" | awk -F. '{$$NF += 1; OFS="."; print}'); \
	echo "Version: $$CURRENT -> $$NEW"; \
	sed -i 's/^version = "'"$$CURRENT"'"$$/version = "'"$$NEW"'"/' pyproject.toml

## build docker containers (BUILD_OPTS='--no-version-increment --no-cache')
build: maybe_increment_version
	@cd ./scripts && ./build.sh $(DOCKER_BUILD_OPTS)

## build with verbose output (BUILD_OPTS='--no-version-increment --no-cache')
build_verbose: maybe_increment_version
	@cd ./scripts && ./build_verbose.sh $(DOCKER_BUILD_OPTS)

## rebuild 'target' stage only (uses cached 'builder' stage, no stop/clean)
rebuild: maybe_increment_version
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

## rebuild without bumping the patch version (alias: make rebuild BUILD_OPTS='--no-version-increment')
rebuild_no_version_increment:
	@$(MAKE) rebuild BUILD_OPTS='--no-version-increment $(BUILD_OPTS)'

## pull docker image from dockerhub
pull:
	docker pull stellars/stellars-jupyterhub-ds:latest

## push docker containers to repo
push: tag
	docker push stellars/stellars-jupyterhub-ds:latest
	docker push stellars/stellars-jupyterhub-ds:$(TAG)

tag:
	@if git tag -l | grep -q "^$(TAG)$$"; then \
		echo "Git tag $(TAG) already exists, skipping tagging"; \
	else \
		echo "Creating git tag: $(TAG)"; \
		git tag $(TAG); \
	fi
	@echo "Creating docker tag: $(TAG)"
	@docker tag stellars/stellars-jupyterhub-ds:latest stellars/stellars-jupyterhub-ds:$(TAG)

## start jupyterhub (fg)
start:
	@./start.sh

## stop and remove containers
stop:
	@echo 'stopping and removing containers'
	@if [ -f './compose_override.yml' ]; then \
		docker compose --env-file .env -f compose.yml -f compose_override.yml down; \
	else \
		docker compose --env-file .env -f compose.yml down; \
	fi

## follow container logs to docker.log
logs:
	@echo 'following container logs to docker.log (press Ctrl+C to stop)'
	@if [ -f './compose_override.yml' ]; then \
		docker compose --env-file .env -f compose.yml -f compose_override.yml logs -f 2>&1 | tee docker.log; \
	else \
		docker compose --env-file .env -f compose.yml logs -f 2>&1 | tee docker.log; \
	fi

## clean orphaned containers
clean:
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
