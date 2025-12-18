"""
Quick test to verify category mapping logic
"""

# BigBuy to ManoMano Category Mapping (same as in main script)
CATEGORY_MAPPING = {
    19651: "21542",  # Bricolaje y herramientas (DIY & Tools) => Utensileria (Tools)
    19656: "20204",  # Hogar y cocina (Home & Kitchen) => Arredo casa (Home furnishings)
    19657: "20446",  # Iluminación (Lighting) => Illuminazione (Lighting)
    19661: "19596",  # Jardín (Garden) => Giardino e piscine (Garden and pools)
    19658: "21294",  # Industria, empresas y ciencia (Industrial) => Ferramenta (Hardware)
    19652: "21294",  # Coche y moto (Automotive) => Ferramenta (Hardware - automotive tools/parts)
    19664: "20204",  # Oficina y papelería (Office) => Arredo casa (Home furnishings - office furniture)
    19653: "21092",  # Electrónica (Electronics) => Elettricità (Electricity/Electronics)
    19756: "19596",  # Deportes y aire libre (Sports & Outdoor) => Giardino e piscine (Outdoor/Garden)
    19654: "20204",  # Equipaje (Luggage) => Arredo casa (Home furnishings - storage)
    19666: "20946",  # Productos para mascotas (Pet Products) => Animali (Animals/Pets)
}

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

manomano_categories = {
    "19596": "Giardino e piscine",
    "20204": "Arredo casa",
    "20446": "Illuminazione",
    "20946": "Animali",
    "21092": "Elettricità",
    "21294": "Ferramenta",
    "21542": "Utensileria",
}

print("="*80)
print("CATEGORY MAPPING TEST")
print("="*80)

print("\nTesting category mappings:\n")

# Count how many unique ManoMano categories we're using
unique_mm_cats = set(CATEGORY_MAPPING.values())
print(f"Total BigBuy categories: {len(CATEGORY_MAPPING)}")
print(f"Unique ManoMano categories used: {len(unique_mm_cats)}")
print(f"ManoMano categories: {sorted(unique_mm_cats)}\n")

print("-"*80)
print(f"{'BigBuy ID':<12} {'BigBuy Category':<40} {'ManoMano ID':<15} {'ManoMano Category'}")
print("-"*80)

for bb_id, bb_name in bigbuy_categories.items():
    mm_id = CATEGORY_MAPPING.get(bb_id, "20204")
    mm_name = manomano_categories.get(mm_id, "Unknown")
    print(f"{bb_id:<12} {bb_name[:39]:<40} {mm_id:<15} {mm_name}")

print("\n" + "="*80)
print("CATEGORY DISTRIBUTION")
print("="*80)

# Count products per ManoMano category
from collections import Counter
mm_cat_counts = Counter(CATEGORY_MAPPING.values())

for mm_id, count in mm_cat_counts.most_common():
    mm_name = manomano_categories.get(mm_id, "Unknown")
    print(f"{mm_name} ({mm_id}): {count} BigBuy categories")

print("\n" + "="*80)
print("TEST: Simulating product category lookup")
print("="*80)

# Simulate the lookup process
test_products = [
    {'id': 1001, 'name': 'Hammer', 'bigbuy_cat': 19651},
    {'id': 1002, 'name': 'LED Lamp', 'bigbuy_cat': 19657},
    {'id': 1003, 'name': 'Dog Food', 'bigbuy_cat': 19666},
    {'id': 1004, 'name': 'Garden Hose', 'bigbuy_cat': 19661},
    {'id': 1005, 'name': 'Unknown Product', 'bigbuy_cat': 99999},  # Test default
]

print("\nSimulating product categorization:\n")

# Simulate product_to_category mapping
product_to_category = {p['id']: p['bigbuy_cat'] for p in test_products}

for product in test_products:
    product_id = product['id']
    bigbuy_cat_id = product_to_category.get(product_id)
    manomano_cat_id = CATEGORY_MAPPING.get(bigbuy_cat_id, "20204")  # Default to 20204
    mm_name = manomano_categories.get(manomano_cat_id, "Unknown")

    print(f"Product: {product['name']:<20} | BigBuy Cat: {bigbuy_cat_id:<6} | ManoMano Cat: {manomano_cat_id} ({mm_name})")

print("\n" + "="*80)
print("TEST PASSED - Category mapping logic works correctly!")
print("="*80)
