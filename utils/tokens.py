#!/usr/bin/env python3

from typing import Union, Optional
from pydantic import BaseModel, Field, validator
from .config import MICROSTX_PER_STX, SATOSHI_PER_BTC

# TODO: (LATER) Devo gestire SOLO int (o meglio string?), i float (per STX e BTC) servono solo nel print


class TokenType(BaseModel):
    """Token configuration with symbols and conversion rates."""

    symbol: str = Field(description="Main token symbol")
    base_unit_symbol: str = Field(description="Base unit symbol")
    base_units_per_main: int = Field(description="Base units per main token")
    decimal_places: int = Field(description="Decimal places for display")
    name: str = Field(description="Full token name")

    class Config:
        frozen = True


class TokenAmount(BaseModel):
    """Type-safe token amount with automatic unit conversions."""

    base_units_value: int = Field(description="Amount in base units")
    token_type: TokenType = Field(description="Token configuration")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        base_units: int = 0,
        main_units: float = 0.0,
        token_type: Optional[TokenType] = None,
        **kwargs,
    ):
        """Create TokenAmount from base_units or main_units."""
        if token_type is None:
            raise ValueError("token_type must be specified")

        if base_units != 0:
            super().__init__(
                base_units_value=base_units, token_type=token_type, **kwargs
            )
        elif main_units != 0.0:
            super().__init__(
                base_units_value=int(main_units * token_type.base_units_per_main),
                token_type=token_type,
                **kwargs,
            )
        else:
            super().__init__(base_units_value=0, token_type=token_type, **kwargs)

    @validator("base_units_value")
    def validate_base_units(cls, v):
        if not isinstance(v, int):
            raise TypeError("Base units amount must be an integer")
        return v

    @classmethod
    def from_main_units(cls, amount: float, token_type: TokenType) -> "TokenAmount":
        """Create from main units (e.g., STX, BTC)."""
        return cls(main_units=amount, token_type=token_type)

    @classmethod
    def from_base_units(cls, amount: int, token_type: TokenType) -> "TokenAmount":
        """Create from base units (e.g., microSTX, satoshi)."""
        return cls(base_units=amount, token_type=token_type)

    @property
    def base_units(self) -> int:
        return self.base_units_value

    @property
    def main_units(self) -> float:
        return self.base_units_value / self.token_type.base_units_per_main

    def to_base_units(self) -> int:
        return self.base_units_value

    def to_main_units(self) -> float:
        return self.main_units

    def to_main_units_string(self, decimals: Optional[int] = None) -> str:
        if decimals is None:
            decimals = self.token_type.decimal_places
        return f"{self.main_units:,.{decimals}f}"

    def to_base_units_formatted(self) -> str:
        return f"{self.base_units_value:,}"

    def __add__(self, other: Union["TokenAmount", int, float]) -> "TokenAmount":
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(
                    f"Cannot add {other.token_type.symbol} to {self.token_type.symbol}"
                )
            return self.__class__(self.base_units_value + other.base_units_value)
        elif isinstance(other, int):
            return self.__class__(self.base_units_value + other)
        elif isinstance(other, float):
            return self.__class__(
                self.base_units_value + int(other * self.token_type.base_units_per_main)
            )
        raise TypeError(f"Cannot add {type(other)} to TokenAmount")

    def __sub__(self, other: Union["TokenAmount", int, float]) -> "TokenAmount":
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(
                    f"Cannot subtract {other.token_type.symbol} from {self.token_type.symbol}"
                )
            return self.__class__(self.base_units_value - other.base_units_value)
        elif isinstance(other, int):
            return self.__class__(self.base_units_value - other)
        elif isinstance(other, float):
            return self.__class__(
                self.base_units_value - int(other * self.token_type.base_units_per_main)
            )
        raise TypeError(f"Cannot subtract {type(other)} from TokenAmount")

    def __mul__(self, multiplier: Union[int, float]) -> "TokenAmount":
        if isinstance(multiplier, (int, float)):
            return self.__class__(int(self.base_units_value * multiplier))
        raise TypeError(f"Cannot multiply TokenAmount by {type(multiplier)}")

    def __truediv__(self, divisor: Union[int, float]) -> "TokenAmount":
        if isinstance(divisor, (int, float)) and divisor != 0:
            return self.__class__(int(self.base_units_value / divisor))
        raise TypeError(f"Cannot divide TokenAmount by {type(divisor)}")

    # Comparison operators
    def __eq__(self, other: Union["TokenAmount", int, float]) -> bool:
        if isinstance(other, TokenAmount):
            return (
                self.token_type == other.token_type
                and self.base_units_value == other.base_units_value
            )
        elif isinstance(other, int):
            return self.base_units_value == other
        elif isinstance(other, float):
            return self.base_units_value == int(
                other * self.token_type.base_units_per_main
            )
        return False

    def __lt__(self, other: Union["TokenAmount", int, float]) -> bool:
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(
                    f"Cannot compare {self.token_type.symbol} with {other.token_type.symbol}"
                )
            return self.base_units_value < other.base_units_value
        elif isinstance(other, int):
            return self.base_units_value < other
        elif isinstance(other, float):
            return self.base_units_value < int(
                other * self.token_type.base_units_per_main
            )
        raise TypeError(f"Cannot compare TokenAmount with {type(other)}")

    def __le__(self, other: Union["TokenAmount", int, float]) -> bool:
        return self == other or self < other

    def __gt__(self, other: Union["TokenAmount", int, float]) -> bool:
        return not self <= other

    def __ge__(self, other: Union["TokenAmount", int, float]) -> bool:
        return not self < other

    def __neg__(self) -> "TokenAmount":
        return self.__class__(-self.base_units_value)

    def __str__(self) -> str:
        return f"{self.to_base_units_formatted()} {self.token_type.base_unit_symbol} ({self.to_main_units_string()} {self.token_type.symbol})"

    def __repr__(self) -> str:
        return f"TokenAmount(base_units={self.base_units_value}, token_type={self.token_type.symbol})"


