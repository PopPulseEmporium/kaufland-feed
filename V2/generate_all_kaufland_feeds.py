"""
Generate Kaufland Feeds for All Countries

This script generates separate product feeds for all 7 Kaufland marketplaces:
- Italy (IT)
- Germany (DE)
- France (FR)
- Austria (AT)
- Slovakia (SK)
- Poland (PL)
- Czech Republic (CZ)

Each country gets its own CSV file that can be uploaded independently with
"Replace current offer" to properly remove old products.

Usage:
    python generate_all_kaufland_feeds.py

Environment:
    BIGBUY_API_KEY must be set

Output:
    - kaufland_feed_<country>.csv for each country
    - feed_info_<country>.json for each country
    - index_<country>.html for each country
    - summary_all_countries.json with overall statistics
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List

# Country configurations
COUNTRIES = {
    'IT': {'name': 'Italy', 'flag': '🇮🇹', 'currency': 'EUR'},
    'DE': {'name': 'Germany', 'flag': '🇩🇪', 'currency': 'EUR'},
    'FR': {'name': 'France', 'flag': '🇫🇷', 'currency': 'EUR'},
    'AT': {'name': 'Austria', 'flag': '🇦🇹', 'currency': 'EUR'},
    'SK': {'name': 'Slovakia', 'flag': '🇸🇰', 'currency': 'EUR'},
    'PL': {'name': 'Poland', 'flag': '🇵🇱', 'currency': 'PLN'},
    'CZ': {'name': 'Czech Republic', 'flag': '🇨🇿', 'currency': 'CZK'}
}


class MultiCountryFeedGenerator:
    """Generate feeds for multiple countries"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.results = {}
        self.start_time = None
        self.end_time = None

    def generate_feed_for_country(self, country_code: str) -> Dict:
        """Generate feed for a single country"""

        country_info = COUNTRIES[country_code]
        print(f"\n{'='*70}")
        print(f"{country_info['flag']} Generating {country_info['name']} ({country_code}) feed...")
        print(f"{'='*70}")

        # Set environment variables
        env = os.environ.copy()
        env['BIGBUY_API_KEY'] = self.api_key
        env['COUNTRY_CODE'] = country_code

        # Run bigbuy_kaufland.py
        start = time.time()

        try:
            result = subprocess.run(
                [sys.executable, 'bigbuy_kaufland.py'],
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',  # Force UTF-8 encoding for Windows
                errors='replace',   # Replace problematic characters instead of crashing
                timeout=600  # 10 minute timeout
            )

            duration = time.time() - start

            # Check for success
            if result.returncode != 0:
                print(f"❌ Error generating {country_code} feed:")
                print(result.stderr)
                return {
                    'success': False,
                    'error': result.stderr,
                    'duration': duration
                }

            # Print output
            print(result.stdout)

            # Read feed info to get statistics (consistent naming for all countries)
            info_file = f'feed_info_{country_code.lower()}.json'
            csv_file = f'kaufland_feed_{country_code.lower()}.csv'

            stats = {}
            if os.path.exists(info_file):
                with open(info_file, 'r') as f:
                    feed_info = json.load(f)
                    stats = {
                        'product_count': feed_info.get('product_count', 0),
                        'validation_stats': feed_info.get('validation_stats', {}),
                        'currency': country_info['currency']
                    }

            # Check if CSV exists
            csv_exists = os.path.exists(csv_file)

            print(f"\n✅ {country_info['name']} feed generated successfully!")
            print(f"   Duration: {duration:.1f} seconds")
            if stats.get('product_count'):
                print(f"   Products: {stats['product_count']:,}")

            return {
                'success': True,
                'country_code': country_code,
                'country_name': country_info['name'],
                'csv_file': csv_file if csv_exists else None,
                'info_file': info_file if os.path.exists(info_file) else None,
                'duration': duration,
                'stats': stats
            }

        except subprocess.TimeoutExpired:
            print(f"❌ Timeout generating {country_code} feed (>10 minutes)")
            return {
                'success': False,
                'error': 'Timeout after 10 minutes',
                'duration': 600
            }
        except Exception as e:
            print(f"❌ Exception generating {country_code} feed: {e}")
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - start
            }

    def generate_all_feeds(self) -> Dict:
        """Generate feeds for all countries"""

        print("🚀 KAUFLAND MULTI-COUNTRY FEED GENERATOR")
        print("="*70)
        print(f"Generating feeds for {len(COUNTRIES)} countries")
        print(f"Countries: {', '.join(COUNTRIES.keys())}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)

        self.start_time = time.time()

        # Generate feeds for each country
        for i, country_code in enumerate(COUNTRIES.keys(), 1):
            country_info = COUNTRIES[country_code]
            print(f"\n[{i}/{len(COUNTRIES)}] {country_info['flag']} {country_info['name']}")

            result = self.generate_feed_for_country(country_code)
            self.results[country_code] = result

            # Small delay between countries to avoid API rate limits
            if i < len(COUNTRIES):
                time.sleep(2)

        self.end_time = time.time()

        # Generate summary
        return self.create_summary()

    def create_summary(self) -> Dict:
        """Create summary report"""

        total_duration = self.end_time - self.start_time
        successful = [r for r in self.results.values() if r.get('success')]
        failed = [r for r in self.results.values() if not r.get('success')]

        total_products = sum(
            r.get('stats', {}).get('product_count', 0)
            for r in successful
        )

        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_duration_seconds': round(total_duration, 1),
            'total_duration_minutes': round(total_duration / 60, 1),
            'countries_total': len(COUNTRIES),
            'countries_successful': len(successful),
            'countries_failed': len(failed),
            'total_products': total_products,
            'average_products_per_country': round(total_products / len(successful)) if successful else 0,
            'results': self.results
        }

        # Save summary
        with open('summary_all_countries.json', 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    def print_final_report(self, summary: Dict):
        """Print final summary report"""

        print("\n" + "="*70)
        print("📊 GENERATION COMPLETE - SUMMARY")
        print("="*70)

        print(f"\n⏱️  Total time: {summary['total_duration_minutes']:.1f} minutes")
        print(f"✅ Successful: {summary['countries_successful']}/{summary['countries_total']} countries")

        if summary['countries_failed'] > 0:
            print(f"❌ Failed: {summary['countries_failed']} countries")

        print(f"\n📦 Total products: {summary['total_products']:,} (across all countries)")
        print(f"📊 Average per country: {summary['average_products_per_country']:,}")

        # List successful feeds
        print(f"\n✅ SUCCESSFUL FEEDS:")
        print("-" * 70)
        for country_code, result in self.results.items():
            if result.get('success'):
                country_info = COUNTRIES[country_code]
                product_count = result.get('stats', {}).get('product_count', 0)
                csv_file = result.get('csv_file', 'N/A')
                print(f"   {country_info['flag']} {country_info['name']:15} → {csv_file:30} ({product_count:,} products)")

        # List failed feeds if any
        if summary['countries_failed'] > 0:
            print(f"\n❌ FAILED FEEDS:")
            print("-" * 70)
            for country_code, result in self.results.items():
                if not result.get('success'):
                    country_info = COUNTRIES[country_code]
                    error = result.get('error', 'Unknown error')
                    print(f"   {country_info['flag']} {country_info['name']:15} → {error}")

        # Next steps
        print("\n" + "="*70)
        print("📋 NEXT STEPS")
        print("="*70)
        print("\nUpload each CSV file to its respective Kaufland marketplace:")
        print("Method: 'Replace current offer' (this will remove old products)")
        print()

        for country_code, result in self.results.items():
            if result.get('success') and result.get('csv_file'):
                country_info = COUNTRIES[country_code]
                csv_file = result['csv_file']
                print(f"   {country_info['flag']} {country_info['name']:15} → Upload {csv_file}")

        print("\n" + "="*70)
        print("💾 Summary saved to: summary_all_countries.json")
        print("="*70)


def main():
    """Main execution"""

    # Check for API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ Error: BIGBUY_API_KEY environment variable not set")
        print("\nUsage:")
        print("  Windows PowerShell:")
        print('    $env:BIGBUY_API_KEY="your_key_here"')
        print("    python generate_all_kaufland_feeds.py")
        print("\n  Linux/Mac:")
        print("    BIGBUY_API_KEY=your_key_here python generate_all_kaufland_feeds.py")
        sys.exit(1)

    # Check if bigbuy_kaufland.py exists
    if not os.path.exists('bigbuy_kaufland.py'):
        print("❌ Error: bigbuy_kaufland.py not found in current directory")
        print("   Make sure you're running this from the feeds directory")
        sys.exit(1)

    # Generate feeds
    generator = MultiCountryFeedGenerator(api_key)
    summary = generator.generate_all_feeds()
    generator.print_final_report(summary)

    # Exit with appropriate code
    if summary['countries_failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()


## HOW TO RUN:
# $env:BIGBUY_API_KEY="YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"
# python generate_all_kaufland_feeds.py
