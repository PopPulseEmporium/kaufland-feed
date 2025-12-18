import requests
import os
import time
from collections import Counter

class BigBuyAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    def _request(self, endpoint: str):
        url = f"{self.base_url}{endpoint}?t={int(time.time())}"
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

# Sample one category with variants
api_key = os.getenv('BIGBUY_API_KEY')
if not api_key:
    print("Set BIGBUY_API_KEY first")
    exit()

api = BigBuyAPI(api_key)

# Test category: 19651 (DIY & Tools - likely to have variants)
cat_id = 19651
print(f"🔍 Checking category {cat_id} for variant data...")
print("="*70)

# Get products
products = api._request(f"/rest/catalog/products.json?parentTaxonomy={cat_id}")
print(f"\n✅ Products: {len(products) if products else 0}")

# Get variations
variations = api._request(f"/rest/catalog/productsvariations.json?parentTaxonomy={cat_id}")
print(f"✅ Variations: {len(variations) if variations else 0}")

if variations and len(variations) > 0:
    print(f"\n🎉 VARIANTS EXIST! Analyzing structure...")
    
    # Group by parent
    by_parent = {}
    for var in variations:
        pid = var.get('product')
        by_parent.setdefault(pid, []).append(var)
    
    print(f"\n📊 Found {len(by_parent)} parent products with variants")
    
    # Show top 3 families
    top_families = sorted(by_parent.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    
    for parent_id, vars in top_families:
        print(f"\n{'='*70}")
        print(f"Parent Product ID: {parent_id}")
        print(f"Number of variants: {len(vars)}")
        
        # Find parent product
        parent = next((p for p in products if p.get('id') == parent_id), None)
        if parent:
            print(f"\nParent Details:")
            print(f"  SKU: {parent.get('sku')}")
            print(f"  EAN: {parent.get('ean13')}")
            print(f"  Price: €{parent.get('wholesalePrice')}")
            print(f"  Condition: {parent.get('condition')}")
        
        print(f"\nVariants:")
        for i, var in enumerate(vars[:5], 1):
            print(f"  {i}. Variant SKU: {var.get('sku')}")
            print(f"     EAN: {var.get('ean13')}")
            print(f"     Price: €{var.get('wholesalePrice', 'N/A')}")
            print(f"     Has own price: {'YES' if var.get('wholesalePrice') else 'NO'}")
            print(f"     Has dimensions: {bool(var.get('width') or var.get('height') or var.get('depth'))}")
        
        if len(vars) > 5:
            print(f"  ... and {len(vars)-5} more variants")
    
    # Get stock data
    print(f"\n{'='*70}")
    print("Checking variant stock...")
    var_stock = api._request(f"/rest/catalog/productsvariationsstockbyhandlingdays.json?parentTaxonomy={cat_id}")
    
    if var_stock:
        print(f"✅ Variant stock entries: {len(var_stock)}")
        
        # Check how many have actual stock
        with_stock = 0
        stock_amounts = []
        for vs in var_stock:
            total = sum(s.get('quantity', 0) for s in vs.get('stocks', []))
            if total > 0:
                with_stock += 1
                stock_amounts.append(total)
        
        print(f"   Variants with stock > 0: {with_stock}")
        if stock_amounts:
            print(f"   Stock range: {min(stock_amounts)} - {max(stock_amounts)}")
            print(f"   Average stock: {sum(stock_amounts)/len(stock_amounts):.1f}")
    
    # Show a sample variant with full data
    print(f"\n{'='*70}")
    print("SAMPLE VARIANT (full structure):")
    if variations:
        import json
        print(json.dumps(variations[0], indent=2))
    
else:
    print("\n❌ NO VARIANTS found in this category")
    print("Try another category or variants might be rare in BigBuy")

print(f"\n{'='*70}")
print("DIAGNOSIS COMPLETE")
print("="*70)