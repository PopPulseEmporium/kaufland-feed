import pandas as pd
import json
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
file_path = "category tree.xlsx"

try:
    # Try reading all sheets
    xlsx = pd.ExcelFile(file_path)
    print(f"Found {len(xlsx.sheet_names)} sheets: {xlsx.sheet_names}\n")

    for sheet_name in xlsx.sheet_names:
        print(f"\n{'='*70}")
        print(f"Sheet: {sheet_name}")
        print('='*70)

        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"\nColumns: {list(df.columns)}")
        print(f"Rows: {len(df)}")
        print(f"\nFirst 20 rows:")
        print(df.head(20).to_string())

        # If there are category IDs and names, show unique top-level categories
        if 'id' in df.columns or 'ID' in df.columns or 'category_id' in df.columns:
            print("\n\nLooking for top-level categories...")
            print(df.head(50).to_string())

        # Save to JSON for easier viewing
        output_file = f"category_tree_{sheet_name}.json"
        df.to_json(output_file, orient='records', indent=2, force_ascii=False)
        print(f"\nSaved to: {output_file}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
