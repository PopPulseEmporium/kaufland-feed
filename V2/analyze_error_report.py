"""
Analyze ManoMano PIM Error Report

Parses the error CSV and categorizes all issues:
- Error type distribution
- Most common errors
- Problematic products
- Actionable recommendations
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import csv
import json
from collections import Counter, defaultdict
from typing import Dict, List

def parse_error_report(filepath: str) -> Dict:
    """Parse error report and categorize issues"""

    results = {
        'total_errors': 0,
        'error_types': Counter(),
        'category_errors': [],
        'brand_errors': [],
        'disallowed_errors': [],
        'random_design_products': [],
        'sku_errors': defaultdict(list),
        'sample_errors': defaultdict(list)
    }

    print("=" * 80)
    print("PARSING ERROR REPORT")
    print("=" * 80)
    print(f"\nReading: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                results['total_errors'] += 1

                sku = row.get('sku', 'Unknown')
                ean = row.get('ean', 'Unknown')
                errors = row.get('Errors', '')
                warnings = row.get('Warnings', '')
                error_msg = errors if errors else warnings  # Use errors first, fallback to warnings
                description = row.get('description', '')
                brand = row.get('brand', '')
                category = row.get('mm_category', '')

                # Categorize error
                error_category = categorize_error(error_msg)
                results['error_types'][error_category] += 1

                # Track specific error types
                if 'unverified brand' in error_msg.lower():
                    results['brand_errors'].append({
                        'sku': sku,
                        'ean': ean,
                        'brand': brand,
                        'error': error_msg
                    })

                if 'add a category' in error_msg.lower():
                    results['category_errors'].append({
                        'sku': sku,
                        'ean': ean,
                        'category': category,
                        'error': error_msg
                    })

                if 'disallowed' in error_msg.lower():
                    results['disallowed_errors'].append({
                        'sku': sku,
                        'ean': ean,
                        'error': error_msg
                    })

                # Check for "random design" products
                if 'aleatorio' in description.lower() or 'assortit' in description.lower():
                    results['random_design_products'].append({
                        'sku': sku,
                        'ean': ean,
                        'description_snippet': description[:200]
                    })

                # Track errors per SKU
                results['sku_errors'][sku].append(error_category)

                # Keep samples of each error type (max 5 per type)
                if len(results['sample_errors'][error_category]) < 5:
                    results['sample_errors'][error_category].append({
                        'sku': sku,
                        'ean': ean,
                        'error': error_msg,
                        'brand': brand,
                        'category': category
                    })

                # Progress indicator
                if results['total_errors'] % 1000 == 0:
                    print(f"  Processed {results['total_errors']:,} rows...")

    except Exception as e:
        print(f"\n❌ Error reading file: {e}")
        return None

    return results

def categorize_error(error_msg: str) -> str:
    """Categorize error message into types"""
    error_lower = error_msg.lower()

    if 'unverified brand' in error_lower:
        return 'BRAND_UNVERIFIED'
    elif 'add a category' in error_lower:
        return 'CATEGORY_MISSING'
    elif 'disallowed' in error_lower:
        return 'PRODUCT_DISALLOWED'
    elif 'price' in error_lower:
        return 'PRICE_ISSUE'
    elif 'image' in error_lower:
        return 'IMAGE_ISSUE'
    elif 'description' in error_lower:
        return 'DESCRIPTION_ISSUE'
    elif 'ean' in error_lower:
        return 'EAN_ISSUE'
    else:
        return 'OTHER'

def print_results(results: Dict):
    """Print analysis results"""

    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)

    # Overall stats
    print(f"\n📊 Total Errors: {results['total_errors']:,}")
    print(f"📦 Unique SKUs with Errors: {len(results['sku_errors']):,}")
    print(f"🎲 Random Design Products: {len(results['random_design_products']):,}")

    # Error type distribution
    print("\n" + "-" * 80)
    print("ERROR TYPE DISTRIBUTION:")
    print("-" * 80)

    for error_type, count in results['error_types'].most_common():
        percentage = (count / results['total_errors']) * 100
        print(f"  {error_type:25s} {count:6,} ({percentage:5.1f}%)")

    # Top error categories
    print("\n" + "-" * 80)
    print("TOP 3 ERROR CATEGORIES:")
    print("-" * 80)

    top_3 = results['error_types'].most_common(3)

    for i, (error_type, count) in enumerate(top_3, 1):
        print(f"\n{i}. {error_type} ({count:,} occurrences)")
        print(f"   Sample Errors:")

        for j, sample in enumerate(results['sample_errors'][error_type][:3], 1):
            print(f"\n   {i}.{j}. SKU: {sample['sku']}, EAN: {sample['ean']}")
            print(f"       Brand: {sample['brand']}")
            print(f"       Category: {sample['category']}")
            print(f"       Error: {sample['error'][:100]}...")

    # Random design products
    if results['random_design_products']:
        print("\n" + "-" * 80)
        print("🎲 RANDOM DESIGN PRODUCTS (Winning Box Type):")
        print("-" * 80)
        print(f"\nFound {len(results['random_design_products']):,} products with random/assorted designs")
        print("\nSample products:")

        for i, prod in enumerate(results['random_design_products'][:10], 1):
            print(f"\n  {i}. SKU: {prod['sku']}, EAN: {prod['ean']}")
            print(f"     Description: {prod['description_snippet']}...")

    # SKUs with multiple errors
    print("\n" + "-" * 80)
    print("SKUS WITH MULTIPLE ERROR TYPES:")
    print("-" * 80)

    multi_error_skus = {sku: errors for sku, errors in results['sku_errors'].items()
                        if len(set(errors)) > 1}

    if multi_error_skus:
        print(f"\nFound {len(multi_error_skus):,} SKUs with multiple error types")
        print("\nTop 10 SKUs by error variety:")

        sorted_skus = sorted(multi_error_skus.items(),
                            key=lambda x: len(set(x[1])), reverse=True)[:10]

        for sku, errors in sorted_skus:
            unique_errors = set(errors)
            print(f"  {sku}: {', '.join(unique_errors)}")
    else:
        print("\n✓ No SKUs with multiple error types")

def generate_recommendations(results: Dict):
    """Generate actionable recommendations"""

    print("\n" + "=" * 80)
    print("🔧 ACTIONABLE RECOMMENDATIONS")
    print("=" * 80)

    top_errors = results['error_types'].most_common(3)

    for i, (error_type, count) in enumerate(top_errors, 1):
        print(f"\n{i}. {error_type} ({count:,} products)")
        print("-" * 60)

        if error_type == 'BRAND_UNVERIFIED':
            print("   Issue: Products using brand 'Autres' are unverified")
            print("   Solutions:")
            print("   a) Extract actual brand from BigBuy API product data")
            print("   b) Map common brands to verified ManoMano brands")
            print("   c) Leave as 'Autres' and wait for ManoMano verification")
            print("\n   Recommended Action:")
            print("   - Check if BigBuy API provides brand field")
            print("   - Update manomano_feed_generator.py line 313 to use actual brand")
            print("   - Code change:")
            print("     OLD: 'brand': 'Autres'")
            print("     NEW: 'brand': product.get('brand', 'Autres')")

        elif error_type == 'CATEGORY_MISSING':
            print("   Issue: ManoMano cannot match provided category ID")
            print("   Possible Causes:")
            print("   a) Category ID doesn't exist in ManoMano taxonomy")
            print("   b) Category ID format incorrect")
            print("   c) Category not available in Italy marketplace")
            print("\n   Recommended Action:")
            print("   - Review CATEGORY_MAPPING (lines 24-36)")
            print("   - Verify each ManoMano category ID exists")
            print("   - Check against category tree.xlsx")
            print("   - Test with known-good category like 20204")

        elif error_type == 'PRODUCT_DISALLOWED':
            print("   Issue: Product doesn't meet ManoMano requirements")
            print("   Possible Causes:")
            print("   a) Restricted category")
            print("   b) Missing required fields")
            print("   c) Random/assorted design products (Winning Box type)")
            print(f"   d) {len(results['random_design_products']):,} products have 'random design' text")
            print("\n   Recommended Action:")
            print("   - Filter out 'random design' products")
            print("   - Add validation in ProductValidator.validate()")
            print("   - Code change:")
            print("     if 'aleatorio' in description.lower():")
            print("         return False, 'Random design product excluded'")

    # Overall recommendation
    print("\n" + "=" * 80)
    print("PRIORITY ACTION PLAN:")
    print("=" * 80)

    print("""
