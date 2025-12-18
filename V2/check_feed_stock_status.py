"""
Check Stock Status for Existing Feed

Reads products from an existing feed CSV (e.g., kaufland_feed.csv) and checks
which products are still in stock vs out of stock.

This helps identify:
- Products that need to be removed from marketplace (out of stock)
- Products that are still available
- Overall feed health

Usage:
    python check_feed_stock_status.py kaufland_feed.csv
    python check_feed_stock_status.py kaufland_feed.csv --all-stock
    python check_feed_stock_status.py kaufland_feed.csv --out-of-stock-only

Options:
    --all-stock           Check all warehouses (not just 0-2 day handling)
    --out-of-stock-only   Only show products that are out of stock
"""

import os
import sys
import csv
import requests
from typing import Dict, List, Set
from dataclasses import dataclass

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class FeedProduct:
    """Product from feed"""
    sku: str
    ean: str
    title: str
    category: str
    price: float
    quantity_in_feed: int


@dataclass
class StockStatus:
    """Stock status comparison"""
    sku: str
    title: str
    was_quantity: int  # Quantity in feed
    now_fast_stock: int  # Current fast stock (0-2 days)
    now_total_stock: int  # Current total stock (all warehouses)
    status: str  # "in_stock", "out_of_stock", "not_found"


