#!/usr/bin/env python3
"""
Recipe Runner - Single entry point for executing recipes.

Usage:
    ./runner.py --recipe example_contract_replicate
    ./runner.py --recipe example_transfer
    ./runner.py --list
"""

import sys
import argparse
import importlib.util
from pathlib import Path
from utils.logger import logger

# TODO: Support passing arguments/parameters to recipes


class RecipeRunner:
    """Simple runner to execute recipes by name."""

    def __init__(self, recipe_name: str):
        self._recipe_name = recipe_name
        self._tests_dir = Path(__file__).parent / "tests"

    @staticmethod
    def list_recipes() -> None:
        """List all available recipes."""
        tests_dir = Path(__file__).parent / "tests"
        recipes = sorted([
            f.stem for f in tests_dir.glob("*.py")
            if not f.name.startswith("_") and f.name != "__init__.py"
        ])

        if not recipes:
            logger.info("No recipes found")
            return

        logger.info("Available recipes:")
        for recipe in recipes:
            logger.info(f"  - {recipe}")

    def run(self) -> bool:
        """Execute the specified recipe."""
        recipe_path = self._tests_dir / f"{self._recipe_name}.py"

        if not recipe_path.exists():
            logger.error(f"Recipe not found: {recipe_path}")
            return False

        logger.info(f"Running recipe: {self._recipe_name}")

        # Dynamically import and execute the recipe
        spec = importlib.util.spec_from_file_location(self._recipe_name, recipe_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load recipe: {recipe_path}")
            return False

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Instantiate and execute the Recipe class
        if not hasattr(module, "Recipe"):
            logger.error(f"Recipe class not found in {recipe_path}")
            return False

        recipe = module.Recipe()
        return recipe.execute()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a recipe by name")
    parser.add_argument("--recipe", help="Recipe name (without .py extension)")
    parser.add_argument("--list", action="store_true", help="List all available recipes")

    args = parser.parse_args()

    if args.list:
        RecipeRunner.list_recipes()
        sys.exit(0)

    if not args.recipe:
        parser.error("--recipe is required when not using --list")

    runner = RecipeRunner(args.recipe)
    success = runner.run()
    sys.exit(0 if success else 1)
