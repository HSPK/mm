#!/usr/bin/env bash
# Build the web frontend and bundle into the Python package.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "==> Installing web dependencies..."
cd web
bun install --frozen-lockfile

echo "==> Building frontend..."
bun run build
cd ..

echo "==> Copying web/dist -> src/mm/_web_dist..."
rm -rf src/mm/_web_dist
cp -r web/dist src/mm/_web_dist

echo "==> Building Python package..."
uv build