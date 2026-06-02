# Developer Setup

This section is for contributors.

## Install dependencies

```bash
uv sync
npm ci --prefix web
```

## Run checks

```bash
uv run --group dev pre-commit run --all-files
uv run --group dev python -m pytest -q
npm --prefix web run lint
npm --prefix web run build
```

## Run the web app in development

```bash
npm --prefix web run dev
```

In another terminal, run the Python server as needed.

## Build the documentation site

```bash
uv run --only-group docs mkdocs serve
uv run --only-group docs mkdocs build --strict
```

The published GitHub Pages site is built from the Markdown files under `docs/`.

## Release notes

The release workflow builds the frontend, verifies the bundled web assets, builds
the Python distributions, and publishes to PyPI from GitHub Releases.
