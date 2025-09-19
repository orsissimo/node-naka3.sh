#!/usr/bin/env python3

from pydantic import BaseModel, Field
from typing import TypeVar

T = TypeVar("T", bound=BaseModel)


class Integer(BaseModel):
    """Wrapper type for integers returned from Stacks Core API."""
    
    _value: int = Field(alias="value", description="The integer value")
    
    def __init__(self, value: int, **kwargs):
        super().__init__(_value=value, **kwargs)
    
    @property
    def value(self) -> int:
        """Get the wrapped integer value."""
        return self._value
    
    @classmethod
    def from_raw(cls, raw_value: int) -> "Integer":
        """Create Integer from raw API response."""
        return cls(value=raw_value)
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __repr__(self) -> str:
        return f"Integer({self._value})"
    
    def __int__(self) -> int:
        return self._value
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Integer):
            return self._value == other._value
        if isinstance(other, int):
            return self._value == other
        return False
    
    class Config:
        allow_population_by_field_name = True


class Bytes(BaseModel):
    """Wrapper type for bytes returned from Stacks Core API."""
    
    _value: bytes = Field(alias="value", description="The bytes value")
    
    def __init__(self, value: bytes, **kwargs):
        super().__init__(_value=value, **kwargs)
    
    @property
    def value(self) -> bytes:
        """Get the wrapped bytes value."""
        return self._value
    
    @classmethod
    def from_raw(cls, raw_value: bytes) -> "Bytes":
        """Create Bytes from raw API response."""
        return cls(value=raw_value)
    
    def __str__(self) -> str:
        return f"Bytes({len(self._value)} bytes)"
    
    def __repr__(self) -> str:
        return f"Bytes({self._value!r})"
    
    def __bytes__(self) -> bytes:
        return self._value
    
    def __len__(self) -> int:
        return len(self._value)
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Bytes):
            return self._value == other._value
        if isinstance(other, bytes):
            return self._value == other
        return False
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class String(BaseModel):
    """Wrapper type for strings returned from Stacks Core API."""
    
    _value: str = Field(alias="value", description="The string value")
    
    def __init__(self, value: str, **kwargs):
        super().__init__(_value=value, **kwargs)
    
    @property
    def value(self) -> str:
        """Get the wrapped string value."""
        return self._value
    
    @classmethod
    def from_raw(cls, raw_value: str) -> "String":
        """Create String from raw API response."""
        return cls(value=raw_value)
    
    def __str__(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        return f"String({self._value!r})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, String):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return False
    
    class Config:
        allow_population_by_field_name = True


class SortitionList(BaseModel):
    """Wrapper type for sortition responses that can be single item or list."""
    
    _value: list = Field(alias="value", description="The list of sortition items")
    
    def __init__(self, value: list, **kwargs):
        super().__init__(_value=value, **kwargs)
    
    @property
    def value(self) -> list:
        """Get the wrapped list value."""
        return self._value
    
    @classmethod
    def from_raw(cls, raw_value) -> "SortitionList":
        """Create SortitionList from raw API response (handles both single item and list)."""
        if isinstance(raw_value, list):
            return cls(value=raw_value)
        else:
            return cls(value=[raw_value])
    
    def __len__(self) -> int:
        return len(self._value)
    
    def __iter__(self):
        return iter(self._value)
    
    def __getitem__(self, index):
        return self._value[index]
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True