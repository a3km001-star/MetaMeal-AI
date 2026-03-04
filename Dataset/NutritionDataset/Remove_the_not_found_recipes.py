import pandas as pd

# Load the CSV file
input_file = "recipe_nutrition_output.csv"        # Replace with your file name
output_file = "cleaned.csv"     # Output file name

# Read CSV
df = pd.read_csv(input_file)

# Remove rows where 'NotFound' column contains any non-null value
df_cleaned = df[df['NotFound'].isna()]

# Save cleaned data to a new CSV file
df_cleaned.to_csv(output_file, index=False)

print("Rows with values in 'NotFound' column have been removed successfully.")