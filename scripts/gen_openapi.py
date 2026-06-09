#!/usr/bin/env python3
"""Dump the FastAPI OpenAPI schema to stdout.

Used by the web frontend's ``gen:api`` script to regenerate typed bindings from
``openapi-typescript`` without needing a running server.
"""

from __future__ import annotations

import json
import sys

from mm.server.app import create_app


def main() -> None:
    app = create_app("openapi-gen.db")
    json.dump(app.openapi(), sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
