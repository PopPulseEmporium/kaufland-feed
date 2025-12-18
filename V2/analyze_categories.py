"""
Analyze ManoMano category tree to understand structure
and find the right category mappings
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd

df = pd.read_excel('category tree.xlsx')

print('=' * 80)
print('MANOMANO CATEGORY STRUCTURE ANALYSIS')
print('=' * 80)

# Basic stats
print(f'\nTotal rows: {len(df):,}')
print(f'Unique CATEGORY_IDs: {df["CATEGORY_ID"].nunique():,}')

# Depth distribution
print('\nCategory depth distribution:')
df['depth'] = 1
df.loc[pd.notna(df['S_CATEGORY_LVL_2_NAME']), 'depth'] = 2
df.loc[pd.notna(df['S_CATEGORY_LVL_3_NAME']), 'depth'] = 3
df.loc[pd.notna(df['S_CATEGORY_LVL_4_NAME']), 'depth'] = 4

print(df['depth'].value_counts().sort_index())

# Level 1 categories (no Level 2)
print('\n' + '=' * 80)
print('LEVEL 1 CATEGORIES (Root categories)')
print('=' * 80)

level1_cats = df[pd.isna(df['S_CATEGORY_LVL_2_NAME'])][['CATEGORY_ID', 'S_CATEGORY_LVL_1_NAME']].drop_duplicates().sort_values('CATEGORY_ID')

print(f'\nFound {len(level1_cats)} Level 1 categories:')
for idx, row in level1_cats.iterrows():
    print(f'  {row["CATEGORY_ID"]}: {row["S_CATEGORY_LVL_1_NAME"]}')

# Current mappings analysis
print('\n' + '=' * 80)
print('CURRENT MAPPING ANALYSIS')
print('=' * 80)

our_mappings = {
    19651: ("21542", "DIY & Tools"),
    19656: ("20204", "Home & Kitchen"),
    19657: ("20446", "Lighting"),
    19661: ("19596", "Garden"),
    19658: ("21294", "Industrial"),
    19652: ("21294", "Automotive"),
    19664: ("20204", "Office"),
    19653: ("21092", "Electronics"),
    19756: ("19596", "Sports & Outdoor"),
    19654: ("20204", "Luggage"),
    19666: ("20946", "Pet Products"),
}

df['CATEGORY_ID'] = df['CATEGORY_ID'].astype(str)

print('\nCurrent mappings:')
for bigbuy_id, (manomano_id, desc) in our_mappings.items():
    matches = df[df['CATEGORY_ID'] == manomano_id]
    if len(matches) > 0:
        row = matches.iloc[0]
        depth = 1
        if pd.notna(row.get('S_CATEGORY_LVL_2_NAME')): depth = 2
        if pd.notna(row.get('S_CATEGORY_LVL_3_NAME')): depth = 3
        if pd.notna(row.get('S_CATEGORY_LVL_4_NAME')): depth = 4

        print(f'\n  BigBuy {bigbuy_id} ({desc})')
        print(f'    → ManoMano {manomano_id} (Level {depth})')
        print(f'    Path: {row["S_CATEGORY_LVL_1_NAME"]}', end='')
        if depth >= 2: print(f' > {row["S_CATEGORY_LVL_2_NAME"]}', end='')
        if depth >= 3: print(f' > {row["S_CATEGORY_LVL_3_NAME"]}', end='')
        if depth >= 4: print(f' > {row["S_CATEGORY_LVL_4_NAME"]}', end='')
        print()

        if depth > 2:
            print(f'    ⚠️  WARNING: Very specific subcategory (Level {depth})')

# Recommended mappings
print('\n' + '=' * 80)
print('RECOMMENDED CATEGORY MAPPINGS')
print('=' * 80)

print('\nBased on analysis:')
print('  - Use Level 1 categories where available')
print('  - Avoid deep subcategories (Level 3-4)')
print('  - Map to broader categories')

print('\nRecommended changes:')

# DIY & Tools → Utensileria doesn't have Level 1, use Edilizia or keep broad category
print('\n  19651 (DIY & Tools):')
print('    PROBLEM: Current 21542 is Level 4 (Spazzole in carbone - Carbon brushes)')
print('    OPTIONS:')
print('      - Keep 21542 but products may be rejected')
print('      - Use 20763 (Edilizia, materiali da costruzione) - Level 1')
print('      - Use 20832 (Falegnameria - Woodworking) - Level 1')
print('    RECOMMEND: Try removing from mapping (exclude these products)')

# Industrial/Automotive → Ferramenta doesn't have Level 1
print('\n  19658/19652 (Industrial/Automotive):')
print('    PROBLEM: Current 21294 is Level 4 (Legatrici - Binding tools)')
print('    OPTIONS:')
print('      - Use 20763 (Edilizia, materiali da costruzione) - Level 1')
print('      - Use 20832 (Falegnameria) - Level 1')
print('    RECOMMEND: Use 20763 (Construction materials)')

# Others are OK
print('\n  Others (Home, Garden, Lighting, etc):')
print('    ✓ Already using Level 1 categories - should work')

# Find broader alternatives
print('\n' + '=' * 80)
print('ALTERNATIVE LEVEL 1 CATEGORIES')
print('=' * 80)

print('\nIf you need to map DIY/Tools/Hardware products:')
print('  - 20763: Edilizia, materiali da costruzione (Construction)')
print('  - 20832: Falegnameria (Woodworking)')
print('  - 20515: Elettrodomestici (Appliances)')
print('  - 21092: Elettricità (Electrical) - already using')

# Check if there are any subcategories we can use
print('\n' + '=' * 80)
print('EXPLORING SUBCATEGORY OPTIONS')
print('=' * 80)

# Check what Level 2 categories exist for categories we care about
for lvl1_name in ['Edilizia, materiali da costruzione', 'Falegnameria']:
    level2 = df[
        (df['S_CATEGORY_LVL_1_NAME'] == lvl1_name) &
        pd.notna(df['S_CATEGORY_LVL_2_NAME']) &
        pd.isna(df['S_CATEGORY_LVL_3_NAME'])
    ][['CATEGORY_ID', 'S_CATEGORY_LVL_2_NAME']].drop_duplicates()

    if len(level2) > 0:
        print(f'\n{lvl1_name} - Level 2 subcategories:')
        for idx, row in level2.head(10).iterrows():
            print(f'  {row["CATEGORY_ID"]}: {row["S_CATEGORY_LVL_2_NAME"]}')

print('\n' + '=' * 80)
print('ANALYSIS COMPLETE')
print('=' * 80)
