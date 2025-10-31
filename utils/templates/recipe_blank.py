#!/usr/bin/env python3
"""Minimal recipe template for API-only workflows."""

from abc import ABC, abstractmethod
from utils.logger import logger


class RecipeTemplate(ABC):
    """
    Template Method pattern for lightweight recipes.

    Provides a clean execute() wrapper with error handling, suitable for
    scripts that interact with external APIs (e.g., Hiro) without spinning
    up local miners or performing chain orchestration.
    """

    def execute(self) -> bool:
        """
        Template method that defines the algorithm skeleton.
        This is the main entry point that handles setup, execution, and cleanup.
        """
        try:
            return self._run_recipe()
        except Exception as e:
            logger.error(f"TEST FAILED - Unexpected Error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return False

    @abstractmethod
    def _run_recipe(self) -> bool:
        """
        Abstract method that subclasses must implement.
        Contains the specific test logic for each recipe.

        Returns:
            bool: True if the test passed, False otherwise
        """
        pass
