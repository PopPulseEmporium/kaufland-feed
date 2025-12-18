"""
Check Product Availability via BigBuy API

This script checks if a product is available (in stock) via BigBuy API,
even if it doesn't appear on the BigBuy website.

Usage:
    python check_product_availability.py SKU123456
    python check_product_availability.py S0469229 F01139370

Examples:
    # Check single product
    BIGBUY_API_KEY=your_key python check_product_availability.py F01139370

    # Check multiple products
    BIGBUY_API_KEY=your_key python check_product_availability.py F01139370 S0469229 F01140001
"""

import os
import sys
import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class ProductAvailability:
    """Product availability information"""
    sku: str
    exists: bool
    in_stock: bool
    total_stock: int
    fast_stock: int  # 0-2 day handling
    warehouses: List[Dict]
    product_info: Optional[Dict] = None
    error: Optional[str] = None


class BigBuyAvailabilityChecker:
    """Check product availability via BigBuy API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _request(self, endpoint: str) -> Optional[dict]:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API Error ({endpoint}): {e}")
            return None

    def get_all_stock_data(self) -> Dict[str, Dict]:
        """
        Get ALL product stock data from BigBuy
        Uses the same method as feed generators (fetch by categories)
        """
        print("\n📦 Fetching ALL product stock from BigBuy...")
        print("   (This may take 1-2 minutes...)")

        # Get all products stock by handling days
        # This endpoint returns ALL products, not filtered by category
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

    def check_product(self, sku: str, stock_map: Dict[str, Dict], max_handling_days: int = 2) -> ProductAvailability:
        """
        Check if product is available using pre-loaded stock data

        Args:
            sku: Product SKU (e.g., 'F01139370', 'S0469229')
            stock_map: Pre-loaded stock data (SKU -> stock info)
            max_handling_days: Consider stock with ≤ N day handling (default: 2)

        Returns:
            ProductAvailability with stock details
        """

        if sku not in stock_map:
            return ProductAvailability(
                sku=sku,
                exists=False,
                in_stock=False,
                total_stock=0,
                fast_stock=0,
                warehouses=[],
                error="Product not found in stock data"
            )

        stock_data = stock_map[sku]

        # Parse stock data
        warehouses = stock_data.get('stocks', [])
        total_stock = sum(w.get('quantity', 0) for w in warehouses)

        # Fast stock (0-2 day handling)
        fast_warehouses = [
            w for w in warehouses
            if w.get('maxHandlingDays', 999) <= max_handling_days
        ]
        fast_stock = sum(w.get('quantity', 0) for w in fast_warehouses)

        in_stock = total_stock > 0

        # Get product name if available
        product_name = stock_data.get('name', 'N/A')

        return ProductAvailability(
            sku=sku,
            exists=True,
            in_stock=in_stock,
            total_stock=total_stock,
            fast_stock=fast_stock,
            warehouses=fast_warehouses,
            product_info={'name': product_name}
        )

    def check_multiple_products(self, skus: List[str], max_handling_days: int = 2) -> Dict[str, ProductAvailability]:
        """Check availability for multiple products"""

        # Load all stock data first (one API call)
        stock_map = self.get_all_stock_data()

        results = {}

        print(f"\n{'='*70}")
        print(f"CHECKING {len(skus)} PRODUCTS")
        print(f"{'='*70}\n")

        for i, sku in enumerate(skus, 1):
            print(f"[{i}/{len(skus)}] {sku}...", end=" ")
            result = self.check_product(sku, stock_map, max_handling_days)
            results[sku] = result

            if result.fast_stock > 0:
                print(f"✅ {result.fast_stock} units")
            elif result.exists:
                print(f"❌ No fast stock ({result.total_stock} total)")
            else:
                print(f"⚠️  Not found")

        return results

    def print_summary(self, results: Dict[str, ProductAvailability]):
        """Print summary of availability check"""
        print(f"\n{'='*70}")
        print("AVAILABILITY SUMMARY")
        print(f"{'='*70}\n")

        available = []
        unavailable = []
        not_found = []

        for sku, result in results.items():
            if not result.exists:
                not_found.append(sku)
            elif result.fast_stock > 0:
                available.append((sku, result))
            else:
                unavailable.append((sku, result))

        # Print available products
        if available:
            print(f"✅ AVAILABLE ({len(available)} products):")
            print("-" * 70)
            for sku, result in available:
                print(f"   {sku}")
                print(f"      Name: {result.product_info.get('name', 'N/A')[:60]}")
                print(f"      Fast Stock: {result.fast_stock} units (≤2 day handling)")
                print(f"      Total Stock: {result.total_stock} units (all warehouses)")
                print(f"      Warehouses: {len(result.warehouses)} fast")
                print()

        # Print unavailable products
        if unavailable:
            print(f"❌ NOT IN STOCK ({len(unavailable)} products):")
            print("-" * 70)
            for sku, result in unavailable:
                print(f"   {sku}")
                print(f"      Name: {result.product_info.get('name', 'N/A')[:60]}")
                print(f"      Reason: {result.error or 'No stock in fast warehouses'}")
                print()

        # Print not found products
        if not_found:
            print(f"⚠️  NOT FOUND ({len(not_found)} products):")
            print("-" * 70)
            for sku in not_found:
                print(f"   {sku} - Not in BigBuy catalog")
            print()

        # Summary stats
        print("="*70)
        print(f"TOTALS:")
        print(f"   Available: {len(available)}")
        print(f"   Not in stock: {len(unavailable)}")
        print(f"   Not found: {len(not_found)}")
        print(f"   Total checked: {len(results)}")
        print("="*70)


def main():
    """Main entry point"""

    # Check for API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ Error: BIGBUY_API_KEY environment variable not set")
        print("\nUsage:")
        print("  Windows PowerShell:")
        print('    $env:BIGBUY_API_KEY="your_key"')
        print("    python check_product_availability.py SKU1 SKU2 ...")
        print("\n  Linux/Mac:")
        print("    BIGBUY_API_KEY=your_key python check_product_availability.py SKU1 SKU2 ...")
        sys.exit(1)

    # Check for SKUs in command line
    if len(sys.argv) < 2:
        print("❌ Error: No product SKUs provided")
        print("\nUsage:")
        print("  python check_product_availability.py [--all-stock] SKU1 [SKU2 SKU3 ...]")
        print("\nOptions:")
        print("  --all-stock    Check all warehouses (not just fast 0-2 day handling)")
        print("\nExamples:")
        print("  python check_product_availability.py F01139370")
        print("  python check_product_availability.py --all-stock S0469229 F01139370")
        sys.exit(1)

    # Parse arguments
    args = sys.argv[1:]
    max_handling_days = 2  # Default: fast stock only

    if '--all-stock' in args:
        max_handling_days = 999  # All warehouses
        args.remove('--all-stock')
        print("📦 Mode: Checking ALL warehouses (including slow stock)")
    else:
        print("⚡ Mode: Checking FAST warehouses only (0-2 day handling)")
        print("   Tip: Use --all-stock to see all warehouses\n")

    skus = args

    # Initialize checker
    checker = BigBuyAvailabilityChecker(api_key)

    # Check products
    results = checker.check_multiple_products(skus, max_handling_days)

    # Print summary
    checker.print_summary(results)

    # Return appropriate exit code
    all_available = all(r.fast_stock > 0 for r in results.values())
    sys.exit(0 if all_available else 1)


if __name__ == "__main__":
    main()

## HOT TO RUN
# $env:BIGBUY_API_KEY="YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"; 
# python check_product_availability.py S3059176 --> only fast stock
# python check_product_availability.py --all-stock S3059176 --> all warehouses