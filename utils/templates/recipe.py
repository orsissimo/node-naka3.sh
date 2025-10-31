#!/usr/bin/env python3
"""Template Method pattern implementation for test recipes."""

from abc import ABC, abstractmethod
from utils.stacks.miners import MinerManager
from utils.logger import logger


class RecipeTemplate(ABC):
    """
    Template Method pattern implementation for test recipes.

    Defines the skeleton of a test algorithm, with common setup, cleanup,
    and error handling, while allowing subclasses to implement the specific
    test logic.
    """

    def __init__(self):
        self._miners = MinerManager()

    @property
    def miners(self) -> MinerManager:
        """Protected access to miners for subclasses."""
        return self._miners

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
        finally:
            logger.header("Cleaning up...")
            self._miners.stop()
            self._miners.cleanup()

    @abstractmethod
    def _run_recipe(self) -> bool:
        """
        Abstract method that subclasses must implement.
        Contains the specific test logic for each recipe.

        Returns:
            bool: True if the test passed, False otherwise
        """
        pass

# TODO: Creo un'altra ricetta, un blank template per poter usare le API Hiro --> Poi faccio example che prende tutto, partendo da un address, quello che ha fatto in un certo timeframe
# TODO: Fare funzionare il tutto con docker https://github.com/stacks-network/hacknet --naka3 --docker
# TODO: 