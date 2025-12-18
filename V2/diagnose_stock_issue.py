"""
Diagnose stock issue for EAN 4711387067246
Check what the API actually returns vs what we show
"""

import requests
import os
import time
import json
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

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

# Initialize API
api_key = os.getenv('BIGBUY_API_KEY', 'YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ')
api = BigBuyAPI(api_key)

TARGET_EAN = "4711387067246"

print("="*80)
print(f"DIAGNOSING STOCK ISSUE FOR EAN: {TARGET_EAN}")
print("="*80)

# Step 1: Search for products by EAN (if API supports it)
# Let's check a specific category first
categories_to_check = [19651, 19656, 19657, 19661, 19658, 19652, 19664, 19653, 19756, 19654, 19666]

found_product = None
found_in_category = None

print("\nSearching for product across categories...")

for cat_id in categories_to_check:
    print(f"\nChecking category {cat_id}...")

    # Get products from category
    products = api._request(f"/rest/catalog/products.json?parentTaxonomy={cat_id}")

    if products:
        for product in products:
            if str(product.get('ean13')) == TARGET_EAN:
                found_product = product
                found_in_category = cat_id
                print(f"\n✓ FOUND PRODUCT in category {cat_id}!")
                break

    if found_product:
        break

    time.sleep(0.3)

if not found_product:
    print(f"\n✗ Product with EAN {TARGET_EAN} NOT FOUND in any category")
    print("Trying to get ALL products from first category for analysis...")

    # Get sample from first category to understand structure
    products = api._request(f"/rest/catalog/products.json?parentTaxonomy={categories_to_check[0]}")

    if products:
        print(f"\nSample product structure from category {categories_to_check[0]}:")
        print(json.dumps(products[0], indent=2))

        # Check if ANY products have this EAN
        all_eans = [str(p.get('ean13')) for p in products[:100]]
        print(f"\nSample EANs from first 100 products:")
        for ean in all_eans[:10]:
            print(f"  {ean}")

    exit()

print("\n" + "="*80)
print("PRODUCT DETAILS")
print("="*80)
print(json.dumps(found_product, indent=2))

product_id = found_product.get('id')
product_sku = found_product.get('sku')

print(f"\nProduct ID: {product_id}")
print(f"Product SKU: {product_sku}")
print(f"Product EAN: {found_product.get('ean13')}")

# Step 2: Get variations for this product
print("\n" + "="*80)
print("CHECKING VARIATIONS")
print("="*80)

variations = api._request(f"/rest/catalog/productsvariations.json?parentTaxonomy={found_in_category}")

product_variations = [v for v in variations if v.get('product') == product_id] if variations else []

print(f"\nVariations found for product {product_id}: {len(product_variations)}")

if product_variations:
    print("\nVariation details:")
    for i, var in enumerate(product_variations, 1):
        print(f"\n  Variant {i}:")
        print(f"    SKU: {var.get('sku')}")
        print(f"    EAN: {var.get('ean13')}")
        print(f"    Product ID: {var.get('product')}")
        print(json.dumps(var, indent=4))

# Step 3: Get PRODUCT stock (parent)
print("\n" + "="*80)
print("PRODUCT STOCK (PARENT)")
print("="*80)

product_stock_data = api._request(f"/rest/catalog/productsstockbyhandlingdays.json?parentTaxonomy={found_in_category}")

if product_stock_data:
    # Find stock for our SKU
    our_stock = [s for s in product_stock_data if s.get('sku') == product_sku]

    if our_stock:
        print(f"\nStock data for SKU {product_sku}:")
        print(json.dumps(our_stock[0], indent=2))

        # Calculate total
        total_stock = sum(s.get('quantity', 0) for s in our_stock[0].get('stocks', []))
        print(f"\nTotal parent stock: {total_stock}")
    else:
        print(f"\n✗ No stock data found for parent SKU {product_sku}")
        print(f"\nAll stock entries (first 5):")
        for s in product_stock_data[:5]:
            print(f"  SKU: {s.get('sku')} - Stocks: {s.get('stocks')}")
else:
    print("✗ No product stock data returned")

# Step 4: Get VARIANT stock
print("\n" + "="*80)
print("VARIANT STOCK")
print("="*80)

variant_stock_data = api._request(f"/rest/catalog/productsvariationsstockbyhandlingdays.json?parentTaxonomy={found_in_category}")

if variant_stock_data:
    print(f"\nTotal variant stock entries: {len(variant_stock_data)}")

    # Check if any variants belong to our product
    if product_variations:
        variant_skus = [v.get('sku') for v in product_variations]

        for var_sku in variant_skus:
            var_stock = [s for s in variant_stock_data if s.get('sku') == var_sku]

            if var_stock:
                total_var_stock = sum(s.get('quantity', 0) for s in var_stock[0].get('stocks', []))
                print(f"\nVariant SKU {var_sku}:")
                print(f"  Stock: {total_var_stock}")
                print(f"  Full data: {json.dumps(var_stock[0], indent=2)}")
else:
    print("✗ No variant stock data returned")

# Step 5: Simulate our stock calculation
print("\n" + "="*80)
print("SIMULATING OUR STOCK CALCULATION")
print("="*80)

def calculate_safe_quantity(bigbuy_stock: int) -> int:
    if bigbuy_stock <= 0:
        return 0
    elif bigbuy_stock <= 2:
        return 1
    elif bigbuy_stock <= 5:
        return min(2, bigbuy_stock - 1)
    elif bigbuy_stock <= 10:
        return min(5, bigbuy_stock - 2)
    elif bigbuy_stock <= 20:
        return min(10, bigbuy_stock - 3)
    elif bigbuy_stock <= 50:
        return min(25, bigbuy_stock - 5)
    else:
        return min(50, int(bigbuy_stock * 0.9))

# Build stock maps like we do in main script
prod_stock = {}
var_stock = {}

if product_stock_data:
    for item in product_stock_data:
        sku = item.get('sku')
        if sku:
            total = sum(s.get('quantity', 0) for s in item.get('stocks', []))
            prod_stock[sku] = total

if variant_stock_data:
    for item in variant_stock_data:
        sku = item.get('sku')
        if sku:
            total = sum(s.get('quantity', 0) for s in item.get('stocks', []))
            var_stock[sku] = total

print(f"\nProduct stock map for SKU {product_sku}: {prod_stock.get(product_sku, 0)}")
print(f"Safe quantity: {calculate_safe_quantity(prod_stock.get(product_sku, 0))}")

if product_variations:
    print("\nVariant stock:")
    for var in product_variations:
        var_sku = var.get('sku')
        raw_stock = var_stock.get(var_sku, 0)
        safe_stock = calculate_safe_quantity(raw_stock)
        print(f"  Variant SKU {var_sku}: Raw={raw_stock}, Safe={safe_stock}")

print("\n" + "="*80)
print("DIAGNOSIS COMPLETE")
print("="*80)
