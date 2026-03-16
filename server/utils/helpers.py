"""
Utility helper functions for the FastAPI application.

This module provides various helper functions including:
- Food dataset loading
- Macro calculations
- Data formatting utilities
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import HTTPException

# Configure logger for this module
logger = logging.getLogger(__name__)


def load_food_dataset() -> List[Dict[str, Any]]:
    """
    Load the Indian food dataset from JSON file.
    
    This function loads the food dataset containing nutritional information,
    ingredients, and cooking instructions for Indian recipes.
    
    Returns:
        List[Dict[str, Any]]: List of recipe dictionaries containing:
            - RecipeName: Name of the recipe
            - Calories: Caloric content (kcal)
            - Protein: Protein content (g)
            - Carbohydrates: Carbohydrate content (g)
            - Fat: Fat content (g)
            - Ingredients: List of ingredients
            - Instructions: Cooking instructions
            - DietType: Dietary classification
    
    Raises:
        HTTPException: If the dataset file is not found or cannot be loaded
        
    Example:
        >>> recipes = load_food_dataset()
        >>> print(f"Loaded {len(recipes)} recipes")
    """
    try:
        # Get the path to the constants directory
        # Assuming helpers.py is in server/utils/
        current_dir = Path(__file__).parent.parent  # Go up to server/
        dataset_path = current_dir / "constants" / "indian_food.json"
        
        # Check if file exists
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {dataset_path}")
        
        # Load the JSON file
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract the recipes list from the JSON structure
        # The JSON has structure: {"metadata": {...}, "recipes": [...]}
        if isinstance(data, dict) and 'recipes' in data:
            recipes = data['recipes']
        elif isinstance(data, list):
            # If it's already a list, use it directly
            recipes = data
        else:
            raise ValueError("Invalid dataset format: expected 'recipes' key or list")
        
        # Validate that we have data
        if not recipes:
            raise ValueError("Dataset is empty")
        
        return recipes
        
    except FileNotFoundError as e:
        # Log full error details server-side
        logger.error(f"Food dataset file not found: {str(e)}", exc_info=True)
        # Return generic error to client
        raise HTTPException(
            status_code=500,
            detail="Failed to load food dataset"
        )
    except json.JSONDecodeError as e:
        # Log full error details server-side
        logger.error(f"Invalid JSON format in dataset file: {str(e)}", exc_info=True)
        # Return generic error to client
        raise HTTPException(
            status_code=500,
            detail="Failed to load food dataset"
        )
    except ValueError as e:
        # Log full error details server-side
        logger.error(f"Dataset validation error: {str(e)}", exc_info=True)
        # Return generic error to client
        raise HTTPException(
            status_code=500,
            detail="Failed to load food dataset"
        )
    except Exception as e:
        # Log full error details server-side
        logger.error(f"Unexpected error loading food dataset: {str(e)}", exc_info=True)
        # Return generic error to client
        raise HTTPException(
            status_code=500,
            detail="Failed to load food dataset"
        )


def get_food_dataset_metadata() -> Optional[Dict[str, Any]]:
    """
    Load metadata about the food dataset.
    
    Returns:
        Optional[Dict[str, Any]]: Metadata dictionary containing dataset info,
                                   or None if metadata not available
    """
    try:
        current_dir = Path(__file__).parent.parent
        dataset_path = current_dir / "constants" / "indian_food.json"
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Return metadata if it exists
        if isinstance(data, dict) and 'metadata' in data:
            return data['metadata']
        
        return None
        
    except Exception:
        return None

