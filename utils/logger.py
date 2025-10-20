#!/usr/bin/env python3
"""A logger with semantic methods, log level filtering, and f-string key-value support."""

import os
from typing import Optional
from enum import Enum
import datetime

class LogLevel(Enum):
    """Log level enumeration with filtering support."""

    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    @classmethod
    def from_string(cls, level_str: str) -> "LogLevel":
        """Convert string to LogLevel enum."""
        level_map = {
            "debug": cls.DEBUG,
            "info": cls.INFO,
            "warning": cls.WARNING,
            "error": cls.ERROR,
        }
        return level_map.get(level_str.lower(), cls.INFO)


class Colors:
    """A simple utility class for adding color to terminal output."""

    ORANGE = "\033[38;5;208m"
    WHITE = "\033[97m"
    GREY = "\033[90m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class Logger:
    """Clean logger with semantic methods, log level filtering, and f-string key-value support."""

    def __init__(self, min_level: Optional[LogLevel] = None):
        # Get log level from environment or default to INFO
        env_level = os.getenv("LOG_LEVEL", "info")
        if min_level is not None:
            self._min_level = self._validate_log_level(min_level)
        else:
            self._min_level = LogLevel.from_string(env_level)

    def _validate_log_level(self, level: LogLevel) -> LogLevel:
        """Validate log level parameter."""
        if not isinstance(level, LogLevel):
            raise TypeError("Log level must be a LogLevel enum value")
        return level

    @property
    def min_level(self) -> LogLevel:
        """Get the current minimum log level (read-only)."""
        return self._min_level

    @property
    def level(self) -> LogLevel:
        """Alias for min_level property."""
        return self._min_level

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on minimum level."""
        return level.value >= self._min_level.value

    def _format_with_color(self, text: str, color: Optional[str]) -> str:
        """Apply color formatting to text."""
        if color:
            return f"{color}{text}{Colors.RESET}"
        return text

    def _get_timestamp(self) -> str:
        """Get current timestamp in [YYYY-MM-DD HH:MM:SS] format."""

        return f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

    def _format_message(
        self, level_tag: str, message: str, color: Optional[str]
    ) -> str:
        """Format message with new [TIME][LEVEL] Message format."""
        timestamp = self._get_timestamp()
        formatted_message = self._format_with_color(message, color)
        return f"{timestamp}[{level_tag}] {formatted_message}"

    def header(self, text: str, color: Optional[str] = None) -> None:
        """Log a step header with automatic spacing (always shown regardless of log level)."""
        formatted = self._format_with_color(text, color or Colors.BLUE)
        print(f"{'=' * 60}")
        print(formatted)
        print(f"{'=' * 60}")

    def info(self, message: str, color: Optional[str] = None) -> None:
        """
        Log general information with f-string key-value support.

        Usage:
          logger.info("Starting process")
          logger.info(f"Sender: {address}", Colors.ORANGE)
          logger.info(f"Balance: {balance:,} µSTX")
        """
        if not self._should_log(LogLevel.INFO):
            return
        formatted = self._format_message("INFO", message, color or Colors.WHITE)
        print(formatted)

    def success(self, message: str, color: Optional[str] = None) -> None:
        """Log success message."""
        if not self._should_log(LogLevel.INFO):
            return
        success_msg = f"✓ {message}"
        formatted = self._format_message("SUCC", success_msg, color or Colors.GREEN)
        print(formatted)

    def error(self, message: str, color: Optional[str] = None) -> None:
        """Log error message."""
        if not self._should_log(LogLevel.ERROR):
            return
        error_msg = f"✗ {message}"
        formatted = self._format_message("ERRO", error_msg, color or Colors.RED)
        print(formatted)

    def warning(self, message: str, color: Optional[str] = None) -> None:
        """Log warning message."""
        if not self._should_log(LogLevel.WARNING):
            return
        warning_msg = f"⚠ {message}"
        formatted = self._format_message("WARN", warning_msg, color or Colors.YELLOW)
        print(formatted)

    def debug(self, message: str, color: Optional[str] = None) -> None:
        """Log debug message."""
        if not self._should_log(LogLevel.DEBUG):
            return
        formatted = self._format_message("DEBG", message, color or Colors.GREY)
        print(formatted)

    def set_level(self, level: LogLevel) -> None:
        """Change the minimum log level at runtime with validation."""
        self._min_level = self._validate_log_level(level)


# Global logger instance with environment-based configuration
logger = Logger()

# Export for easy access
__all__ = ["logger", "Colors", "LogLevel"]
