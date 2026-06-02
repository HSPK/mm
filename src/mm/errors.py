"""Application-wide error and exception types."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    IMPORT_TEMPLATE_FORMAT_FAILED = "import_template.format_failed"


class MMError(Exception):
    """Base class for expected MM application errors."""

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code.value, "message": self.message}
        if self.details:
            data["details"] = self.details
        return data


class ImportTemplateError(MMError):
    """Raised when an import path template cannot be formatted."""

    def __init__(
        self,
        template: str,
        values: dict[str, object],
        cause: BaseException,
    ) -> None:
        super().__init__(
            f"Invalid import template: {template!r}",
            code=ErrorCode.IMPORT_TEMPLATE_FORMAT_FAILED,
            details={
                "template": template,
                "values": values,
                "supported_fields": sorted(values),
                "error": str(cause),
            },
            cause=cause,
        )
