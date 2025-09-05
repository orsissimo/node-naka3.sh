#!/usr/bin/env python3

from typing import Union
from pydantic import BaseModel, Field, validator
from .config import MICROSTX_PER_STX, SATOSHI_PER_BTC


class TokenType(BaseModel):
    """
    Token type configuration containing symbol information and conversion rates.
    
    This class encapsulates all token-specific metadata including symbols,
    conversion rates, and formatting preferences for different cryptocurrency tokens.
    """
    
    symbol: str = Field(description="Main token symbol (e.g., 'STX', 'BTC')")
    base_unit_symbol: str = Field(description="Base unit symbol (e.g., 'µSTX', 'sat')")
    base_units_per_main: int = Field(description="Base units per main token (e.g., 1,000,000 µSTX per STX)")
    decimal_places: int = Field(description="Default decimal places for main unit display")
    name: str = Field(description="Full token name (e.g., 'Stacks', 'Bitcoin')")
    
    class Config:
        frozen = True  # Make immutable for safety


# Token type definitions - must be defined before TokenAmount class
STACKS_TOKEN = TokenType(
    symbol="STX",
    base_unit_symbol="µSTX",
    base_units_per_main=MICROSTX_PER_STX,
    decimal_places=6,
    name="Stacks"
)

BITCOIN_TOKEN = TokenType(
    symbol="BTC", 
    base_unit_symbol="sat",
    base_units_per_main=SATOSHI_PER_BTC,
    decimal_places=8,
    name="Bitcoin"
)


