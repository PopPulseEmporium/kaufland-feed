import pandas as pd

# Read the problematic CSV file
input_file = 'manomano_feed_it__3_.csv'  # Change this to your file path
output_file = 'manomano_feed_it_CORRECTED.csv'

print(f"Reading file: {input_file}")
df = pd.read_csv(input_file)

print(f"Original file: {len(df)} rows, {len(df.columns)} columns")
print(f"Original columns: {list(df.columns)}")

# 1. Rename columns
column_rename_map = {
    'category': 'mm_category',
    'picture_1': 'image_1',
    'picture_2': 'image_2',
    'picture_3': 'image_3',
    'picture_4': 'image_4',
    'picture_5': 'image_5',
    'parent_sku': 'Parent_SKU'
}

df = df.rename(columns=column_rename_map)
print("\n✓ Columns renamed")

# 2. Add unit columns
df['width_unit'] = 'cm'
df['height_unit'] = 'cm'
df['length_unit'] = 'cm'
df['weight_unit'] = 'kg'
print("✓ Unit columns added")

# 3. Reorder columns to match the working file format
correct_column_order = [
    'sku', 'ean', 'sku_manufacturer', 'brand', 'mm_category', 'title', 'description',
    'image_1', 'image_2', 'image_3', 'image_4', 'image_5',
    'product_price_vat_inc', 'min_quantity', 'increment', 'quantity',
    'use_grid', 'carrier_grid_1', 'shipping_time_carrier_grid_1',
    'width', 'width_unit', 'height', 'height_unit', 'length', 'length_unit', 
    'weight', 'weight_unit', 'volume', 'DisplayWeight', 'Parent_SKU', 'parent_title'
]

df = df[correct_column_order]
print("✓ Columns reordered")

# 4. Save the corrected file
df.to_csv(output_file, index=False)

print(f"\n✅ SUCCESS! Fixed file saved to: {output_file}")
print(f"New file: {len(df)} rows, {len(df.columns)} columns")
print(f"\nNew columns:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i}. {col}")

# Show a sample row to verify
print("\n" + "="*80)
print("SAMPLE - First product:")
print("="*80)
sample = df.iloc[0]
for col, val in sample.items():
    if pd.notna(val) and val != '':
        print(f"{col}: {val}")
