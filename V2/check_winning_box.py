"""
Check for "Winning Box" or mystery/surprise box products in BigBuy

These are products where customers receive random items.
They may have special flags or naming patterns.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import os
import time
import json
from collections import Counter

class BigBuyAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint: str):
        separator = '&' if '?' in endpoint else '?'
        url = f"{self.base_url}{endpoint}{separator}t={int(time.time())}"
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Error: {e}")
            return None

# Initialize
api_key = os.getenv('BIGBUY_API_KEY', 'YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ')
api = BigBuyAPI(api_key)

print("="*80)
print("SEARCHING FOR 'WINNING BOX' TYPE PRODUCTS")
print("="*80)

# Categories to check
categories_to_check = [19651, 19656, 19657, 19661, 19658, 19652, 19664, 19653, 19756, 19654, 19666]

# Keywords that might indicate mystery/surprise boxes
keywords = [
    'winning', 'box', 'surprise', 'mystery', 'random', 'lucky',
    'mixed', 'assorted', 'variety', 'pack', 'bundle'
]

print("\nSearching for products containing keywords:")
print(f"  {', '.join(keywords)}\n")

found_products = []
total_products = 0

for cat_id in categories_to_check:
    print(f"\nChecking category {cat_id}...")

    # Get products
    products = api._request(f"/rest/catalog/products.json?parentTaxonomy={cat_id}")
    if not products:
        continue

    # Get product info (with descriptions)
    info = api._request(f"/rest/catalog/productsinformation.json?isoCode=it&parentTaxonomy={cat_id}")
    if not info:
        info = []

    # Build info map
    info_map = {item['sku']: item for item in info}

    total_products += len(products)

    # Search for keywords
    for product in products:
        sku = product.get('sku')
        product_info = info_map.get(sku, {})

        name = product_info.get('name', '').lower()
        description = product_info.get('description', '').lower()

        # Check if any keyword is in name or description
        matches = []
        for keyword in keywords:
            if keyword in name or keyword in description:
                matches.append(keyword)

        if matches:
            found_products.append({
                'sku': sku,
                'ean': product.get('ean13'),
                'name': product_info.get('name', 'Unknown'),
                'description': product_info.get('description', '')[:200],  # First 200 chars
                'price': product.get('wholesalePrice'),
                'category': cat_id,
                'keywords_found': matches,
                'product_fields': product  # Full product data
            })

    time.sleep(0.3)

print("\n" + "="*80)
print("RESULTS")
print("="*80)

print(f"\nTotal products scanned: {total_products}")
print(f"Products matching keywords: {len(found_products)}")

if found_products:
    print("\n" + "-"*80)
    print("MATCHED PRODUCTS:")
    print("-"*80)

    for i, prod in enumerate(found_products[:20], 1):  # Show first 20
        print(f"\n{i}. {prod['name']}")
        print(f"   SKU: {prod['sku']}")
        print(f"   EAN: {prod['ean']}")
        print(f"   Price: €{prod['price']}")
        print(f"   Keywords: {', '.join(prod['keywords_found'])}")
        print(f"   Description: {prod['description'][:100]}...")

    if len(found_products) > 20:
        print(f"\n... and {len(found_products) - 20} more")

    # Analyze keywords
    print("\n" + "="*80)
    print("KEYWORD FREQUENCY:")
    print("="*80)

    keyword_counts = Counter()
    for prod in found_products:
        for kw in prod['keywords_found']:
            keyword_counts[kw] += 1

    for kw, count in keyword_counts.most_common():
        print(f"  {kw}: {count} products")

    # Check product structure for special flags
    print("\n" + "="*80)
    print("ANALYZING PRODUCT FIELDS:")
    print("="*80)

    if found_products:
        sample = found_products[0]['product_fields']
        print("\nSample product fields:")
        for key in sorted(sample.keys()):
            print(f"  {key}: {sample[key]}")

        # Look for potential flags
        print("\n" + "-"*80)
        print("Checking for special flags/fields:")
        print("-"*80)

        special_fields = ['winning', 'box', 'surprise', 'mystery', 'random', 'type', 'category_type', 'product_type']
        for field in special_fields:
            if field in sample:
                print(f"  ✓ Found field: {field} = {sample[field]}")

    # Save to JSON
    with open('winning_box_products.json', 'w', encoding='utf-8') as f:
        json.dump(found_products, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Full data saved to: winning_box_products.json")

else:
    print("\n✓ No 'Winning Box' type products found")
    print("  (This is good - these products may cause customer issues)")

print("\n" + "="*80)
print("RECOMMENDATION:")
print("="*80)

print("""
If 'Winning Box' or mystery box products were found:

1. Check if they need special handling
2. Consider filtering them out from feed
3. Add flag check in validation

BigBuy API fields to check:
- Product name (already checked)
- Product description (already checked)
- Product 'tags' field (if available)
- Product 'type' field (if available)
- Category-specific flags

To filter them out, add to ProductValidator.validate():
    if 'winning' in info.get('name', '').lower():
        return False, "Winning box product excluded"
""")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
