"""
Convert Cleaned Dataset to JSON

This script converts the cleaned_food_dataset.csv to JSON format
and saves it to server/constants/indian_food.json for use in the application.

"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime


def convert_csv_to_json(
    input_file: str = "cleaned_food_dataset.csv",
    output_file: str = "indian_food.json"
):
    """
    Convert cleaned CSV dataset to JSON format.
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Name of output JSON file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get paths
        script_dir = Path(__file__).parent
        input_path = script_dir / input_file
        
        # Output path should be in server/constants/
        output_dir = script_dir.parent / "constants"
        output_path = output_dir / output_file
        
        # Check if input file exists
        if not input_path.exists():
            print(f"Error: Input file '{input_path}' not found.")
            return False
        
        print(f"Reading CSV from: {input_path}")
        df = pd.read_csv(input_path)
        
        print(f"Dataset shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Convert DataFrame to list of dictionaries
        recipes_list = df.to_dict(orient='records')
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare JSON structure
        json_data = {
            "metadata": {
                "total_recipes": len(recipes_list),
                "source": input_file,
                "date_created": datetime.now().date().isoformat(),
                "columns": list(df.columns)
            },
            "recipes": recipes_list
        }
        
        # Save to JSON with proper formatting
        print(f"\nSaving JSON to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Verify file was created
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"✓ JSON file created successfully!")
            print(f"  Location: {output_path}")
            print(f"  Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            print(f"  Total recipes: {len(recipes_list)}")
            
            # Display sample recipe only if recipes exist
            if recipes_list:
                print("\n=== Sample Recipe ===")
                sample = recipes_list[0]
                for key, value in sample.items():
                    display_value = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                    print(f"{key}: {display_value}")
            else:
                print("\nWarning: No data rows found in the dataset")
            
            return True
        else:
            print("Error: File was not created")
            return False
            
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return False
    except pd.errors.EmptyDataError:
        print("Error: The input file is empty")
        return False
    except (TypeError, OverflowError) as e:
        print(f"Error: JSON encoding failed - {e}")
        return False
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("CSV to JSON Converter")
    print("=" * 60)
    
    success = convert_csv_to_json()
    
    if success:
        print("\n Conversion completed successfully!")
        sys.exit(0)
    else:
        print("\n Conversion failed!")
        sys.exit(1)
