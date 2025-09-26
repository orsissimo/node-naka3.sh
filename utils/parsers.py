#!/usr/bin/env python3

"""Common JSON parsing utilities for API responses and CLI output."""

from __future__ import annotations

import json
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .logger import logger
from .types.exceptions import (
    StacksValidationException,
    StacksAPIException,
    StacksCLIException,
)

T = TypeVar("T", bound=BaseModel)


def validate_pydantic_model(json_data: Any, response_type: Type[T]) -> T:
    """Core Pydantic validation with consistent error logging."""
    if not isinstance(response_type, type) or not issubclass(response_type, BaseModel):
        raise TypeError(
            f"response_type {response_type.__name__} must be a Pydantic BaseModel"
        )

    try:
        logger.debug(f"Parsing JSON data for {response_type.__name__}: {json_data}")
        parsed_object = response_type.model_validate(json_data)
        logger.debug(f"Successfully created {response_type.__name__} object")
        return parsed_object
    except ValidationError as e:
        logger.error(f"Pydantic validation error for {response_type.__name__}: {e}")
        logger.error(f"JSON data: {json_data}")
        raise StacksValidationException(
            f"Validation failed for {response_type.__name__}: {e}"
        ) from e


def parse_api_response(data: Dict[str, Any], response_type: Type[T]) -> T:
    """Parse already-parsed JSON data from API responses."""
    if not data:
        raise StacksValidationException(
            f"Empty or None data for {response_type.__name__}"
        )

    try:
        return validate_pydantic_model(data, response_type)
    except Exception as e:
        logger.error(f"Unexpected error parsing {response_type.__name__}: {e}")
        raise StacksAPIException(
            f"Unexpected error parsing {response_type.__name__}: {e}"
        ) from e


def parse_cli_response(stdout: str, response_type: Type[T]) -> T:
    """Parse JSON string from CLI stdout."""
    if not stdout or not stdout.strip():
        raise StacksValidationException(
            f"Empty or None stdout for {response_type.__name__}"
        )

    try:
        json_data = json.loads(stdout.strip())
        logger.debug(f"Parsed JSON data: {json_data}")
        return validate_pydantic_model(json_data, response_type)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for {response_type.__name__}: {e}")
        logger.error(f"Raw stdout: {repr(stdout)}")
        raise StacksValidationException(
            f"JSON decode error for {response_type.__name__}: {e}"
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error parsing {response_type.__name__}: {e}")
        raise StacksCLIException(
            f"Unexpected error parsing {response_type.__name__}: {e}"
        ) from e
