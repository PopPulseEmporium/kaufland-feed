import pandas as pd
import json
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Read the Excel file
df = pd.read_excel("category tree.xlsx")

print("="*80)
print("MANOMANO CATEGORY ANALYSIS")
print("="*80)

print(f"\nTotal rows: {len(df)}")
print(f"Columns: {list(df.columns)}\n")

# Get unique level 1 categories (top level)
level1_cats = df[df['S_CATEGORY_LVL_1_NAME'].notna()].copy()

# Group by level 1 name and get unique category IDs
level1_grouped = level1_cats.groupby('S_CATEGORY_LVL_1_NAME')['CATEGORY_ID'].apply(lambda x: sorted(x.unique())).reset_index()

print("\n" + "="*80)
print("TOP-LEVEL (LEVEL 1) MANOMANO CATEGORIES")
print("="*80)
print(f"\nFound {len(level1_grouped)} unique Level 1 categories:\n")

for idx, row in level1_grouped.iterrows():
    cat_name = row['S_CATEGORY_LVL_1_NAME']
    cat_ids = row['CATEGORY_ID']

    # Get the most common category ID for this level 1 category
    # Usually the first/lowest ID is the parent
    main_id = cat_ids[0] if cat_ids else "N/A"

    print(f"{idx+1:2d}. {cat_name}")
    print(f"    Main Category ID: {main_id}")
    print(f"    Total IDs in tree: {len(cat_ids)}")
    print()

# Now let's look at OUR BigBuy categories and suggest mappings
print("\n" + "="*80)
print("BIGBUY TO MANOMANO CATEGORY MAPPING SUGGESTIONS")
print("="*80)

bigbuy_categories = {
    19651: "Bricolaje y herramientas (DIY & Tools)",
    19656: "Hogar y cocina (Home & Kitchen)",
    19657: "Iluminación (Lighting)",
    19661: "Jardín (Garden)",
    19658: "Industria, empresas y ciencia (Industrial)",
    19652: "Coche y moto (Automotive)",
    19664: "Oficina y papelería (Office)",
    19653: "Electrónica (Electronics)",
    19756: "Deportes y aire libre (Sports & Outdoor)",
    19654: "Equipaje (Luggage)",
    19666: "Productos para mascotas (Pet Products)",
}

print("\nBigBuy Categories to map:")
for bb_id, bb_name in bigbuy_categories.items():
    print(f"  [{bb_id}] {bb_name}")

# Create mapping based on semantic matching
print("\n\nSuggested mappings based on semantic analysis:\n")

# Manual best-match mapping
mapping_suggestions = []

for bb_id, bb_name in bigbuy_categories.items():
    bb_name_lower = bb_name.lower()

    # Try to find best match
    best_match = None
    best_score = 0

    for idx, row in level1_grouped.iterrows():
        mm_name = row['S_CATEGORY_LVL_1_NAME']
        mm_id = row['CATEGORY_ID'][0]
        mm_name_lower = mm_name.lower()

        # Simple keyword matching
        score = 0
        if 'giardino' in mm_name_lower and ('jardín' in bb_name_lower or 'garden' in bb_name_lower):
            score = 10
        elif 'attrezzi' in mm_name_lower and ('herramientas' in bb_name_lower or 'tool' in bb_name_lower):
            score = 10
        elif 'casa' in mm_name_lower and ('hogar' in bb_name_lower or 'home' in bb_name_lower or 'cocina' in bb_name_lower):
            score = 9
        elif 'illuminazione' in mm_name_lower and ('iluminación' in bb_name_lower or 'lighting' in bb_name_lower):
            score = 10
        elif 'auto' in mm_name_lower and ('coche' in bb_name_lower or 'moto' in bb_name_lower or 'automotive' in bb_name_lower):
            score = 10
        elif 'ufficio' in mm_name_lower and ('oficina' in bb_name_lower or 'office' in bb_name_lower):
            score = 10
        elif 'elettronica' in mm_name_lower and ('electrónica' in bb_name_lower or 'electronics' in bb_name_lower):
            score = 10
        elif 'sport' in mm_name_lower and ('deportes' in bb_name_lower or 'sports' in bb_name_lower):
            score = 10
        elif 'bagagli' in mm_name_lower and ('equipaje' in bb_name_lower or 'luggage' in bb_name_lower):
            score = 10
        elif 'animali' in mm_name_lower and ('mascotas' in bb_name_lower or 'pet' in bb_name_lower):
            score = 10
        elif 'industria' in mm_name_lower and ('industria' in bb_name_lower or 'industrial' in bb_name_lower):
            score = 10

        if score > best_score:
            best_score = score
            best_match = (mm_id, mm_name)

    if best_match:
        mapping_suggestions.append({
            'bigbuy_id': bb_id,
            'bigbuy_name': bb_name,
            'manomano_id': best_match[0],
            'manomano_name': best_match[1],
            'confidence': 'HIGH' if best_score >= 9 else 'MEDIUM'
        })
    else:
        # Default to a general category
        mapping_suggestions.append({
            'bigbuy_id': bb_id,
            'bigbuy_name': bb_name,
            'manomano_id': 20204,  # Default fallback
            'manomano_name': 'General/Other',
            'confidence': 'LOW (DEFAULT)'
        })

# Display suggestions
print("SUGGESTED CATEGORY_MAPPING:")
print("-" * 80)
for m in mapping_suggestions:
    print(f"\nBigBuy: [{m['bigbuy_id']:5d}] {m['bigbuy_name']}")
    print(f"  => ManoMano: [{m['manomano_id']:5d}] {m['manomano_name']}")
    print(f"     Confidence: {m['confidence']}")

# Generate Python code
print("\n\n" + "="*80)
print("PYTHON CODE TO ADD TO manomano_feed_generator.py:")
print("="*80)
print("\nCATEGORY_MAPPING = {")
for m in mapping_suggestions:
    print(f"    {m['bigbuy_id']}: \"{m['manomano_id']}\",  # {m['bigbuy_name'][:40]} => {m['manomano_name'][:40]}")
print("}")

# Save to JSON
output = {
    'mapping': mapping_suggestions,
    'manomano_level1_categories': level1_grouped.to_dict('records')
}

with open('category_mapping_suggestions.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("\n\nSaved detailed analysis to: category_mapping_suggestions.json")
