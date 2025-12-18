"""
Find Vinted Profit Opportunities - Price Comparison Tool

Compares clothing product prices from your feed against online market prices
to identify products you can buy cheap and resell on Vinted for profit.

Usage:
    python find_vinted_opportunities.py kaufland_feed.csv --limit 10
    python find_vinted_opportunities.py kaufland_feed.csv --category "Moda e accessori"
"""

import os
import sys
import csv
import time
import requests
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class ProductOpportunity:
    """Product with profit opportunity data"""
    sku: str
    title: str
    your_price: float
    market_min: Optional[float]
    market_max: Optional[float]
    market_avg: Optional[float]
    potential_profit: Optional[float]
    profit_margin: Optional[float]
    competitor_count: int
    search_url: str


class GoogleShoppingSearcher:
    """Search Google Shopping for product prices"""

    def __init__(self, country: str = "it"):
        self.country = country
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def search_product(self, product_title: str, delay: float = 2.0) -> Dict:
        """
        Search Google Shopping for a product and extract prices

        Args:
            product_title: Product name to search
            delay: Delay in seconds before making request (rate limiting)

        Returns:
            Dictionary with prices found
        """
        # Add delay to avoid rate limiting
        time.sleep(delay)

        # Clean up title for search
        clean_title = self._clean_title_for_search(product_title)

        # Build Google Shopping search URL (Italy)
        search_url = f"https://www.google.com/search?q={clean_title}&tbm=shop&hl=it&gl=it"

        try:
            print(f"      Searching: {clean_title[:50]}...", end=" ")
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract prices from Google Shopping results
            prices = self._extract_prices(soup)

            if prices:
                print(f"Found {len(prices)} prices")
                return {
                    'prices': prices,
                    'min': min(prices),
                    'max': max(prices),
                    'avg': sum(prices) / len(prices),
                    'count': len(prices),
                    'url': search_url
                }
            else:
                print("No prices found")
                return {'prices': [], 'count': 0, 'url': search_url}

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return {'prices': [], 'count': 0, 'url': search_url}

    def _clean_title_for_search(self, title: str) -> str:
        """Clean product title for better search results"""
        # Remove special characters
        title = re.sub(r'[^\w\s\-]', ' ', title)
        # Remove extra whitespace
        title = ' '.join(title.split())
        # URL encode
        title = requests.utils.quote(title)
        return title

    def _extract_prices(self, soup: BeautifulSoup) -> List[float]:
        """Extract prices from Google Shopping HTML"""
        prices = []

        # Try multiple selectors (Google changes these frequently)
        price_selectors = [
            'span.a8Pemb',  # Common Google Shopping price span
            'div.sh-pr__product-price',
            'span[data-price]',
            'div.product-price',
            'span.price',
        ]

        for selector in price_selectors:
            elements = soup.select(selector)
            for elem in elements:
                price_text = elem.get_text()
                price = self._parse_price(price_text)
                if price and price > 0:
                    prices.append(price)

        # Also try data attributes
        for elem in soup.find_all(attrs={'data-price': True}):
            try:
                price = float(elem['data-price'])
                if price > 0:
                    prices.append(price)
            except (ValueError, KeyError):
                continue

        # Remove duplicates and outliers
        if prices:
            prices = list(set(prices))
            # Remove extreme outliers (prices 10x different from median)
            if len(prices) > 2:
                median = sorted(prices)[len(prices) // 2]
                prices = [p for p in prices if 0.1 * median <= p <= 10 * median]

        return sorted(prices)

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text like '€29,99' or '29.99 EUR'"""
        # Remove currency symbols and whitespace
        price_text = price_text.strip()
        price_text = price_text.replace('€', '').replace('EUR', '').replace('$', '')
        price_text = price_text.strip()

        # Handle European format (comma as decimal separator)
        price_text = price_text.replace('.', '').replace(',', '.')

        # Extract first number
        match = re.search(r'(\d+\.?\d*)', price_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None


class VintedOpportunityFinder:
    """Find profit opportunities for Vinted reselling"""

    VINTED_FEE_RATE = 0.12  # 12% Vinted commission
    VINTED_PAYMENT_FEE = 0.50  # €0.50 payment processing
    SHIPPING_COST = 5.00  # Average shipping cost

    def __init__(self):
        self.searcher = GoogleShoppingSearcher()

    def load_clothing_products(self, csv_file: str, limit: int = None, category_filter: str = None) -> List[Dict]:
        """Load clothing products from feed CSV"""
        print(f"\n📂 Loading clothing products from {csv_file}...")

        products = []

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                # Detect format
                first_row = next(reader)
                is_kaufland = 'id_offer' in first_row
                is_manomano = 'sku' in first_row and 'product_price_vat_inc' in first_row

                if is_kaufland:
                    sku_col, title_col, category_col, price_col = 'id_offer', 'title', 'category', 'price_cs'
                elif is_manomano:
                    sku_col, title_col, category_col, price_col = 'sku', 'title', 'mm_category', 'product_price_vat_inc'
                else:
                    print("   ❌ Unknown feed format")
                    return []

                # Read all rows
                f.seek(0)
                reader = csv.DictReader(f)

                for row in reader:
                    category = row.get(category_col, '')

                    # Filter for clothing/fashion categories
                    if not self._is_clothing_category(category):
                        continue

                    # Apply category filter if specified
                    if category_filter and category_filter.lower() not in category.lower():
                        continue

                    try:
                        products.append({
                            'sku': row.get(sku_col, ''),
                            'title': row.get(title_col, ''),
                            'category': category,
                            'price': float(row.get(price_col, 0))
                        })

                        if limit and len(products) >= limit:
                            break

                    except (ValueError, TypeError):
                        continue

            print(f"   ✅ Loaded {len(products)} clothing products")
            return products

        except FileNotFoundError:
            print(f"   ❌ File not found: {csv_file}")
            return []

    def _is_clothing_category(self, category: str) -> bool:
        """Check if category is clothing/fashion related"""
        clothing_keywords = [
            'moda', 'accessori', 'abbigliamento', 'vestiti', 'fashion',
            'clothing', 'apparel', 'clothes', 'wear', 'textile'
        ]
        category_lower = category.lower()
        return any(keyword in category_lower for keyword in clothing_keywords)

    def analyze_products(self, products: List[Dict], delay: float = 3.0) -> List[ProductOpportunity]:
        """Analyze products for profit opportunities"""
        print(f"\n🔍 Analyzing {len(products)} products for profit opportunities...")
        print(f"   (Delay: {delay}s between searches to avoid rate limiting)\n")

        opportunities = []

        for i, product in enumerate(products, 1):
            print(f"   [{i}/{len(products)}] {product['sku']}")
            print(f"      Title: {product['title'][:60]}")
            print(f"      Your price: €{product['price']:.2f}")

            # Search for market prices
            market_data = self.searcher.search_product(product['title'], delay=delay)

            if market_data['count'] > 0:
                # Calculate potential profit
                market_avg = market_data['avg']
                vinted_revenue = market_avg - (market_avg * self.VINTED_FEE_RATE) - self.VINTED_PAYMENT_FEE
                profit = vinted_revenue - product['price'] - self.SHIPPING_COST
                profit_margin = (profit / product['price'] * 100) if product['price'] > 0 else 0

                print(f"      Market avg: €{market_avg:.2f} (range: €{market_data['min']:.2f} - €{market_data['max']:.2f})")
                print(f"      Potential profit: €{profit:.2f} ({profit_margin:.1f}% margin)")

                opportunities.append(ProductOpportunity(
                    sku=product['sku'],
                    title=product['title'],
                    your_price=product['price'],
                    market_min=market_data['min'],
                    market_max=market_data['max'],
                    market_avg=market_avg,
                    potential_profit=profit,
                    profit_margin=profit_margin,
                    competitor_count=market_data['count'],
                    search_url=market_data['url']
                ))
            else:
                print(f"      ⚠️  No market data found")
                opportunities.append(ProductOpportunity(
                    sku=product['sku'],
                    title=product['title'],
                    your_price=product['price'],
                    market_min=None,
                    market_max=None,
                    market_avg=None,
                    potential_profit=None,
                    profit_margin=None,
                    competitor_count=0,
                    search_url=market_data['url']
                ))

            print()

        return opportunities

    def print_report(self, opportunities: List[ProductOpportunity]):
        """Print profit opportunity report"""
        print(f"\n{'='*90}")
        print("VINTED PROFIT OPPORTUNITY REPORT")
        print(f"{'='*90}\n")

        # Filter profitable opportunities
        profitable = [o for o in opportunities if o.potential_profit and o.potential_profit > 5.0]
        marginal = [o for o in opportunities if o.potential_profit and 0 < o.potential_profit <= 5.0]
        unprofitable = [o for o in opportunities if o.potential_profit and o.potential_profit <= 0]
        no_data = [o for o in opportunities if o.potential_profit is None]

        print("📊 SUMMARY:")
        print("-" * 90)
        print(f"   💰 Highly profitable (>€5 profit):     {len(profitable)} products")
        print(f"   💵 Marginally profitable (€0-€5):      {len(marginal)} products")
        print(f"   ❌ Not profitable:                      {len(unprofitable)} products")
        print(f"   ⚠️  No market data:                     {len(no_data)} products")
        print(f"   📦 Total analyzed:                      {len(opportunities)} products\n")

        # Show top opportunities
        if profitable:
            profitable.sort(key=lambda x: x.potential_profit, reverse=True)
            print("💰 TOP PROFIT OPPORTUNITIES:")
            print("-" * 90)
            for i, opp in enumerate(profitable[:10], 1):
                print(f"{i}. {opp.title[:60]}")
                print(f"   SKU: {opp.sku}")
                print(f"   Your cost: €{opp.your_price:.2f}")
                print(f"   Market price: €{opp.market_avg:.2f} (€{opp.market_min:.2f} - €{opp.market_max:.2f})")
                print(f"   Potential profit: €{opp.potential_profit:.2f} ({opp.profit_margin:.1f}% margin)")
                print(f"   Competitors: {opp.competitor_count}")
                print(f"   Search: {opp.search_url}")
                print()

        # Save results to CSV
        output_file = 'vinted_opportunities.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'SKU', 'Title', 'Your Price', 'Market Min', 'Market Avg', 'Market Max',
                'Potential Profit', 'Profit Margin %', 'Competitors', 'Search URL'
            ])
            for opp in sorted(opportunities, key=lambda x: x.potential_profit or -999, reverse=True):
                writer.writerow([
                    opp.sku,
                    opp.title,
                    f"{opp.your_price:.2f}" if opp.your_price else '',
                    f"{opp.market_min:.2f}" if opp.market_min else '',
                    f"{opp.market_avg:.2f}" if opp.market_avg else '',
                    f"{opp.market_max:.2f}" if opp.market_max else '',
                    f"{opp.potential_profit:.2f}" if opp.potential_profit else '',
                    f"{opp.profit_margin:.1f}" if opp.profit_margin else '',
                    opp.competitor_count,
                    opp.search_url
                ])

        print(f"💾 Saved results to: {output_file}\n")
        print("="*90)


def main():
    """Main entry point"""

    if len(sys.argv) < 2:
        print("❌ Error: No CSV file provided")
        print("\nUsage:")
        print("  python find_vinted_opportunities.py <feed_csv> [options]")
        print("\nOptions:")
        print("  --limit N              Analyze only first N clothing products")
        print("  --category CATEGORY    Filter by category name")
        print("  --delay SECONDS        Delay between searches (default: 3s)")
        print("\nExamples:")
        print("  python find_vinted_opportunities.py kaufland_feed.csv --limit 10")
        print("  python find_vinted_opportunities.py kaufland_feed.csv --category 'Moda'")
        sys.exit(1)

    # Parse arguments
    csv_file = sys.argv[1]
    limit = None
    category_filter = None
    delay = 3.0

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--limit' and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == '--category' and i + 1 < len(args):
            category_filter = args[i + 1]
            i += 2
        elif args[i] == '--delay' and i + 1 < len(args):
            delay = float(args[i + 1])
            i += 2
        else:
            i += 1

    # Initialize finder
    finder = VintedOpportunityFinder()

    # Load clothing products
    products = finder.load_clothing_products(csv_file, limit=limit, category_filter=category_filter)

    if not products:
        print("❌ No clothing products found")
        sys.exit(1)

    # Analyze for profit opportunities
    opportunities = finder.analyze_products(products, delay=delay)

    # Print report
    finder.print_report(opportunities)


if __name__ == "__main__":
    main()


## HOW TO RUN
# python find_vinted_opportunities.py kaufland_feed.csv --limit 10
# python find_vinted_opportunities.py kaufland_feed.csv --limit 10 --delay 2
