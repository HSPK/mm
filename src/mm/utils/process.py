"""Subprocess helpers."""

from __future__ import annotations

import json
import subprocess
from typing import Any


def run_json_command(cmd: list[str], *, timeout: float = 30) -> Any:
    """Run a command and parse stdout as JSON, returning {} on expected failures."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except (
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        FileNotFoundError,
        UnicodeError,
    ):
        return {}
