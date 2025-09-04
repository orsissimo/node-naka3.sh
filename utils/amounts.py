#!/usr/bin/env python3

from typing import Union
from pydantic import BaseModel, Field, validator
from .config import MICROSTX_PER_STX, SATOSHI_PER_BTC


class StacksAmount(BaseModel):
    """
    Type-safe Stacks amount with automatic unit conversions.
    
    Stores amounts internally in microSTX (µSTX) for precision,
    provides convenient conversion methods and operators.
    """
    
    microstx_value: int = Field(alias="microstx")
    
    class Config:
        populate_by_name = True
        
    def __init__(self, microstx: int = 0, stx: float = 0.0, **kwargs):
        """
        Create StacksAmount from either microSTX or STX.
        
        Args:
            microstx: Amount in microSTX (takes precedence)
            stx: Amount in STX (converted to microSTX)
        """
        if microstx != 0:
            super().__init__(microstx_value=microstx, **kwargs)
        elif stx != 0.0:
            super().__init__(microstx_value=int(stx * MICROSTX_PER_STX), **kwargs)
        else:
            super().__init__(microstx_value=0, **kwargs)
    
    @validator("microstx_value")
    def validate_microstx(cls, v):
        if not isinstance(v, int):
            raise TypeError("MicroSTX amount must be an integer")
        # Allow negative values for balance changes/differences
        return v
    
    @classmethod
    def from_stx(cls, stx: float) -> "StacksAmount":
        """Create from STX amount."""
        return cls(stx=stx)
    
    @classmethod
    def from_microstx(cls, microstx: int) -> "StacksAmount":
        """Create from microSTX amount."""
        return cls(microstx=microstx)
    
    @property
    def microstx(self) -> int:
        """Get amount in microSTX (µSTX) - base unit."""
        return self.microstx_value
    
    @property
    def stx(self) -> float:
        """Get amount in STX."""
        return self.microstx_value / MICROSTX_PER_STX
    
    def to_microstx(self) -> int:
        """Convert to microSTX integer."""
        return self.microstx_value
    
    def to_stx(self) -> float:
        """Convert to STX float."""
        return self.stx
    
    def to_stx_string(self, decimals: int = 2) -> str:
        """Convert to STX string with specified decimals."""
        return f"{self.stx:,.{decimals}f}"
    
    def to_microstx_formatted(self) -> str:
        """Convert to formatted microSTX string with commas."""
        return f"{self.microstx_value:,}"
    
    # Arithmetic operators
    def __add__(self, other: Union["StacksAmount", int, float]) -> "StacksAmount":
        if isinstance(other, StacksAmount):
            return StacksAmount(microstx=self.microstx_value + other.microstx_value)
        elif isinstance(other, int):
            return StacksAmount(microstx=self.microstx_value + other)
        elif isinstance(other, float):
            return StacksAmount(microstx=self.microstx_value + int(other * MICROSTX_PER_STX))
        raise TypeError(f"Cannot add {type(other)} to StacksAmount")
    
    def __sub__(self, other: Union["StacksAmount", int, float]) -> "StacksAmount":
        if isinstance(other, StacksAmount):
            return StacksAmount(microstx=self.microstx_value - other.microstx_value)
        elif isinstance(other, int):
            return StacksAmount(microstx=self.microstx_value - other)
        elif isinstance(other, float):
            return StacksAmount(microstx=self.microstx_value - int(other * MICROSTX_PER_STX))
        raise TypeError(f"Cannot subtract {type(other)} from StacksAmount")
    
    def __mul__(self, multiplier: Union[int, float]) -> "StacksAmount":
        if isinstance(multiplier, (int, float)):
            return StacksAmount(microstx=int(self.microstx_value * multiplier))
        raise TypeError(f"Cannot multiply StacksAmount by {type(multiplier)}")
    
    def __truediv__(self, divisor: Union[int, float]) -> "StacksAmount":
        if isinstance(divisor, (int, float)) and divisor != 0:
            return StacksAmount(microstx=int(self.microstx_value / divisor))
        raise TypeError(f"Cannot divide StacksAmount by {type(divisor)}")
    
    # Comparison operators
    def __eq__(self, other: Union["StacksAmount", int, float]) -> bool:
        if isinstance(other, StacksAmount):
            return self.microstx_value == other.microstx_value
        elif isinstance(other, int):
            return self.microstx_value == other
        elif isinstance(other, float):
            return self.microstx_value == int(other * MICROSTX_PER_STX)
        return False
    
    def __lt__(self, other: Union["StacksAmount", int, float]) -> bool:
        if isinstance(other, StacksAmount):
            return self.microstx_value < other.microstx_value
        elif isinstance(other, int):
            return self.microstx_value < other
        elif isinstance(other, float):
            return self.microstx_value < int(other * MICROSTX_PER_STX)
        raise TypeError(f"Cannot compare StacksAmount with {type(other)}")
    
    def __le__(self, other: Union["StacksAmount", int, float]) -> bool:
        return self == other or self < other
    
    def __gt__(self, other: Union["StacksAmount", int, float]) -> bool:
        return not self <= other
    
    def __ge__(self, other: Union["StacksAmount", int, float]) -> bool:
        return not self < other
    
    def __neg__(self) -> "StacksAmount":
        """Unary minus operator for negative amounts."""
        return StacksAmount(microstx=-self.microstx_value)
    
    def __str__(self) -> str:
        """String representation showing both units with default formatting."""
        return f"{self.to_microstx_formatted()} µSTX ({self.to_stx_string()} STX)"
    
    def __repr__(self) -> str:
        return f"StacksAmount(microstx={self.microstx_value})"