class StacksToken(TokenAmount):
    """TokenAmount for Stacks with constructors and display methods."""

    def __init__(self, base_units: int):
        stacks_token_type = TokenType(
            symbol="STX",
            base_unit_symbol="µSTX",
            base_units_per_main=MICROSTX_PER_STX,
            decimal_places=6,
            name="Stacks",
        )
        super().__init__(base_units=base_units, token_type=stacks_token_type)

    @classmethod
    def from_stx(cls, amount: float) -> "StacksToken":
        base_units = int(amount * MICROSTX_PER_STX)
        return cls(base_units)

    @classmethod
    def from_microstx(cls, amount: int) -> "StacksToken":
        return cls(amount)

    def to_stx(self) -> float:
        return self.to_main_units()

    def to_microstx(self) -> int:
        return self.to_base_units()

    def format_stx(self) -> str:
        return f"{self.to_stx():.6f} STX"

    def format_microstx(self) -> str:
        return f"{self.to_microstx()} µSTX"


class BitcoinToken(TokenAmount):
    """TokenAmount for Bitcoin with constructors and display methods."""

    def __init__(self, base_units: int):
        bitcoin_token_type = TokenType(
            symbol="BTC",
            base_unit_symbol="sat",
            base_units_per_main=SATOSHI_PER_BTC,
            decimal_places=8,
            name="Bitcoin",
        )
        super().__init__(base_units=base_units, token_type=bitcoin_token_type)

    @classmethod
    def from_btc(cls, amount: float) -> "BitcoinToken":
        base_units = int(amount * SATOSHI_PER_BTC)
        return cls(base_units)

    @classmethod
    def from_satoshi(cls, amount: int) -> "BitcoinToken":
        return cls(amount)

    def to_btc(self) -> float:
        return self.to_main_units()

    def to_satoshi(self) -> int:
        return self.to_base_units()

    def format_btc(self) -> str:
        return f"{self.to_btc():.8f} BTC"

    def format_satoshi(self) -> str:
        return f"{self.to_satoshi()} sat"
