import requests
import json
import os
import time
from collections import Counter
from typing import Dict, List, Optional


class BigBuyAPI:
    """Simplified BigBuy API client"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint: str) -> Optional[List]:
        """Make API request with error handling"""
        separator = '&' if '?' in endpoint else '?'
        url = f"{self.base_url}{endpoint}{separator}t={int(time.time())}"
        try:
            r = requests.get(url, headers=self.headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error ({endpoint}): {e}")
            return None

    def get_all_categories(self) -> List[Dict]:
        """Get ALL categories (not just first level)"""
        print("📡 Fetching all categories...")
        result = self._request("/rest/catalog/taxonomies.json")
        return result or []

    def get_category_tree(self, taxonomy_id: int) -> Optional[Dict]:
        """Get specific category with its children"""
        print(f"📡 Fetching category tree for ID {taxonomy_id}...")
        result = self._request(f"/rest/catalog/taxonomy/{taxonomy_id}.json")
        return result

    def get_sample_products(self, limit: int = 100) -> List[Dict]:
        """Get sample products to analyze conditions"""
        print(f"📡 Fetching {limit} sample products...")
        result = self._request(f"/rest/catalog/products.json?pageSize={limit}")
        return result or []

    def get_sample_variations(self, taxonomy_id: int) -> List[Dict]:
        """Get sample variations from a category"""
        print(f"📡 Fetching variations for taxonomy {taxonomy_id}...")
        result = self._request(f"/rest/catalog/productsvariations.json?parentTaxonomy={taxonomy_id}")
        return result or []

    def get_variation_stock(self, taxonomy_id: int) -> List[Dict]:
        """Get variation stock data"""
        print(f"📡 Fetching variation stock for taxonomy {taxonomy_id}...")
        result = self._request(f"/rest/catalog/productsvariationsstockbyhandlingdays.json?parentTaxonomy={taxonomy_id}")
        return result or []


def analyze_conditions(products: List[Dict]) -> None:
    """Analyze product conditions"""
    print("\n" + "="*70)
    print("📊 PRODUCT CONDITIONS ANALYSIS")
    print("="*70)
    
    conditions = Counter(p.get('condition', 'UNKNOWN') for p in products)
    
    print(f"\nTotal products sampled: {len(products)}")
    print(f"\nConditions found:")
    for condition, count in conditions.most_common():
        percentage = (count / len(products)) * 100
        print(f"  • {condition}: {count} ({percentage:.1f}%)")
    
    # Show example products for each condition
    print(f"\n📦 Example products by condition:")
    seen_conditions = set()
    for product in products:
        condition = product.get('condition', 'UNKNOWN')
        if condition not in seen_conditions:
            seen_conditions.add(condition)
            print(f"\n  {condition}:")
            print(f"    SKU: {product.get('sku')}")
            print(f"    EAN: {product.get('ean13')}")
            print(f"    Price: {product.get('wholesalePrice')} EUR")
            if len(seen_conditions) >= len(conditions):
                break


def analyze_categories(categories: List[Dict]) -> None:
    """Analyze and display category structure"""
    print("\n" + "="*70)
    print("📁 CATEGORY STRUCTURE ANALYSIS")
    print("="*70)
    
    print(f"\nTotal categories: {len(categories)}")
    
    if not categories:
        print("❌ No categories found!")
        return
    
    # Examine structure of first few categories
    print("\n🔍 Sample category structure (first 3):")
    for i, cat in enumerate(categories[:3], 1):
        print(f"\n  Category {i}:")
        print(f"    ID: {cat.get('id')}")
        print(f"    Name: {cat.get('name')}")
        print(f"    Parent Taxonomy: {cat.get('parentTaxonomy', 'None (ROOT)')}")
        print(f"    All keys: {list(cat.keys())}")
    
    # Find ROOT categories (no parent)
    root_categories = [c for c in categories if not c.get('parentTaxonomy')]
    
    print(f"\n🌳 ROOT CATEGORIES (Top-level): {len(root_categories)}")
    
    # Build hierarchy levels
    cat_by_id = {c['id']: c for c in categories}
    
    def get_level(cat):
        """Calculate category level in hierarchy"""
        level = 0
        current = cat
        while current.get('parentTaxonomy'):
            level += 1
            parent_id = current.get('parentTaxonomy')
            if parent_id not in cat_by_id:
                break
            current = cat_by_id[parent_id]
            if level > 10:  # Prevent infinite loops
                break
        return level
    
    # Calculate levels
    for cat in categories:
        cat['calculated_level'] = get_level(cat)
    
    by_level = {}
    for cat in categories:
        level = cat.get('calculated_level', 0)
        by_level.setdefault(level, []).append(cat)
    
    print(f"\n📊 Categories by hierarchy level:")
    for level in sorted(by_level.keys()):
        print(f"  Level {level}: {len(by_level[level])} categories")
    
    # Display ROOT categories
    print("\n" + "="*70)
    print(f"🏷️  TOP-LEVEL (ROOT) CATEGORIES ({len(root_categories)})")
    print("="*70)
    print(f"\n{'ID':<12} {'Name':<60}")
    print("-" * 74)
    
    for cat in sorted(root_categories, key=lambda x: x.get('name', '')):
        cat_id = str(cat.get('id', '')).ljust(12)
        name = cat.get('name', 'Unknown')[:60]
        print(f"{cat_id} {name}")
    
    # Save full category tree to JSON for detailed review
    output_file = 'bigbuy_categories_full.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Full category data saved to: {output_file}")


def analyze_variants(variations: List[Dict], stock_data: List[Dict], products: List[Dict]) -> None:
    """Analyze variant structure and relationships"""
    print("\n" + "="*70)
    print("🔀 VARIANTS ANALYSIS")
    print("="*70)
    
    print(f"\nTotal variations found: {len(variations)}")
    
    if not variations:
        print("⚠️  No variations found in sample. Try a different category.")
        return
    
    # Group by parent product
    by_parent = {}
    for var in variations:
        parent_id = var.get('product')
        by_parent.setdefault(parent_id, []).append(var)
    
    print(f"Total parent products with variants: {len(by_parent)}")
    
    # Find products with most variants
    most_variants = sorted(by_parent.items(), key=lambda x: len(x[1]), reverse=True)[:3]
    
    print(f"\n📦 Products with most variants:")
    for parent_id, vars in most_variants:
        print(f"\n  Parent Product ID: {parent_id}")
        print(f"  Number of variants: {len(vars)}")
        
        # Find parent product details
        parent = next((p for p in products if p.get('id') == parent_id), None)
        if parent:
            print(f"  Parent SKU: {parent.get('sku')}")
            print(f"  Parent EAN: {parent.get('ean13')}")
            print(f"  Parent Price: {parent.get('wholesalePrice')} EUR")
        
        print(f"\n  Variants:")
        for var in vars[:5]:  # Show first 5 variants
            print(f"    • Variant SKU: {var.get('sku')}")
            print(f"      Variant EAN: {var.get('ean13')}")
            print(f"      Intrastat: {var.get('intrastatCode', 'N/A')}")
            
            # Check if variant has own price or other fields
            var_keys = [k for k in var.keys() if k not in ['id', 'sku', 'product', 'ean13', 'intrastatCode']]
            if var_keys:
                print(f"      Other fields: {', '.join(var_keys)}")
    
    # Analyze stock structure
    print(f"\n📊 Variant Stock Analysis:")
    if stock_data:
        print(f"  Stock entries found: {len(stock_data)}")
        
        # Show example stock structure
        if stock_data:
            example = stock_data[0]
            print(f"\n  Example stock entry:")
            print(f"    SKU: {example.get('sku')}")
            print(f"    Stocks: {json.dumps(example.get('stocks', []), indent=6)}")
    else:
        print("  ⚠️  No stock data found")
    
    # Save sample data
    output_file = 'bigbuy_variants_sample.json'
    sample_data = {
        'variations': variations[:20],
        'stock': stock_data[:20],
        'parent_products': [p for p in products if p.get('id') in [v.get('product') for v in variations[:20]]]
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Sample variant data saved to: {output_file}")


def suggest_manomano_categories(categories: List[Dict]) -> None:
    """Suggest categories relevant for ManoMano"""
    print("\n" + "="*70)
    print("💡 SUGGESTED MANOMANO-RELEVANT CATEGORIES")
    print("="*70)
    
    # Keywords that indicate ManoMano relevance
    relevant_keywords = [
        'tool', 'garden', 'hardware', 'building', 'construction',
        'plumbing', 'electrical', 'lighting', 'paint', 'door',
        'window', 'heating', 'ventilation', 'safety', 'workshop',
        'drill', 'saw', 'hammer', 'screw', 'nail', 'wood',
        'metal', 'outdoor', 'lawn', 'fence', 'tile', 'flooring',
        'bathroom', 'kitchen', 'diy', 'repair', 'maintenance',
        'decor', 'furniture', 'home', 'house', 'interior',
        # Spanish/Italian equivalents
        'herramienta', 'jardin', 'ferramenta', 'giardino', 'bagno',
        'cucina', 'casa', 'hogar', 'construccion', 'costruzione'
    ]
    
    irrelevant_keywords = [
        'fashion', 'clothing', 'toy', 'game', 'book', 'media',
        'food', 'beverage', 'cosmetic', 'beauty', 'phone', 'computer',
        'tablet', 'laptop', 'tv', 'audio', 'video', 'camera',
        'sport', 'fitness', 'jewelry', 'watch', 'bag', 'shoe',
        'baby', 'infant', 'child', 'pet', 'animal',
        # Spanish/Italian equivalents
        'moda', 'ropa', 'gioco', 'juguete', 'libro', 'comida',
        'belleza', 'telefono', 'ordenador', 'deporte', 'joya',
        'bebe', 'bambino', 'mascota', 'animale'
    ]
    
    # Use ALL categories (no active field exists)
    # Focus on root categories (level 0) for main categorization
    root_cats = [c for c in categories if not c.get('parentTaxonomy')]
    
    relevant = []
    maybe = []
    irrelevant = []
    
    for cat in root_cats:
        name_lower = cat.get('name', '').lower()
        
        relevant_match = any(kw in name_lower for kw in relevant_keywords)
        irrelevant_match = any(kw in name_lower for kw in irrelevant_keywords)
        
        if relevant_match and not irrelevant_match:
            relevant.append(cat)
        elif irrelevant_match:
            irrelevant.append(cat)
        else:
            maybe.append(cat)
    
    print(f"\n✅ LIKELY RELEVANT ({len(relevant)}):")
    for cat in sorted(relevant, key=lambda x: x.get('name', '')):
        print(f"  [{cat.get('id')}] {cat.get('name')}")
    
    print(f"\n❓ MAYBE RELEVANT ({len(maybe)}) - Review manually:")
    for cat in sorted(maybe, key=lambda x: x.get('name', '')):
        print(f"  [{cat.get('id')}] {cat.get('name')}")
    
    print(f"\n❌ LIKELY NOT RELEVANT ({len(irrelevant)}):")
    for cat in sorted(irrelevant, key=lambda x: x.get('name', '')):
        print(f"  [{cat.get('id')}] {cat.get('name')}")
    
    # Save category suggestions
    output_file = 'manomano_category_suggestions.json'
    suggestions = {
        'relevant': [{'id': c.get('id'), 'name': c.get('name')} for c in relevant],
        'maybe': [{'id': c.get('id'), 'name': c.get('name')} for c in maybe],
        'irrelevant': [{'id': c.get('id'), 'name': c.get('name')} for c in irrelevant]
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(suggestions, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Category suggestions saved to: {output_file}")


def main():
    print("🔍 BIGBUY API DISCOVERY TOOL")
    print("="*70)
    
    api_key = "YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"
    if not api_key:
        print("❌ BIGBUY_API_KEY environment variable not set")
        return
    
    api = BigBuyAPI(api_key)
    
    # 1. Analyze product conditions
    print("\n🔄 Step 1: Analyzing product conditions...")
    products = api.get_sample_products(500)  # Get more samples for better coverage
    if products:
        analyze_conditions(products)
    else:
        print("❌ Could not fetch products")
    
    time.sleep(1)
    
    # 2. Analyze categories
    print("\n🔄 Step 2: Analyzing category structure...")
    categories = api.get_all_categories()
    if categories:
        analyze_categories(categories)
        suggest_manomano_categories(categories)
    else:
        print("❌ Could not fetch categories")
    
    time.sleep(1)
    
    # 3. Analyze variants (pick a category likely to have variants)
    print("\n🔄 Step 3: Analyzing variant structure...")
    if categories:
        # Get root categories (no parent)
        root_cats = [c for c in categories if not c.get('parentTaxonomy')]
        if root_cats:
            # Pick first root category
            sample_cat = root_cats[0]
            print(f"Using sample category: {sample_cat.get('name')} (ID: {sample_cat.get('id')})")
            
            variations = api.get_sample_variations(sample_cat['id'])
            stock_data = api.get_variation_stock(sample_cat['id'])
            
            if variations or stock_data:
                analyze_variants(variations, stock_data, products)
            else:
                print("⚠️  No variants found in this category. Trying another...")
                # Try second category if available
                if len(root_cats) > 1:
                    sample_cat = root_cats[1]
                    print(f"Trying: {sample_cat.get('name')} (ID: {sample_cat.get('id')})")
                    variations = api.get_sample_variations(sample_cat['id'])
                    stock_data = api.get_variation_stock(sample_cat['id'])
                    if variations or stock_data:
                        analyze_variants(variations, stock_data, products)
                    else:
                        print("⚠️  No variants found. Variants may be sparse in BigBuy.")
    
    print("\n" + "="*70)
    print("✅ DISCOVERY COMPLETE")
    print("="*70)
    print("\nGenerated files:")
    print("  • bigbuy_categories_full.json - Complete category tree")
    print("  • manomano_category_suggestions.json - Category recommendations")
    print("  • bigbuy_variants_sample.json - Sample variant data (if found)")
    print("\nNext steps:")
    print("  1. Review category suggestions")
    print("  2. Check if REFURBISHED condition exists")
    print("  3. Examine variant structure for feed generation")


if __name__ == "__main__":
    main()