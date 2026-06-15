# Optimum Hub mock-antd - self-contained frontend subproject.
# Use these targets rather than calling npm directly.
.PHONY: install dev build preview lint typecheck clean

install:        ## install deps
	npm install

dev:            ## start the Vite dev server (mock data mode by default)
	npm run dev

build:          ## typecheck + production build to dist/
	npm run build

preview:        ## serve the production build locally
	npm run preview

lint:           ## eslint
	npm run lint

typecheck:      ## tsc --noEmit
	npm run typecheck

clean:          ## remove node_modules and dist
	rm -rf node_modules dist
