"""JSON-RPC models for Codex bridge interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class JsonRpcRequest:
    """A JSON-RPC request payload."""

    method: str
    params: dict[str, Any] | list[Any] | None = None
    request_id: int | str | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the request to a JSON-compatible dictionary."""
        payload: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.request_id is not None:
            payload["id"] = self.request_id
        if self.params is not None:
            payload["params"] = self.params
        return payload


@dataclass(frozen=True, slots=True)
class JsonRpcError:
    """A JSON-RPC error payload."""

    code: int
    message: str
    data: Any | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> JsonRpcError:
        """Build an error object from a response payload."""
        return cls(
            code=int(payload["code"]),
            message=str(payload["message"]),
            data=payload.get("data"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error to a JSON-compatible dictionary."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.data is not None:
            payload["data"] = self.data
        return payload


@dataclass(frozen=True, slots=True)
class JsonRpcResponse:
    """A JSON-RPC response payload."""

    request_id: int | str | None
    result: Any | None = None
    error: JsonRpcError | None = None
    jsonrpc: str = "2.0"

    @property
    def ok(self) -> bool:
        """Return whether the response is successful."""
        return self.error is None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> JsonRpcResponse:
        """Build a response object from a response payload."""
        error = payload.get("error")
        return cls(
            request_id=payload.get("id"),
            result=payload.get("result"),
            error=JsonRpcError.from_dict(error) if isinstance(error, dict) else None,
            jsonrpc=str(payload.get("jsonrpc", "2.0")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the response to a JSON-compatible dictionary."""
        payload: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.request_id,
        }
        if self.error is not None:
            payload["error"] = self.error.to_dict()
        else:
            payload["result"] = self.result
        return payload


@dataclass(frozen=True, slots=True)
class JsonRpcNotification:
    """A JSON-RPC notification payload."""

    method: str
    params: dict[str, Any] | list[Any] | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the notification to a JSON-compatible dictionary."""
        payload: dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
        }
        if self.params is not None:
            payload["params"] = self.params
        return payload