class TokenAmount(BaseModel):
    """
    Generic type-safe token amount with automatic unit conversions.
    
    Stores amounts internally in base units (smallest denomination) for precision,
    provides convenient conversion methods and operators.
    Uses configurable TokenType for symbols and conversion rates.
    """
    
    base_units_value: int = Field(description="Amount in base units (e.g., microSTX, satoshi)")
    token_type: TokenType = Field(description="Token configuration")
    
    class Config:
        arbitrary_types_allowed = True
        
    def __init__(self, base_units: int = 0, main_units: float = 0.0, token_type: TokenType = STACKS_TOKEN, **kwargs):
        """
        Create TokenAmount from either base units or main units.
        
        Args:
            base_units: Amount in base units (takes precedence over main_units parameter)
            main_units: Amount in main units (automatically converted to base units)
            token_type: TokenType configuration object (defaults to STACKS_TOKEN)
            **kwargs: Additional arguments passed to parent BaseModel
            
        Note:
            - If both base_units and main_units are provided, base_units takes precedence
            - If neither is provided, creates a zero amount
            - Main unit conversion uses integer truncation to avoid floating point precision issues
        """
        if base_units != 0:
            super().__init__(base_units_value=base_units, token_type=token_type, **kwargs)
        elif main_units != 0.0:
            super().__init__(base_units_value=int(main_units * token_type.base_units_per_main), token_type=token_type, **kwargs)
        else:
            super().__init__(base_units_value=0, token_type=token_type, **kwargs)
    
    @validator("base_units_value")
    def validate_base_units(cls, v):
        """Validate base units value ensuring type safety and business logic constraints.
        
        Args:
            v: The base units value to validate
            
        Returns:
            int: The validated base units value
            
        Raises:
            TypeError: If value is not an integer
            
        Note:
            Negative values are allowed to support balance differences,
            transaction deltas, and fee calculations.
        """
        if not isinstance(v, int):
            raise TypeError("Base units amount must be an integer")
        # Allow negative values for balance changes/differences
        return v
    
    @classmethod
    def from_main_units(cls, amount: float, token_type: TokenType) -> "TokenAmount":
        """Create TokenAmount from main units (e.g., STX, BTC)."""
        return cls(main_units=amount, token_type=token_type)
    
    @classmethod
    def from_base_units(cls, amount: int, token_type: TokenType) -> "TokenAmount":
        """Create TokenAmount from base units (e.g., microSTX, satoshi)."""
        return cls(base_units=amount, token_type=token_type)
    
    
    @property
    def base_units(self) -> int:
        """Get amount in base units (smallest denomination)."""
        return self.base_units_value
    
    @property
    def main_units(self) -> float:
        """Get amount in main units (e.g., STX, BTC)."""
        return self.base_units_value / self.token_type.base_units_per_main
    
    def to_base_units(self) -> int:
        """Convert to base units integer."""
        return self.base_units_value
    
    def to_main_units(self) -> float:
        """Convert to main units float."""
        return self.main_units
    
    def to_main_units_string(self, decimals: int = None) -> str:
        """Convert to main units string with specified decimals."""
        if decimals is None:
            decimals = self.token_type.decimal_places
        return f"{self.main_units:,.{decimals}f}"
    
    def to_base_units_formatted(self) -> str:
        """Convert to formatted base units string with commas."""
        return f"{self.base_units_value:,}"
    
    
    # Arithmetic operators with type-safe automatic unit conversion
    def __add__(self, other: Union["TokenAmount", int, float]) -> "TokenAmount":
        """Add another amount, integer (base units), or float (main units) to this amount.
        
        Args:
            other: Amount to add (TokenAmount, int as base units, or float as main units)
            
        Returns:
            TokenAmount: New amount representing the sum
            
        Raises:
            TypeError: If other is not a supported type
            ValueError: If TokenAmount has different token type
            
        Note:
            - TokenAmount + TokenAmount: Direct base units addition (must have same token type)
            - TokenAmount + int: Treats int as base units
            - TokenAmount + float: Treats float as main units, converts to base units
        """
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(f"Cannot add {other.token_type.symbol} to {self.token_type.symbol}")
            return TokenAmount(base_units=self.base_units_value + other.base_units_value, token_type=self.token_type)
        elif isinstance(other, int):
            # Treat integer as base units for precise arithmetic
            return TokenAmount(base_units=self.base_units_value + other, token_type=self.token_type)
        elif isinstance(other, float):
            # Convert main units float to base units, using int() for truncation
            return TokenAmount(base_units=self.base_units_value + int(other * self.token_type.base_units_per_main), token_type=self.token_type)
        raise TypeError(f"Cannot add {type(other)} to TokenAmount")
    
    def __sub__(self, other: Union["TokenAmount", int, float]) -> "TokenAmount":
        """Subtract another amount, integer (base units), or float (main units) from this amount.
        
        Args:
            other: Amount to subtract (TokenAmount, int as base units, or float as main units)
            
        Returns:
            TokenAmount: New amount representing the difference
            
        Raises:
            TypeError: If other is not a supported type
            ValueError: If TokenAmount has different token type
            
        Note:
            - Can result in negative amounts for balance calculations
            - Same type conversion rules as addition apply
        """
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(f"Cannot subtract {other.token_type.symbol} from {self.token_type.symbol}")
            return TokenAmount(base_units=self.base_units_value - other.base_units_value, token_type=self.token_type)
        elif isinstance(other, int):
            # Treat integer as base units for precise arithmetic
            return TokenAmount(base_units=self.base_units_value - other, token_type=self.token_type)
        elif isinstance(other, float):
            # Convert main units float to base units, using int() for truncation
            return TokenAmount(base_units=self.base_units_value - int(other * self.token_type.base_units_per_main), token_type=self.token_type)
        raise TypeError(f"Cannot subtract {type(other)} from TokenAmount")
    
    def __mul__(self, multiplier: Union[int, float]) -> "TokenAmount":
        """Multiply this amount by a numeric multiplier.
        
        Args:
            multiplier: Numeric value to multiply by (int or float)
            
        Returns:
            TokenAmount: New amount representing the product
            
        Raises:
            TypeError: If multiplier is not numeric
            
        Note:
            - Result is truncated to integer base units using int()
            - Useful for calculating percentages, splits, or scaling amounts
        """
        if isinstance(multiplier, (int, float)):
            # Truncate to integer base units to maintain precision
            return TokenAmount(base_units=int(self.base_units_value * multiplier), token_type=self.token_type)
        raise TypeError(f"Cannot multiply TokenAmount by {type(multiplier)}")
    
    def __truediv__(self, divisor: Union[int, float]) -> "TokenAmount":
        """Divide this amount by a numeric divisor.
        
        Args:
            divisor: Numeric value to divide by (int or float, must be non-zero)
            
        Returns:
            TokenAmount: New amount representing the quotient
            
        Raises:
            TypeError: If divisor is not numeric or is zero
            
        Note:
            - Result is truncated to integer base units using int()
            - Division by zero raises TypeError (not ZeroDivisionError for consistency)
            - Useful for splitting amounts or calculating averages
        """
        if isinstance(divisor, (int, float)) and divisor != 0:
            # Truncate to integer base units to maintain precision
            return TokenAmount(base_units=int(self.base_units_value / divisor), token_type=self.token_type)
        raise TypeError(f"Cannot divide TokenAmount by {type(divisor)}")
    
    # Comparison operators
    def __eq__(self, other: Union["TokenAmount", int, float]) -> bool:
        if isinstance(other, TokenAmount):
            return self.token_type == other.token_type and self.base_units_value == other.base_units_value
        elif isinstance(other, int):
            return self.base_units_value == other
        elif isinstance(other, float):
            return self.base_units_value == int(other * self.token_type.base_units_per_main)
        return False
    
    def __lt__(self, other: Union["TokenAmount", int, float]) -> bool:
        if isinstance(other, TokenAmount):
            if other.token_type != self.token_type:
                raise ValueError(f"Cannot compare {self.token_type.symbol} with {other.token_type.symbol}")
            return self.base_units_value < other.base_units_value
        elif isinstance(other, int):
            return self.base_units_value < other
        elif isinstance(other, float):
            return self.base_units_value < int(other * self.token_type.base_units_per_main)
        raise TypeError(f"Cannot compare TokenAmount with {type(other)}")
    
    def __le__(self, other: Union["TokenAmount", int, float]) -> bool:
        return self == other or self < other
    
    def __gt__(self, other: Union["TokenAmount", int, float]) -> bool:
        return not self <= other
    
    def __ge__(self, other: Union["TokenAmount", int, float]) -> bool:
        return not self < other
    
    def __neg__(self) -> "TokenAmount":
        """Unary minus operator for negative amounts."""
        return TokenAmount(base_units=-self.base_units_value, token_type=self.token_type)
    
    def __str__(self) -> str:
        """String representation showing both units with default formatting."""
        return f"{self.to_base_units_formatted()} {self.token_type.base_unit_symbol} ({self.to_main_units_string()} {self.token_type.symbol})"
    
    def __repr__(self) -> str:
        return f"TokenAmount(base_units={self.base_units_value}, token_type={self.token_type.symbol})"




