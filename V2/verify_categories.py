"""
Verify ManoMano Category IDs

Checks if the category IDs in CATEGORY_MAPPING exist in ManoMano's category tree.
This helps identify the root cause of CATEGORY_MISSING errors.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd

print("=" * 80)
print("VERIFYING MANOMANO CATEGORY IDS")
print("=" * 80)

# Our current mapping
CATEGORY_MAPPING = {
    19651: "21542",  # DIY & Tools => Utensileria
    19656: "20204",  # Home & Kitchen => Arredo casa
    19657: "20446",  # Lighting => Illuminazione
    19661: "19596",  # Garden => Giardino e piscine
    19658: "21294",  # Industrial => Ferramenta
    19652: "21294",  # Automotive => Ferramenta
    19664: "20204",  # Office => Arredo casa
    19653: "21092",  # Electronics => Elettricità
    19756: "19596",  # Sports & Outdoor => Giardino e piscine
    19654: "20204",  # Luggage => Arredo casa
    19666: "20946",  # Pet Products => Animali
}

# Load ManoMano category tree
print("\nLoading category tree.xlsx...")
df = pd.read_excel('category tree.xlsx')
print(f"✅ Loaded {len(df):,} ManoMano categories")

# Convert CATEGORY_ID to string for comparison
df['CATEGORY_ID'] = df['CATEGORY_ID'].astype(str)

# Check each category
print("\n" + "-" * 80)
print("CHECKING CATEGORY IDS:")
print("-" * 80)

unique_categories = set(CATEGORY_MAPPING.values())
found = 0
not_found = 0
results = {}

for cat_id in sorted(unique_categories):
    matches = df[df['CATEGORY_ID'] == cat_id]
    if len(matches) > 0:
        lvl1 = matches.iloc[0]['S_CATEGORY_LVL_1_NAME']
        lvl2 = matches.iloc[0].get('S_CATEGORY_LVL_2_NAME', '')
        print(f"\n✓ Category {cat_id}: FOUND")
        print(f"  Level 1: {lvl1}")
        if lvl2 and pd.notna(lvl2):
            print(f"  Level 2: {lvl2}")
        found += 1
        results[cat_id] = 'FOUND'
    else:
        print(f"\n✗ Category {cat_id}: NOT FOUND IN MANOMANO TREE")
        not_found += 1
        results[cat_id] = 'NOT_FOUND'

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nTotal unique categories checked: {len(unique_categories)}")
print(f"✓ Found: {found}")
print(f"✗ Not found: {not_found}")

# Show which BigBuy categories use which ManoMano IDs
print("\n" + "-" * 80)
print("BIGBUY → MANOMANO MAPPING STATUS:")
print("-" * 80)

for bigbuy_id, manomano_id in sorted(CATEGORY_MAPPING.items()):
    status = results.get(manomano_id, 'UNKNOWN')
    icon = "✓" if status == 'FOUND' else "✗"
    print(f"{icon} BigBuy {bigbuy_id} → ManoMano {manomano_id} ({status})")

# Recommendations
print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if not_found > 0:
    print("\n⚠️  ACTION REQUIRED:")
    print(f"{not_found} category ID(s) don't exist in ManoMano tree.")
    print("These are likely causing the CATEGORY_MISSING errors (4,459 products).")

    print("\n📋 Next steps:")
    print("1. For each invalid category, search category tree.xlsx for alternatives")
    print("2. Update CATEGORY_MAPPING in manomano_feed_generator.py (lines 24-36)")
    print("3. Regenerate feed with: python manomano_feed_generator.py")
    print("4. Re-upload to ManoMano and check error report")

    print("\n💡 Tips:")
    print("- Look for similar categories in the same top-level group")
    print("- Use broader categories if specific ones don't exist")
    print("- Test with a small batch first")

    # Suggest searching the tree
    print("\n🔍 To find alternative categories:")
    not_found_ids = [cat_id for cat_id, status in results.items() if status == 'NOT_FOUND']
    for cat_id in not_found_ids:
        print(f"\n  Category {cat_id} alternatives:")
        print(f"  - Open category tree.xlsx")
        print(f"  - Search for relevant category names")
        print(f"  - Note the CATEGORY_ID")
        print(f"  - Update CATEGORY_MAPPING")
else:
    print("\n✅ All category IDs verified!")
    print("Category IDs are NOT the cause of CATEGORY_MISSING errors.")
    print("\nOther possible causes:")
    print("1. Category format issue (string vs integer)")
    print("2. ManoMano marketplace restrictions")
    print("3. Missing category attributes/parameters")
    print("4. Country-specific category availability")
    print("\n💡 Next step: Contact ManoMano support for clarification")

# Show top-level category distribution
print("\n" + "=" * 80)
print("TOP-LEVEL CATEGORY DISTRIBUTION IN MANOMANO TREE")
print("=" * 80)

lvl1_counts = df['S_CATEGORY_LVL_1_NAME'].value_counts()
print(f"\nTotal top-level categories: {len(lvl1_counts)}")
print("\nTop 10 categories:")
for cat, count in lvl1_counts.head(10).items():
    print(f"  {cat}: {count:,} subcategories")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
