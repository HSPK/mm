# Developer Setup

This section is for contributors.

## Install dependencies

```bash
uv sync
bun install --cwd web
```

## Run checks

```bash
uv run --group dev pre-commit run --all-files
uv run --group dev python -m pytest -q
bun run --cwd web lint
bun run --cwd web build
```

## Run the web app in development

```bash
bun run --cwd web dev
```

In another terminal, run the Python server as needed.

## Sync API types from FastAPI

The web frontend's typed bindings live in `web/src/api/schema.ts` and are
generated from FastAPI's OpenAPI schema. Regenerate after changing routes or
request body models:

```bash
bun run --cwd web gen:api
```

The script invokes `scripts/gen_openapi.py` (which imports the FastAPI app
in-process — no running server required) and feeds the schema into
`openapi-typescript`. Request body types are re-exported from
`web/src/api/types.ts`; response shapes are still hand-written there because
endpoints currently return untyped dicts. Add `response_model=` on a route to
get its response shape into the generated schema automatically.

## Build the iOS / macOS app

The SwiftUI client lives under `ios/`. On macOS with Xcode 15+ installed:

```bash
brew install xcodegen
cd ios
xcodegen generate
open MM.xcodeproj
```

`project.yml` is the source of truth — re-run `xcodegen generate` after every
edit. The same SwiftUI sources build for iPhone, iPad, and Mac targets. See
[ios/README.md](../../ios/README.md) for more.

## Build the documentation site

```bash
uv run --only-group docs mkdocs serve
uv run --only-group docs mkdocs build --strict
```

The published GitHub Pages site is built from the Markdown files under `docs/`.

## Release notes

The release workflow builds the frontend, verifies the bundled web assets, builds
the Python distributions, and publishes to PyPI from GitHub Releases.
