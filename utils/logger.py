import logging
from typing import Optional, Any
from enum import Enum

class Colors:
    """A simple utility class for adding color to terminal output."""
    ORANGE = '\033[38;5;208m'
    WHITE = '\033[97m'
    GREY = '\033[90m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

class Logger:
    """Clean logger with semantic methods and optional color overrides."""
    
    def __init__(self):
        pass
    
    def _get_color_code(self, color: str) -> str:
        """Get ANSI color code directly from Colors class."""
        return color
    
    def _format_with_color(self, text: str, color: Optional[str]) -> str:
        """Apply color formatting to text."""
        if color:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in HH:MM:SS format."""
        import datetime
        return datetime.datetime.now().strftime('%H:%M:%S')
    
    def header(self, text: str, color: Optional[str] = None) -> None:
        """Log a step header with automatic spacing."""
        formatted = self._format_with_color(text, color or Colors.BLUE)
        print(f"{'=' * 60}")
        print(formatted)
        print(f"{'=' * 60}")
    
    def standard(self, key: str, value: Any, unit: Optional[str] = None, color: Optional[str] = None) -> None:
        """Log key-value pairs with smart formatting."""
        timestamp = self._get_timestamp()
        # Smart value formatting
        if isinstance(value, int) and abs(value) > 1000:
            formatted_value = f"{value:,}"
        else:
            formatted_value = str(value)
        
        if unit:
            formatted_value += f" {unit}"
        
        # Auto-detect addresses and dim them
        if isinstance(value, str) and value.startswith('ST'):
            value_color = color or Colors.DIM
        else:
            value_color = color or Colors.WHITE
        
        key_part = self._format_with_color(key, Colors.WHITE)
        value_part = self._format_with_color(formatted_value, value_color)
        print(f"{timestamp} - {key_part}: {value_part}")
    
    def info(self, text: str, color: Optional[str] = None) -> None:
        """Log general information."""
        timestamp = self._get_timestamp()
        formatted = self._format_with_color(text, color or Colors.WHITE)
        print(f"{timestamp} - {formatted}")
    
    def success(self, text: str, color: Optional[str] = None) -> None:
        """Log success message."""
        timestamp = self._get_timestamp()
        default_color = color or Colors.GREEN
        formatted = self._format_with_color(f"✓ {text}", default_color)
        print(f"{timestamp} - {formatted}")
    
    def error(self, text: str, color: Optional[str] = None) -> None:
        """Log error message."""
        timestamp = self._get_timestamp()
        default_color = color or Colors.RED
        formatted = self._format_with_color(f"✗ {text}", default_color)
        print(f"{timestamp} - {formatted}")
    
    def warn(self, text: str, color: Optional[str] = None) -> None:
        """Log warning message.""" 
        timestamp = self._get_timestamp()
        default_color = color or Colors.YELLOW
        formatted = self._format_with_color(f"⚠ {text}", default_color)
        print(f"{timestamp} - {formatted}")
    
    def warning(self, text: str, color: Optional[str] = None) -> None:
        """Log warning message (alias for warn)."""
        self.warn(text, color)
    
    def dim(self, text: str, color: Optional[str] = None) -> None:
        """Log dimmed/secondary text."""
        timestamp = self._get_timestamp()
        formatted = self._format_with_color(text, color or Colors.DIM)
        print(f"{timestamp} - {formatted}")
    
    def subheader(self, text: str, color: Optional[str] = None) -> None:
        """Log sub-section header."""
        timestamp = self._get_timestamp()
        formatted = self._format_with_color(text, color or Colors.CYAN)
        print(f"{timestamp} - {formatted}")
    
    def stacks(self, text: str, color: Optional[str] = None) -> None:
        """Log Stacks-specific data (default orange)."""
        timestamp = self._get_timestamp()
        formatted = self._format_with_color(text, color or Colors.ORANGE)
        print(f"{timestamp} - {formatted}")
    
    def custom(self, text: str, color: str) -> None:
        """Log with custom color (always requires color)."""
        timestamp = self._get_timestamp()
        formatted = self._format_with_color(text, color)
        print(f"{timestamp} - {formatted}")
    
    # Debug and critical methods with simple colored output
    def debug(self, msg: str) -> None:
        """Log debug message with timestamp."""
        timestamp = self._get_timestamp()
        formatted_msg = f"{Colors.GREY}{timestamp} - DEBUG - {msg}{Colors.RESET}"
        print(formatted_msg)
    
    def critical(self, msg: str) -> None:
        """Log critical message with timestamp."""
        timestamp = self._get_timestamp()
        formatted_msg = f"{Colors.BOLD}{Colors.RED}{timestamp} - CRITICAL - {msg}{Colors.RESET}"
        print(formatted_msg)


# Create simple logger instance
logger = Logger()

# Export for easy access
__all__ = ['logger', 'Colors']