# Fee convenience functions
def standard_fee(token_type: TokenType = STACKS_TOKEN) -> TokenAmount:
    """Standard transaction fee for the given token type."""
    if token_type == STACKS_TOKEN:
        return microstx(1000)  # 1000 µSTX
    elif token_type == BITCOIN_TOKEN:
        return satoshi(5000)  # 5000 sat
    else:
        raise ValueError(f"No standard fee defined for {token_type.symbol}")

def high_fee(token_type: TokenType = STACKS_TOKEN) -> TokenAmount:
    """High priority transaction fee for the given token type."""
    if token_type == STACKS_TOKEN:
        return microstx(5000)  # 5000 µSTX
    elif token_type == BITCOIN_TOKEN:
        return satoshi(20000)  # 20000 sat
    else:
        raise ValueError(f"No high fee defined for {token_type.symbol}")

def low_fee(token_type: TokenType = STACKS_TOKEN) -> TokenAmount:
    """Low transaction fee for the given token type."""
    if token_type == STACKS_TOKEN:
        return microstx(500)  # 500 µSTX
    elif token_type == BITCOIN_TOKEN:
        return satoshi(1000)  # 1000 sat
    else:
        raise ValueError(f"No low fee defined for {token_type.symbol}")


# Convenience constructors for simplified amount creation

def stx(amount: float) -> TokenAmount:
    """Create TokenAmount from STX value.
    
    Args:
        amount: STX amount as float (e.g., 1.5 STX)
        
    Returns:
        TokenAmount: Amount object with converted microSTX value
        
    Example:
        >>> balance = stx(10.5)  # Creates 10,500,000 microSTX
    """
    return TokenAmount.from_main_units(amount, STACKS_TOKEN)

def microstx(amount: int) -> TokenAmount:
    """Create TokenAmount from microSTX value.
    
    Args:
        amount: microSTX amount as integer (base unit)
        
    Returns:
        TokenAmount: Amount object with exact microSTX value
        
    Example:
        >>> precise_amount = microstx(1500000)  # Creates 1.5 STX
    """ 
    return TokenAmount.from_base_units(amount, STACKS_TOKEN)


def btc(amount: float) -> TokenAmount:
    """Create TokenAmount from BTC value.
    
    Args:
        amount: BTC amount as float (e.g., 0.001 BTC)
        
    Returns:
        TokenAmount: Amount object with converted satoshi value
        
    Example:
        >>> wallet_balance = btc(0.5)  # Creates 50,000,000 satoshi
    """
    return TokenAmount.from_main_units(amount, BITCOIN_TOKEN)

def satoshi(amount: int) -> TokenAmount:
    """Create TokenAmount from satoshi value.
    
    Args:
        amount: Satoshi amount as integer (base unit)
        
    Returns:
        TokenAmount: Amount object with exact satoshi value
        
    Example:
        >>> precise_amount = satoshi(100000)  # Creates 0.001 BTC
    """
    return TokenAmount.from_base_units(amount, BITCOIN_TOKEN)