class StacksFee(StacksAmount):
    """
    Type-safe transaction fee with same conversion logic as StacksAmount.
    Inherits all conversion methods and operators.
    """
    
    @classmethod
    def standard(cls) -> "StacksFee":
        """Standard transaction fee (1000 µSTX)."""
        return cls(microstx=1000)
    
    @classmethod
    def high(cls) -> "StacksFee":
        """High priority transaction fee (5000 µSTX)."""
        return cls(microstx=5000)
    
    @classmethod
    def low(cls) -> "StacksFee":
        """Low transaction fee (500 µSTX)."""
        return cls(microstx=500)
    
    def __str__(self) -> str:
        """String representation for fees with improved formatting."""
        return f"Fee: {self.to_microstx_formatted()} µSTX ({self.to_stx_string()} STX)"
    
    def __repr__(self) -> str:
        return f"StacksFee(microstx={self.microstx_value})"


class BitcoinAmount(BaseModel):
    """
    Type-safe Bitcoin amount with automatic unit conversions.
    
    Stores amounts internally in satoshi for precision,
    provides convenient conversion methods and operators.
    """
    
    satoshi_value: int = Field(alias="satoshi")
    
    class Config:
        populate_by_name = True
        
    def __init__(self, satoshi: int = 0, btc: float = 0.0, **kwargs):
        """
        Create BitcoinAmount from either satoshi or BTC.
        
        Args:
            satoshi: Amount in satoshi (takes precedence)
            btc: Amount in BTC (converted to satoshi)
        """
        if satoshi != 0:
            super().__init__(satoshi_value=satoshi, **kwargs)
        elif btc != 0.0:
            super().__init__(satoshi_value=int(btc * SATOSHI_PER_BTC), **kwargs)
        else:
            super().__init__(satoshi_value=0, **kwargs)
    
    @validator("satoshi_value")
    def validate_satoshi(cls, v):
        if not isinstance(v, int):
            raise TypeError("Satoshi amount must be an integer")
        # Allow negative values for balance changes/differences
        return v
    
    @classmethod
    def from_btc(cls, btc: float) -> "BitcoinAmount":
        """Create from BTC amount."""
        return cls(btc=btc)
    
    @classmethod
    def from_satoshi(cls, satoshi: int) -> "BitcoinAmount":
        """Create from satoshi amount."""
        return cls(satoshi=satoshi)
    
    @property
    def satoshi(self) -> int:
        """Get amount in satoshi - base unit."""
        return self.satoshi_value
    
    @property
    def btc(self) -> float:
        """Get amount in BTC."""
        return self.satoshi_value / SATOSHI_PER_BTC
    
    def to_satoshi(self) -> int:
        """Convert to satoshi integer."""
        return self.satoshi_value
    
    def to_btc(self) -> float:
        """Convert to BTC float."""
        return self.btc
    
    def to_btc_string(self, decimals: int = 8) -> str:
        """Convert to BTC string with specified decimals."""
        return f"{self.btc:,.{decimals}f}"
    
    def to_satoshi_formatted(self) -> str:
        """Convert to formatted satoshi string with commas."""
        return f"{self.satoshi_value:,}"
    
    # Arithmetic operators
    def __add__(self, other: Union["BitcoinAmount", int, float]) -> "BitcoinAmount":
        if isinstance(other, BitcoinAmount):
            return BitcoinAmount(satoshi=self.satoshi_value + other.satoshi_value)
        elif isinstance(other, int):
            return BitcoinAmount(satoshi=self.satoshi_value + other)
        elif isinstance(other, float):
            return BitcoinAmount(satoshi=self.satoshi_value + int(other * SATOSHI_PER_BTC))
        raise TypeError(f"Cannot add {type(other)} to BitcoinAmount")
    
    def __sub__(self, other: Union["BitcoinAmount", int, float]) -> "BitcoinAmount":
        if isinstance(other, BitcoinAmount):
            return BitcoinAmount(satoshi=self.satoshi_value - other.satoshi_value)
        elif isinstance(other, int):
            return BitcoinAmount(satoshi=self.satoshi_value - other)
        elif isinstance(other, float):
            return BitcoinAmount(satoshi=self.satoshi_value - int(other * SATOSHI_PER_BTC))
        raise TypeError(f"Cannot subtract {type(other)} from BitcoinAmount")
    
    def __mul__(self, multiplier: Union[int, float]) -> "BitcoinAmount":
        if isinstance(multiplier, (int, float)):
            return BitcoinAmount(satoshi=int(self.satoshi_value * multiplier))
        raise TypeError(f"Cannot multiply BitcoinAmount by {type(multiplier)}")
    
    def __truediv__(self, divisor: Union[int, float]) -> "BitcoinAmount":
        if isinstance(divisor, (int, float)) and divisor != 0:
            return BitcoinAmount(satoshi=int(self.satoshi_value / divisor))
        raise TypeError(f"Cannot divide BitcoinAmount by {type(divisor)}")
    
    # Comparison operators
    def __eq__(self, other: Union["BitcoinAmount", int, float]) -> bool:
        if isinstance(other, BitcoinAmount):
            return self.satoshi_value == other.satoshi_value
        elif isinstance(other, int):
            return self.satoshi_value == other
        elif isinstance(other, float):
            return self.satoshi_value == int(other * SATOSHI_PER_BTC)
        return False
    
    def __lt__(self, other: Union["BitcoinAmount", int, float]) -> bool:
        if isinstance(other, BitcoinAmount):
            return self.satoshi_value < other.satoshi_value
        elif isinstance(other, int):
            return self.satoshi_value < other
        elif isinstance(other, float):
            return self.satoshi_value < int(other * SATOSHI_PER_BTC)
        raise TypeError(f"Cannot compare BitcoinAmount with {type(other)}")
    
    def __le__(self, other: Union["BitcoinAmount", int, float]) -> bool:
        return self == other or self < other
    
    def __gt__(self, other: Union["BitcoinAmount", int, float]) -> bool:
        return not self <= other
    
    def __ge__(self, other: Union["BitcoinAmount", int, float]) -> bool:
        return not self < other
    
    def __neg__(self) -> "BitcoinAmount":
        """Unary minus operator for negative amounts."""
        return BitcoinAmount(satoshi=-self.satoshi_value)
    
    def __str__(self) -> str:
        """String representation showing both units with default formatting."""
        return f"{self.to_satoshi_formatted()} sat ({self.to_btc_string()} BTC)"
    
    def __repr__(self) -> str:
        return f"BitcoinAmount(satoshi={self.satoshi_value})"


