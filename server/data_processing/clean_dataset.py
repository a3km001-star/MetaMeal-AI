"""
Dataset Cleaning Script for Nutrition Data

This script processes the raw nutrition dataset by:
- Removing unused columns
- Selecting only required nutritional and recipe information
- Removing rows with missing data
- Saving the cleaned dataset for use in the application
"""

import os
import sys
import pandas as pd
from pathlib import Path


def clean_dataset(input_file: str = "Dataset.csv", output_file: str = "cleaned_food_dataset.csv"):
    """
    Clean and process the nutrition dataset.
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path to save the cleaned CSV file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the directory of this script
        script_dir = Path(__file__).parent
        input_path = script_dir / input_file
        output_path = script_dir / output_file
        
        # Check if input file exists
        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found.")
            return False
        
        print(f"Reading dataset from: {input_path}")
        orig_df = pd.read_csv(input_path)
        
        # Display initial dataset info
        print(f"Initial dataset shape: {orig_df.shape}")
        print(f"Columns found: {list(orig_df.columns)}")
        
        # Define column mapping from dataset columns to our required names
        column_mapping = {
            'RecipeName': 'RecipeName',
            'Calories (kcal)': 'Calories',
            'Protein (g)': 'Protein',
            'Carbohydrates (g)': 'Carbohydrates',
            'Fat (g)': 'Fat',
            'Cleaned-Ingredients': 'Ingredients',
            'TranslatedInstructions': 'Instructions'
        }
        
        # Optional column mapping (these may not exist or be empty)
        optional_mapping = {
            'Veg(yes or no)': 'DietType'
        }
        
        # Check if all required source columns exist
        missing_columns = [col for col in column_mapping.keys() if col not in orig_df.columns]
        if missing_columns:
            print(f"Error: Missing required columns: {missing_columns}")
            print(f"Available columns: {list(orig_df.columns)}")
            return False
        
        # Select and rename required columns
        df = orig_df[list(column_mapping.keys())].copy()
        df = df.rename(columns=column_mapping)
        
        # Add optional columns if they exist and have data
        for old_col, new_col in optional_mapping.items():
            if old_col in orig_df.columns:
                if not orig_df[old_col].isna().all():
                    df[new_col] = orig_df[old_col]
                else:
                    print(f"Optional column '{old_col}' is empty, using default value")
                    df[new_col] = 'Unknown'
            else:
                print(f"Optional column '{old_col}' not found, using default value")
                df[new_col] = 'Unknown'
        
        print(f"Selected and renamed columns successfully")
        
        # Check for missing values per column (excluding DietType which we set manually)
        print("\n=== Missing Values Analysis ===")
        columns_to_check = [col for col in df.columns if col != 'DietType']
        missing_counts = df[columns_to_check].isnull().sum()
        for col, count in missing_counts.items():
            if count > 0:
                print(f"{col}: {count} missing values ({count/len(df)*100:.1f}%)")
        
        # Remove rows with missing values in critical columns
        critical_columns = ['RecipeName', 'Calories', 'Protein', 'Carbohydrates', 'Fat', 'Ingredients']
        initial_rows = len(df)
        df = df.dropna(subset=critical_columns)
        rows_removed = initial_rows - len(df)
        print(f"\nRemoved {rows_removed} rows with missing critical data")
        
        if len(df) == 0:
            print("Error: No data remaining after removing missing values!")
            return False
        
        # Additional data quality checks
        # Remove duplicate recipes if any
        initial_rows = len(df)
        df = df.drop_duplicates(subset=['RecipeName'], keep='first')
        duplicates_removed = initial_rows - len(df)
        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate recipes")
        
        # Process and clean string columns
        string_columns = ['RecipeName', 'DietType', 'Ingredients', 'Instructions']
        critical_columns_set = set(critical_columns)
        for col in string_columns:
            if col in df.columns:
                # For critical columns, preserve NaN; for non-critical, fill empty strings
                if col not in critical_columns_set:
                    df[col] = df[col].fillna('').astype(str).str.strip()
                else:
                    # Keep NaN as is for critical columns (already handled by dropna)
                    df[col] = df[col].astype(str).str.strip()
        
        # Standardize DietType values (convert "yes"/"no" to "Vegetarian"/"Non-Vegetarian")
        if 'DietType' in df.columns:
            df['DietType'] = df['DietType'].str.lower().str.strip()
            df['DietType'] = df['DietType'].map({
                'yes': 'Vegetarian',
                'no': 'Non-Vegetarian',
                'veg': 'Vegetarian',
                'non-veg': 'Non-Vegetarian'
            }).fillna('Unknown')
        
        # Ensure numeric columns are float type
        numeric_columns = ['Calories', 'Protein', 'Carbohydrates', 'Fat']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove any rows where numeric conversion failed
        initial_rows = len(df)
        df = df.dropna(subset=numeric_columns)
        numeric_failures = initial_rows - len(df)
        if numeric_failures > 0:
            print(f"Removed {numeric_failures} rows with invalid numeric values")
        
        # Save cleaned dataset
        df.to_csv(output_path, index=False)
        print(f"\nCleaned dataset saved to: {output_path}")
        print(f"Final dataset shape: {df.shape}")
        print(f"Total recipes: {len(df)}")
        
        # Display summary statistics
        print("\n=== Nutritional Summary ===")
        print(df[['Calories', 'Protein', 'Carbohydrates', 'Fat']].describe())
        
        # Display diet type distribution
        print("\n=== Diet Type Distribution ===")
        print(df['DietType'].value_counts())
        
        return True
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return False
    except pd.errors.EmptyDataError:
        print("Error: The input file is empty")
        return False
    except Exception as e:
        print(f"Error processing dataset: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Nutrition Dataset Cleaning Script")
    print("=" * 60)
    
    success = clean_dataset()
    
    if success:
        print("\n Dataset cleaning completed successfully!")
        sys.exit(0)
    else:
        print("\n Dataset cleaning failed!")
        sys.exit(1)