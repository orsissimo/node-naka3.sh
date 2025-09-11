#!/usr/bin/env python3

from typing import Any
from .types.exceptions import RecipeFailedException
from .logger import logger


def assert_eq(expected: Any, actual: Any, description: str) -> None:
    """Assert expected equals actual. Raises RecipeFailedException if not."""
    if actual == expected:
        return  # Success - no output

    # Failure - raise exception
    raise RecipeFailedException(
        f"Assertion failed: {description}",
        details=f"Expected: {expected}, Actual: {actual}",
    )


def check_eq(expected: Any, actual: Any, description: str) -> bool:
    """Check expected equals actual. Logs result and returns bool."""
    if actual == expected:
        logger.success(f"{description}: {expected}")
        return True
    else:
        logger.error(f"{description} incorrect")
        logger.info(f"  Expected: {expected}")
        logger.info(f"  Actual: {actual}")
        return False