class FeedStockChecker:
    """Check stock status for feed products"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint: str) -> dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API Error ({endpoint}): {e}")
            return None

    def load_feed_products(self, csv_file: str) -> List[FeedProduct]:
        """Load products from feed CSV (supports Kaufland and ManoMano formats)"""
        print(f"\n📂 Loading products from {csv_file}...")

        products = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Detect feed format by checking column names
                first_row = next(reader)
                f.seek(0)
                next(reader)  # Skip header again

                # Determine format
                is_kaufland = 'id_offer' in first_row
                is_manomano = 'sku' in first_row and 'product_price_vat_inc' in first_row

                if is_kaufland:
                    print("   📋 Detected format: Kaufland")
                    sku_col = 'id_offer'
                    title_col = 'title'
                    category_col = 'category'
                    price_col = 'real_price'
                    quantity_col = 'quantity'
                elif is_manomano:
                    print("   📋 Detected format: ManoMano")
                    sku_col = 'sku'
                    title_col = 'title'
                    category_col = 'mm_category'
                    price_col = 'product_price_vat_inc'
                    quantity_col = 'quantity'
                else:
                    print("   ❌ Unknown feed format")
                    sys.exit(1)

                # Read all rows
                f.seek(0)
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        products.append(FeedProduct(
                            sku=row.get(sku_col, ''),
                            ean=row.get('ean', ''),
                            title=row.get(title_col, '')[:60],  # Truncate for display
                            category=row.get(category_col, ''),
                            price=float(row.get(price_col, 0)),
                            quantity_in_feed=int(row.get(quantity_col, 0))
                        ))
                    except (ValueError, TypeError):
                        # Skip rows with invalid data
                        continue

            print(f"   ✅ Loaded {len(products)} products from feed")
            return products

        except FileNotFoundError:
            print(f"   ❌ File not found: {csv_file}")
            sys.exit(1)
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            sys.exit(1)

    def get_all_stock_data(self) -> Dict[str, Dict]:
        """Get ALL product stock data from BigBuy"""
        print("\n📦 Fetching current stock from BigBuy API...")
        print("   (This may take 1-2 minutes...)")

        all_stock_data = self._request("/rest/catalog/productsstockbyhandlingdays.json")

        if not all_stock_data:
            print("   ❌ Failed to fetch stock data")
            return {}

        # Build SKU -> stock map
        stock_map = {}
        for item in all_stock_data:
            sku = item.get('sku')
            if sku:
                stock_map[sku] = item

        print(f"   ✅ Loaded stock data for {len(stock_map):,} products")
        return stock_map

    def check_feed_stock(
        self,
        feed_products: List[FeedProduct],
        stock_map: Dict[str, Dict],
        max_handling_days: int = 2
    ) -> List[StockStatus]:
        """Check stock status for all feed products"""

        print(f"\n🔍 Checking stock status for {len(feed_products)} products...")
        print(f"   Max handling days: {max_handling_days}")

        results = []

        for i, product in enumerate(feed_products, 1):
            if i % 100 == 0:
                print(f"   Processed {i}/{len(feed_products)}...")

            if product.sku not in stock_map:
                results.append(StockStatus(
                    sku=product.sku,
                    title=product.title,
                    was_quantity=product.quantity_in_feed,
                    now_fast_stock=0,
                    now_total_stock=0,
                    status="not_found"
                ))
                continue

            stock_data = stock_map[product.sku]
            warehouses = stock_data.get('stocks', [])

            # Calculate total stock
            total_stock = sum(w.get('quantity', 0) for w in warehouses)

            # Calculate fast stock (0-2 day handling, or custom)
            fast_warehouses = [
                w for w in warehouses
                if w.get('maxHandlingDays', 999) <= max_handling_days
            ]
            fast_stock = sum(w.get('quantity', 0) for w in fast_warehouses)

            # Determine status
            if fast_stock > 0:
                status = "in_stock"
            elif total_stock > 0:
                status = "slow_stock_only"  # Has stock but not in fast warehouses
            else:
                status = "out_of_stock"

            results.append(StockStatus(
                sku=product.sku,
                title=product.title,
                was_quantity=product.quantity_in_feed,
                now_fast_stock=fast_stock,
                now_total_stock=total_stock,
                status=status
            ))

        print(f"   ✅ Completed stock check")
        return results

    def print_report(self, results: List[StockStatus], show_only_out_of_stock: bool = False):
        """Print detailed stock status report"""

        # Categorize results
        in_stock = [r for r in results if r.status == "in_stock"]
        out_of_stock = [r for r in results if r.status == "out_of_stock"]
        slow_stock = [r for r in results if r.status == "slow_stock_only"]
        not_found = [r for r in results if r.status == "not_found"]

        print(f"\n{'='*80}")
        print("FEED STOCK STATUS REPORT")
        print(f"{'='*80}\n")

        # Summary
        print("📊 SUMMARY:")
        print("-" * 80)
        print(f"   ✅ Still in stock (fast):     {len(in_stock):>5} products ({len(in_stock)/len(results)*100:.1f}%)")
        print(f"   ⚠️  Slow stock only:           {len(slow_stock):>5} products ({len(slow_stock)/len(results)*100:.1f}%)")
        print(f"   ❌ Out of stock:              {len(out_of_stock):>5} products ({len(out_of_stock)/len(results)*100:.1f}%)")
        print(f"   🔍 Not found in catalog:      {len(not_found):>5} products ({len(not_found)/len(results)*100:.1f}%)")
        print(f"   📦 Total products checked:    {len(results):>5}")
        print()

        # Out of stock products (ALWAYS SHOW)
        if out_of_stock:
            print("❌ OUT OF STOCK - REMOVE FROM MARKETPLACE:")
            print("-" * 80)
            for r in out_of_stock[:50]:  # Show first 50
                print(f"   {r.sku}")
                print(f"      Title: {r.title}")
                print(f"      Was: {r.was_quantity} units → Now: 0 units")
                print()

            if len(out_of_stock) > 50:
                print(f"   ... and {len(out_of_stock) - 50} more out-of-stock products")
                print()

        # Not found products
        if not_found and not show_only_out_of_stock:
            print("🔍 NOT FOUND IN CATALOG:")
            print("-" * 80)
            for r in not_found[:20]:  # Show first 20
                print(f"   {r.sku} - {r.title}")

            if len(not_found) > 20:
                print(f"   ... and {len(not_found) - 20} more not found")
            print()

        # Slow stock only
        if slow_stock and not show_only_out_of_stock:
            print("⚠️  SLOW STOCK ONLY (not in fast warehouses):")
            print("-" * 80)
            for r in slow_stock[:20]:
                print(f"   {r.sku}")
                print(f"      Title: {r.title}")
                print(f"      Total stock: {r.now_total_stock} units (slow warehouses)")
                print()

            if len(slow_stock) > 20:
                print(f"   ... and {len(slow_stock) - 20} more with slow stock only")
            print()

        # In stock (show sample if not filtered)
        if in_stock and not show_only_out_of_stock:
            print(f"✅ STILL IN STOCK (showing 10/{len(in_stock)}):")
            print("-" * 80)
            for r in in_stock[:10]:
                change = r.now_fast_stock - r.was_quantity
                change_str = f"+{change}" if change > 0 else str(change)
                print(f"   {r.sku} - {r.title[:50]}")
                print(f"      Was: {r.was_quantity} units → Now: {r.now_fast_stock} units ({change_str})")
                print()

        # Export out of stock SKUs to file
        if out_of_stock:
            out_file = "out_of_stock_skus.txt"
            with open(out_file, 'w') as f:
                for r in out_of_stock:
                    f.write(f"{r.sku}\n")
            print(f"💾 Saved out-of-stock SKUs to: {out_file}")
            print()

        print("="*80)
        print("RECOMMENDATIONS:")
        print("="*80)
        if out_of_stock:
            print(f"❌ Remove {len(out_of_stock)} out-of-stock products from Kaufland")
            print(f"   Use out_of_stock_skus.txt for bulk removal")
        if slow_stock:
            print(f"⚠️  {len(slow_stock)} products only in slow warehouses (consider removing)")
        if in_stock:
            print(f"✅ {len(in_stock)} products are healthy (still in stock)")

        print("="*80)


def main():
    """Main entry point"""

    # Check for API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ Error: BIGBUY_API_KEY environment variable not set")
        print("\nUsage:")
        print("  Windows PowerShell:")
        print('    $env:BIGBUY_API_KEY="your_key"')
        print("    python check_feed_stock_status.py kaufland_feed.csv")
        print("\n  Linux/Mac:")
        print("    BIGBUY_API_KEY=your_key python check_feed_stock_status.py kaufland_feed.csv")
        sys.exit(1)

    # Check for CSV file argument
    if len(sys.argv) < 2:
        print("❌ Error: No CSV file provided")
        print("\nUsage:")
        print("  python check_feed_stock_status.py <feed_csv> [options]")
        print("\nOptions:")
        print("  --all-stock           Check all warehouses (not just 0-2 day handling)")
        print("  --out-of-stock-only   Only show out-of-stock products")
        print("\nExamples:")
        print("  python check_feed_stock_status.py kaufland_feed.csv")
        print("  python check_feed_stock_status.py kaufland_feed.csv --out-of-stock-only")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    csv_file = args[0]

    max_handling_days = 2  # Default: fast stock only
    show_only_out_of_stock = False

    if '--all-stock' in args:
        max_handling_days = 999
        print("📦 Mode: Checking ALL warehouses (including slow stock)")
    else:
        print("⚡ Mode: Checking FAST warehouses only (0-2 day handling)")

    if '--out-of-stock-only' in args:
        show_only_out_of_stock = True
        print("🔍 Filter: Showing only out-of-stock products\n")

    # Initialize checker
    checker = FeedStockChecker(api_key)

    # Load feed products
    feed_products = checker.load_feed_products(csv_file)

    # Get current stock data
    stock_map = checker.get_all_stock_data()

    # Check stock status
    results = checker.check_feed_stock(feed_products, stock_map, max_handling_days)

    # Print report
    checker.print_report(results, show_only_out_of_stock)


if __name__ == "__main__":
    main()


## HOW TO RUN
# $env:BIGBUY_API_KEY="YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"
# python check_feed_stock_status.py kaufland_feed.csv
# python check_feed_stock_status.py kaufland_feed.csv --out-of-stock-only
