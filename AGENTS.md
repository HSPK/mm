# Repository Guidelines

## Project Structure & Module Organization

The Python 3.10+ package uses a `src` layout. Code lives in `src/mm/`: `server/` contains FastAPI, `db/` owns persistence, and `media/`, `organizer/`, `library/`, and `cli/` contain domain workflows. Python tests are in `tests/` as `test_<feature>.py`.

The React/TypeScript frontend is under `web/`, with pages, components, API clients, stores, and colocated `*.test.ts(x)` files in `web/src/`. The SwiftUI client lives in `ios/MM/`; edit `ios/project.yml`, not the generated Xcode project. Documentation belongs in `docs/`, and utilities in `scripts/`.

## Build, Test, and Development Commands

- `uv sync --group dev`: install Python runtime and contributor dependencies.
- `uv run mm server`: run the FastAPI server locally.
- `uv run --group dev python -m pytest -q`: run the Python suite.
- `uv run --group dev pre-commit run --all-files`: apply Ruff linting, import sorting, and formatting.
- `bun install --cwd web && bun run --cwd web dev`: install and serve the frontend with Vite.
- `bun run --cwd web test`: run Vitest once; use `test:watch` during development.
- `bun run --cwd web lint && bun run --cwd web build`: type-check, lint, and produce `web/dist`.
- `bun run --cwd web gen:api`: regenerate `web/src/api/schema.ts` after FastAPI route or schema changes.
- `cd ios && xcodegen generate`: regenerate the iOS/macOS Xcode project.

## Coding Style & Naming Conventions

Use four spaces in Python, type annotations for public interfaces, and Ruff's 100-character line limit. Python modules and functions are `snake_case`; classes are `PascalCase`. TypeScript components use `PascalCase`, hooks begin with `use`, and other files/exports follow the surrounding kebab-case or camelCase convention. Keep API, database, and UI concerns in their existing layers. Do not hand-edit generated API bindings or Xcode project files.

## Testing Guidelines

Add focused pytest coverage for backend changes and colocated Vitest tests for frontend behavior. Name tests after observable outcomes, and reuse fixtures from `tests/conftest.py`. There is no fixed coverage threshold; regressions should include a failing test that passes with the fix. Run the relevant focused test first, then the full applicable suite before opening a PR.

## Commit & Pull Request Guidelines

Recent history favors concise imperative subjects and Conventional Commit scopes such as `feat(web):`, `fix(db):`, `perf(db):`, and `style(ios):`. Keep commits narrowly scoped. PRs should explain the user-visible change, list verification commands, link related issues, and include screenshots or recordings for web/SwiftUI changes. Call out migrations, generated files, configuration changes, and external tool requirements such as FFmpeg or ExifTool.
