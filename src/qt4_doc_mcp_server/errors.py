"""Error taxonomy for MCP documentation tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DocumentationError(Exception):
    code: str
    message: str

    def __post_init__(self) -> None:
        super().__init__(self.tool_message())

    def __str__(self) -> str:  # pragma: no cover - repr helper
        return f"{self.code}: {self.message}"

    def tool_message(self) -> str:
        return f"{self.code}: {self.message}"


class InvalidURLError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("InvalidURL", message)


class NotAllowedError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("NotAllowed", message)


class NotFoundError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("NotFound", message)


class FetchError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("FetchError", message)


class ParseError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("ParseError", message)


class TimeoutDocumentationError(DocumentationError):
    def __init__(self, message: str):
        super().__init__("Timeout", message)
