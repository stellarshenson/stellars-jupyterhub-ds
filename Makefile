# This makefile helps build, push and run the jupyterhub

#################################################################################
# GLOBALS                                                                       #
#################################################################################
.DEFAULT_GOAL := help
.PHONY: help build push start stop clean increment_version maybe_increment_version tag logs

# Include project configuration
include project.env

# Use VERSION from project.env as TAG (strip quotes)
TAG := $(subst ",,$(VERSION))

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

## increment patch version in project.env
increment_version:
	@awk -F= '/^VERSION=/ { \
		gsub(/"/, "", $$2); \
		match($$2, /^([0-9]+\.[0-9]+\.)([0-9]+)(_.*$$)/, parts); \
		new_patch = parts[2] + 1; \
		new_version = parts[1] new_patch parts[3]; \
		print "VERSION=\"" new_version "\""; \
		print "Current version: " $$2 > "/dev/stderr"; \
		print "New version: " new_version > "/dev/stderr"; \
		next; \
	} \
	{ print }' project.env > project.env.tmp && mv project.env.tmp project.env

## build docker containers (BUILD_OPTS='--no-version-increment --no-cache')
build: maybe_increment_version
	@cd ./scripts && ./build.sh $(DOCKER_BUILD_OPTS)

## build with verbose output (BUILD_OPTS='--no-version-increment --no-cache')
build_verbose: maybe_increment_version
	@cd ./scripts && ./build_verbose.sh $(DOCKER_BUILD_OPTS)

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
		echo "Creating docker tag: $(TAG)"; \
		docker tag stellars/stellars-jupyterhub-ds:latest stellars/stellars-jupyterhub-ds:$(TAG); \
	fi

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