class BitcoinFee(BitcoinAmount):
    """
    Type-safe Bitcoin transaction fee with same conversion logic as BitcoinAmount.
    Inherits all conversion methods and operators.
    """
    
    @classmethod
    def low(cls) -> "BitcoinFee":
        """Low priority Bitcoin fee (1000 sat)."""
        return cls(satoshi=1000)
    
    @classmethod
    def standard(cls) -> "BitcoinFee":
        """Standard Bitcoin fee (5000 sat)."""
        return cls(satoshi=5000)
    
    @classmethod
    def high(cls) -> "BitcoinFee":
        """High priority Bitcoin fee (20000 sat)."""
        return cls(satoshi=20000)
    
    def __str__(self) -> str:
        """String representation for Bitcoin fees with improved formatting."""
        return f"BTC Fee: {self.to_satoshi_formatted()} sat ({self.to_btc_string()} BTC)"
    
    def __repr__(self) -> str:
        return f"BitcoinFee(satoshi={self.satoshi_value})"


# Convenience constructors
def stx(amount: float) -> StacksAmount:
    """Create StacksAmount from STX."""
    return StacksAmount.from_stx(amount)

def microstx(amount: int) -> StacksAmount:
    """Create StacksAmount from microSTX.""" 
    return StacksAmount.from_microstx(amount)

def fee_stx(amount: float) -> StacksFee:
    """Create Fee from STX."""
    return StacksFee.from_stx(amount)

def fee_microstx(amount: int) -> StacksFee:
    """Create Fee from microSTX."""
    return StacksFee.from_microstx(amount)

def btc(amount: float) -> BitcoinAmount:
    """Create BitcoinAmount from BTC."""
    return BitcoinAmount.from_btc(amount)

def satoshi(amount: int) -> BitcoinAmount:
    """Create BitcoinAmount from satoshi."""
    return BitcoinAmount.from_satoshi(amount)

def btc_fee_satoshi(amount: int) -> BitcoinFee:
    """Create BitcoinFee from satoshi."""
    return BitcoinFee.from_satoshi(amount)

def btc_fee_btc(amount: float) -> BitcoinFee:
    """Create BitcoinFee from BTC."""
    return BitcoinFee.from_btc(amount)