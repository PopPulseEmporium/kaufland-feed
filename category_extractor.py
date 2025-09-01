import requests
import json
import os
from datetime import datetime


def get_all_bigbuy_categories(api_key):
    """Extract complete BigBuy categories list"""

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        # Get ALL taxonomies
        response = requests.get(
            "https://api.bigbuy.eu/rest/catalog/taxonomies.json",
            headers=headers
        )

        if response.status_code == 200:
            taxonomies = response.json()

            print(f"✅ Found {len(taxonomies)} total categories")

            # Create organized structure
            categories_by_parent = {}
            all_categories = []

            for taxonomy in taxonomies:
                cat_info = {
                    'id': taxonomy.get('id'),
                    'name': taxonomy.get('name'),
                    'parent_id': taxonomy.get('parentTaxonomy'),
                    'url': taxonomy.get('url'),
                    'date_added': taxonomy.get('dateAdd'),
                    'date_updated': taxonomy.get('dateUpd')
                }

                all_categories.append(cat_info)

                # Group by parent for hierarchy
                parent_id = taxonomy.get('parentTaxonomy')
                if parent_id not in categories_by_parent:
                    categories_by_parent[parent_id] = []
                categories_by_parent[parent_id].append(cat_info)

            # Save complete list
            output_data = {
                "extraction_date": datetime.now().isoformat(),
                "total_categories": len(taxonomies),
                "all_categories": all_categories,
                "hierarchy": categories_by_parent
            }

            # Save as JSON
            with open('bigbuy_all_categories.json', 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            # Create readable text file
            with open('bigbuy_categories_readable.txt', 'w', encoding='utf-8') as f:
                f.write("COMPLETE BIGBUY CATEGORIES LIST\n")
                f.write("=" * 50 + "\n")
                f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Categories: {len(taxonomies)}\n\n")

                # Top-level categories first
                f.write("TOP-LEVEL CATEGORIES (no parent):\n")
                f.write("-" * 40 + "\n")

                top_level = [cat for cat in all_categories if cat['parent_id'] is None]
                for cat in sorted(top_level, key=lambda x: x['name']):
                    f.write(f"ID: {cat['id']:>6} | {cat['name']}\n")

                f.write(f"\nALL CATEGORIES (sorted by name):\n")
                f.write("-" * 40 + "\n")

                for cat in sorted(all_categories, key=lambda x: x['name']):
                    parent_info = f" (Parent: {cat['parent_id']})" if cat['parent_id'] else " (TOP-LEVEL)"
                    f.write(f"ID: {cat['id']:>6} | {cat['name']}{parent_info}\n")

            # Print summary to console
            print(f"\n📊 CATEGORY BREAKDOWN:")
            top_level_count = len([cat for cat in all_categories if cat['parent_id'] is None])
            sub_categories = len(all_categories) - top_level_count

            print(f"   📁 Top-level categories: {top_level_count}")
            print(f"   📂 Sub-categories: {sub_categories}")
            print(f"   📋 Total categories: {len(all_categories)}")

            print(f"\n📁 Files created:")
            print(f"   📄 bigbuy_all_categories.json (complete data)")
            print(f"   📝 bigbuy_categories_readable.txt (human readable)")

            # Show some sample categories
            print(f"\n📝 SAMPLE TOP-LEVEL CATEGORIES:")
            sample_top = sorted(top_level, key=lambda x: x['name'])[:10]
            for cat in sample_top:
                print(f"   {cat['id']:>6}: {cat['name']}")

            if len(top_level) > 10:
                print(f"   ... and {len(top_level) - 10} more")

            return all_categories

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Main function to extract BigBuy categories"""
    print("🔍 BIGBUY CATEGORIES EXTRACTOR")
    print("=" * 50)

    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found in BIGBUY_API_KEY environment variable")
        return

    print(f"🔑 API key found (length: {len(api_key)})")

    # Extract categories
    print("\n🔄 Extracting all BigBuy categories...")
    categories = get_all_bigbuy_categories(api_key)

    if categories:
        print(f"\n✅ SUCCESS! Extracted {len(categories)} categories")
        print("\nCheck the generated files for the complete list!")
    else:
        print("\n❌ Failed to extract categories")


if __name__ == "__main__":
    main()
