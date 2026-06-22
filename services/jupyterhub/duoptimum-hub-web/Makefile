# Duoptimum Hub web - self-contained package: React UI + JupyterHub integration.
# The UI is built with vite; `make assets` stages the build into the Python
# package and `make wheel` produces the installable wheel the hub image
# pip-installs (UI bundle included). Use these targets, not npm/python directly.
.PHONY: install dev build build-live build-hub assets wheel preview lint typecheck clean

install:        ## install JS deps
	npm install

dev:            ## start the Vite dev server (needs a reachable hub)
	npm run dev

build:          ## typecheck + production build to dist/
	npm run build

build-live:     ## build dist/ for the live hub at /portal (legacy same-origin build)
	npm run build:live

build-hub:      ## build dist/ for the hub-served portal (base=/hub/portal/, live)
	npm run build:hub

assets: build-hub  ## stage the built UI bundle into the Python package
	rm -rf duoptimum_hub_web/static
	mkdir -p duoptimum_hub_web/static
	cp -R dist/. duoptimum_hub_web/static/
	rm -f duoptimum_hub_web/static/index.html

wheel: assets   ## build the installable wheel (UI bundle inside)
	python -m build --wheel --outdir dist-wheel .

preview:        ## serve the production build locally
	npm run preview

lint:           ## eslint
	npm run lint

typecheck:      ## tsc --noEmit
	npm run typecheck

clean:          ## remove node_modules, builds, wheel output
	rm -rf node_modules dist dist-wheel duoptimum_hub_web/static build *.egg-info
