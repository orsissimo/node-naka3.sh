#!/usr/bin/env python3

"""Lightweight wrapper types that behave like native primitives."""

from __future__ import annotations

from typing import Any, Iterable


class Integer(int):
    """Integer flavored wrapper that keeps native ``int`` behaviour."""

    __slots__ = ()

    def __new__(cls, value: int | str | "Integer") -> "Integer":
        if isinstance(value, str):
            # Allow decimal or 0x-prefixed strings from RPC responses.
            value = int(value, 0)
        return super().__new__(cls, int(value))

    @property
    def value(self) -> int:
        """Return the underlying integer."""
        return int(self)

    @classmethod
    def from_raw(cls, raw_value: int | str) -> "Integer":
        return cls(raw_value)

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"Integer({int(self)})"


class Bytes(bytes):
    """Bytes wrapper that preserves ``bytes`` semantics."""

    __slots__ = ()

    def __new__(cls, value: bytes | bytearray | memoryview | Iterable[int] | str) -> "Bytes":
        if isinstance(value, str):
            if value.startswith("0x"):
                value = bytes.fromhex(value[2:])
            else:
                value = value.encode()
        elif isinstance(value, memoryview):
            value = value.tobytes()
        return super().__new__(cls, bytes(value))

    @property
    def value(self) -> bytes:
        """Return raw bytes."""
        return bytes(self)

    @classmethod
    def from_raw(
        cls, raw_value: bytes | bytearray | memoryview | Iterable[int] | str
    ) -> "Bytes":
        return cls(raw_value)

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"Bytes({bytes(self)!r})"


class String(str):
    """String wrapper with normal ``str`` behaviour."""

    __slots__ = ()

    def __new__(cls, value: str | bytes | bytearray | memoryview) -> "String":
        if isinstance(value, memoryview):
            value = value.tobytes()
        if isinstance(value, (bytes, bytearray)):
            value = bytes(value).decode()
        return super().__new__(cls, value)

    @property
    def value(self) -> str:
        """Return the underlying string."""
        return str(self)

    @classmethod
    def from_raw(cls, raw_value: str | bytes | bytearray | memoryview) -> "String":
        return cls(raw_value)

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"String({str(self)!r})"


class SortitionList(list):
    """List-like wrapper that normalises single item or list responses."""

    __slots__ = ()

    def __init__(self, value: Iterable[Any] | Any):
        if isinstance(value, SortitionList):
            value = list(value)
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes, bytearray)):
            value = [value]
        super().__init__(value)

    @property
    def value(self) -> list[Any]:
        """Return the underlying list."""
        return list(self)

    @classmethod
    def from_raw(cls, raw_value: Any) -> "SortitionList":
        if raw_value is None:
            return cls([])
        if isinstance(raw_value, SortitionList):
            return cls(raw_value)
        if isinstance(raw_value, list):
            return cls(raw_value)
        return cls([raw_value])

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"SortitionList({list(self)!r})"