1. IMMEDIATE (Fix now):
   ✓ Filter out random/assorted design products
   ✓ Add description validation in ProductValidator

2. SHORT-TERM (Fix today):
   ✓ Verify all CATEGORY_MAPPING IDs against category tree.xlsx
   ✓ Test with subset of products to validate categories

3. MEDIUM-TERM (Fix this week):
   ✓ Extract and use actual brand from BigBuy API
   ✓ Create brand mapping for common brands

4. MONITORING:
   ✓ Re-upload feed after fixes
   ✓ Check if error count reduces
   ✓ Track which errors remain
""")

def save_detailed_report(results: Dict, output_file: str):
    """Save detailed JSON report"""

    # Convert Counter to dict for JSON serialization
    report = {
        'total_errors': results['total_errors'],
        'error_types': dict(results['error_types']),
        'category_errors_count': len(results['category_errors']),
        'brand_errors_count': len(results['brand_errors']),
        'disallowed_errors_count': len(results['disallowed_errors']),
        'random_design_products_count': len(results['random_design_products']),
        'unique_skus_with_errors': len(results['sku_errors']),
        'sample_errors': dict(results['sample_errors']),
        'random_design_sample': results['random_design_products'][:20]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed report saved to: {output_file}")

# Main execution
if __name__ == "__main__":
    input_file = "pim_error_report_40106998_a369c68b.csv"
    output_file = "error_analysis_report.json"

    # Parse error report
    results = parse_error_report(input_file)

    if results:
        # Print analysis
        print_results(results)

        # Generate recommendations
        generate_recommendations(results)

        # Save detailed report
        save_detailed_report(results, output_file)

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
    else:
        print("\n❌ Failed to analyze error report")
