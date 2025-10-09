import requests
import csv
import json
import os
import random
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Config:
    """Configuration for feed generation"""
    margin: float = 0.35
    vat: float = 0.22
    base_price: float = 0.25
    max_price_eur: float = 400.0
    min_price_eur: float = 15.0
    max_volume_cm3: int = 180000
    max_weight_kg: float = 35.0
    sample_size: int = 25000
    categories_limit: int = 20
    products_per_category: int = 500


@dataclass
class CountryConfig:
    """Country-specific configuration"""
    locale: str
    language: str
    name: str
    currency: str
    rate: float

    @classmethod
    def get(cls, country_code: str) -> Optional['CountryConfig']:
        configs = {
            'AT': cls('de-AT', 'de', 'Austria', 'EUR', 1.0),
            'DE': cls('de-DE', 'de', 'Germany', 'EUR', 1.0),
            'IT': cls('it-IT', 'it', 'Italy', 'EUR', 1.0),
            'SK': cls('sk-SK', 'sk', 'Slovakia', 'EUR', 1.0),
            'PL': cls('pl-PL', 'pl', 'Poland', 'PLN', 4.5),
            'CZ': cls('cs-CZ', 'cs', 'Czech Republic', 'CZK', 24.0)
        }
        return configs.get(country_code.upper())


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
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error ({endpoint}): {e}")
            return None

    def get_categories(self, limit: int = 20) -> List[Dict]:
        """Get filtered and randomized categories"""
        result = self._request("/rest/catalog/taxonomies.json?firstLevel")
        if not result:
            return []
        
        # Filter adult content
        erotic_keywords = ['erotic', 'erotico', 'adult', 'sex', 'sexy', 'intimate', 'lingerie']
        filtered = [
            t for t in result 
            if not any(kw in t.get('name', '').lower() for kw in erotic_keywords)
        ]
        
        random.shuffle(filtered)
        return filtered[:limit]

    def get_category_data(self, taxonomy_id: int, language: str) -> Dict:
        """Get all data for a category in one call structure"""
        return {
            'products': self._request(f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}") or [],
            'variations': self._request(f"/rest/catalog/productsvariations.json?parentTaxonomy={taxonomy_id}") or [],
            'stock': self._request(f"/rest/catalog/productsstockbyhandlingdays.json?parentTaxonomy={taxonomy_id}") or [],
            'var_stock': self._request(f"/rest/catalog/productsvariationsstockbyhandlingdays.json?parentTaxonomy={taxonomy_id}") or [],
            'info': self._request(f"/rest/catalog/productsinformation.json?isoCode={language}&parentTaxonomy={taxonomy_id}") or [],
            'images': self._request(f"/rest/catalog/productsimages.json?parentTaxonomy={taxonomy_id}") or []
        }


class StockCalculator:
    """Calculate safe stock quantities"""
    
    @staticmethod
    def calculate_safe_quantity(bigbuy_stock: int) -> int:
        """Apply safety margins to prevent overselling - min 2 units in feed"""
        if bigbuy_stock <= 2:
            return 0  # Reject products with only 1-2 units
        elif bigbuy_stock <= 5:
            return 2  # List 2 if they have 3-5
        elif bigbuy_stock <= 10:
            return min(5, bigbuy_stock - 2)
        elif bigbuy_stock <= 20:
            return min(10, bigbuy_stock - 3)
        elif bigbuy_stock <= 50:
            return min(25, bigbuy_stock - 5)
        else:
            return min(50, int(bigbuy_stock * 0.9))


class ProductValidator:
    """Validate products against Kaufland requirements"""
    
    def __init__(self, config: Config, country_config: CountryConfig):
        self.config = config
        self.country = country_config
        self.stats = {
            'total': 0, 'invalid_ean': 0, 'not_new': 0,
            'no_stock': 0, 'no_info': 0, 'price_high': 0,
            'price_low': 0, 'weight_high': 0, 'volume_high': 0,
            'valid': 0
        }

    def validate(self, product: Dict, info: Dict, total_stock: int) -> Tuple[bool, str]:
        """Validate product against all rules"""
        self.stats['total'] += 1
        
        # EAN validation
        ean = str(product.get('ean13', '')).strip()
        if len(ean) != 13 or not ean.isdigit():
            self.stats['invalid_ean'] += 1
            return False, f"Invalid EAN: {ean}"
        
        # Condition check
        if product.get('condition', '').upper() != 'NEW':
            self.stats['not_new'] += 1
            return False, "Not NEW condition"
        
        # Stock check (require at least 3 to list 2)
        if total_stock <= 2:
            self.stats['no_stock'] += 1
            return False, "Insufficient stock"
        
        # Info check
        if not info or len(info.get('name', '').strip()) < 3:
            self.stats['no_info'] += 1
            return False, "Missing product info"
        
        # Weight check
        weight = float(product.get('weight', 0) or 0)
        if weight > self.config.max_weight_kg:
            self.stats['weight_high'] += 1
            return False, f"Weight too high: {weight}kg"
        
        # Volume check
        volume = (float(product.get('width', 0) or 0) * 
                 float(product.get('height', 0) or 0) * 
                 float(product.get('depth', 0) or 0))
        if volume > self.config.max_volume_cm3:
            self.stats['volume_high'] += 1
            return False, f"Volume too high: {volume}cm³"
        
        # Price check
        price = self._calculate_price(float(product.get('wholesalePrice', 0) or 0))
        max_price = self.config.max_price_eur * self.country.rate
        min_price = self.config.min_price_eur * self.country.rate
        
        if price > max_price:
            self.stats['price_high'] += 1
            return False, f"Price too high: {price}"
        
        if price < min_price:
            self.stats['price_low'] += 1
            return False, f"Price too low: {price}"
        
        self.stats['valid'] += 1
        return True, "Valid"

    def _calculate_price(self, wholesale_eur: float) -> float:
        """Calculate final price in local currency"""
        price_eur = (wholesale_eur * (1 + self.config.vat) * 
                    (1 + self.config.margin) + self.config.base_price)
        return price_eur * self.country.rate


class DataAggregator:
    """Aggregate and organize API data"""
    
    @staticmethod
    def build_stock_map(stock_data: List, var_stock_data: List) -> Tuple[Dict, Dict]:
        """Build stock lookup maps"""
        product_stock = {}
        variation_stock = {}
        
        for item in stock_data:
            sku = item.get('sku')
            if sku:
                total = sum(s.get('quantity', 0) for s in item.get('stocks', []))
                if total > 0:
                    product_stock[sku] = total
        
        for item in var_stock_data:
            sku = item.get('sku')
            if sku:
                total = sum(s.get('quantity', 0) for s in item.get('stocks', []))
                if total > 0:
                    variation_stock[sku] = total
        
        return product_stock, variation_stock

    @staticmethod
    def build_info_map(info_data: List) -> Dict:
        """Build product info lookup"""
        return {item['sku']: item for item in info_data}

    @staticmethod
    def build_image_map(image_data: List) -> Dict:
        """Build image lookup"""
        result = {}
        for img_set in image_data:
            images = img_set.get('images', [])
            if images:
                result[img_set['id']] = [img.get('url', '') for img in images[:4]]
        return result

    @staticmethod
    def build_variation_map(var_data: List) -> Dict:
        """Build variation lookup"""
        result = {}
        for var in var_data:
            pid = var.get('product')
            if pid:
                result.setdefault(pid, []).append(var)
        return result

    @staticmethod
    def calculate_total_stock(product: Dict, variations: Dict, 
                             prod_stock: Dict, var_stock: Dict) -> int:
        """Calculate total available stock"""
        sku = product.get('sku')
        pid = product.get('id')
        
        direct_stock = prod_stock.get(sku, 0)
        variation_stock = 0
        
        if pid in variations:
            for var in variations[pid]:
                var_sku = var.get('sku')
                variation_stock += var_stock.get(var_sku, 0)
        
        return direct_stock + variation_stock


class FeedGenerator:
    """Generate Kaufland-compliant feeds"""
    
    def __init__(self, config: Config, country_config: CountryConfig):
        self.config = config
        self.country = country_config

    def create_product_row(self, product: Dict, info: Dict, images: List) -> Dict:
        """Create product catalog row (for manual upload with translations)"""
        return {
            'ean': str(product.get('ean13', '')),
            'locale': self.country.locale,
            'title': (info.get('name', 'Product') or 'Product')[:100],
            'description': (info.get('description', '') or '')[:5000],
            'short_description': (info.get('description', '') or '')[:500],
            'category': 'Gardening & DIY',
            'manufacturer': 'Pop Pulse Emporium',
            'picture': images[0] if len(images) > 0 else '',
            'picture_2': images[1] if len(images) > 1 else '',
            'picture_3': images[2] if len(images) > 2 else '',
            'picture_4': images[3] if len(images) > 3 else '',
            'condition': 'new',
            'weight': str(round(float(product.get('weight', 0) or 0), 2)),
            'length': str(round(float(product.get('depth', 0) or 0), 2)),
            'width': str(round(float(product.get('width', 0) or 0), 2)),
            'height': str(round(float(product.get('height', 0) or 0), 2))
        }

    def create_offer_row(self, product: Dict, quantity: int) -> Dict:
        """Create offer row (for automatic upload - no translation needed)"""
        price = self._calculate_price(float(product.get('wholesalePrice', 0) or 0))
        
        return {
            'ean': str(product.get('ean13', '')),
            'id_offer': str(product.get('sku', '')),
            'condition': '100',  # Kaufland code: 100 = new
            'price': str(round(price, 2)),
            'currency': self.country.currency,
            'quantity': str(quantity),
            'handling_time': '2',
            'delivery_time_min': '3',
            'delivery_time_max': '8'
        }

    def _calculate_price(self, wholesale_eur: float) -> float:
        """Calculate final price"""
        price_eur = (wholesale_eur * (1 + self.config.vat) * 
                    (1 + self.config.margin) + self.config.base_price)
        return price_eur * self.country.rate

    def save_csv(self, data: List[Dict], filename: str, separator: str = ';') -> bool:
        """Save CSV file with Kaufland format (semicolon separator)"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=separator)
                writer.writeheader()
                writer.writerows(data)
            print(f"✅ Created {filename} ({len(data)} rows)")
            return True
        except Exception as e:
            print(f"❌ CSV Error: {e}")
            return False

    def save_json(self, product_count: int, offer_count: int, stats: Dict, 
                  filename: str, product_file: str, offer_file: str) -> bool:
        """Save metadata JSON"""
        try:
            info = {
                "last_updated": datetime.now().isoformat(),
                "product_count": product_count,
                "offer_count": offer_count,
                "validation_stats": stats,
                "stock_validation_enabled": True,
                "min_stock_in_feed": 2,
                "max_price_eur": self.config.max_price_eur,
                "min_price_eur": self.config.min_price_eur,
                "max_volume": self.config.max_volume_cm3,
                "max_weight": self.config.max_weight_kg,
                "currency": self.country.currency,
                "currency_rate": self.country.rate,
                "margin": f"{self.config.margin*100:.0f}%",
                "country": self.country.name,
                "locale": self.country.locale,
                "product_feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{product_file}",
                "offer_feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{offer_file}",
                "feed_type": "SEPARATED",
                "product_feed_info": "Upload manually with translations for product catalog",
                "offer_feed_info": "Auto-upload 3x daily for price/stock updates - NO translation needed"
            }
            
            with open(filename, 'w') as f:
                json.dump(info, f, indent=2)
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ JSON Error: {e}")
            return False

    def save_html(self, product_data: List[Dict], offer_data: List[Dict], 
                  stats: Dict, filename: str, product_file: str, offer_file: str) -> bool:
        """Save HTML dashboard"""
        try:
            prices = [float(row['price']) for row in offer_data]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            html = f"""<!DOCTYPE html>
<html lang="{self.country.language}">
<head>
    <meta charset="UTF-8">
    <title>Kaufland Feeds - {self.country.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #667eea; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .feed-type {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .feed-url {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; font-family: monospace; word-break: break-all; }}
        .important {{ background: #fff3cd; padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #ffc107; }}
        table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 10px; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #667eea; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ Kaufland Separated Feeds</h1>
        <p><strong>Pop Pulse Emporium - {self.country.name}</strong></p>
        <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="important">
        <h3>⚠️ Important: Two Separate Feeds</h3>
        <p><strong>This setup uses SEPARATED product and offer feeds:</strong></p>
        <ul>
            <li>📦 <strong>Product Feed:</strong> Upload manually (rare) - contains translations</li>
            <li>💰 <strong>Offer Feed:</strong> Auto-upload 3x daily - just prices/stock, NO translation needed</li>
        </ul>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(product_data):,}</div>
            <div class="stat-label">Products</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{len(offer_data):,}</div>
            <div class="stat-label">Offers</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{self.country.currency}{min_price:.2f}</div>
            <div class="stat-label">Min Price</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{self.country.currency}{max_price:.2f}</div>
            <div class="stat-label">Max Price</div>
        </div>
    </div>
    
    <div class="feed-type">
        <h3>📦 Product Feed (Manual Upload)</h3>
        <p><strong>File:</strong> {product_file}</p>
        <div class="feed-url">https://poppulseemporium.github.io/kaufland-feed/{product_file}</div>
        <p><strong>Contains:</strong> EAN, locale, title, description, images, category (with translations)</p>
        <p><strong>Upload:</strong> Manually via Kaufland Seller Portal when products change</p>
        <p><strong>Format:</strong> Semicolon-separated CSV, UTF-8</p>
    </div>
    
    <div class="feed-type">
        <h3>💰 Offer Feed (Automatic Upload)</h3>
        <p><strong>File:</strong> {offer_file}</p>
        <div class="feed-url">https://poppulseemporium.github.io/kaufland-feed/{offer_file}</div>
        <p><strong>Contains:</strong> EAN, SKU, price, stock, condition (NO translations needed!)</p>
        <p><strong>Upload:</strong> Automatically 3x daily (set in Kaufland)</p>
        <p><strong>Schedule:</strong> 02:00, 10:00, 18:00 (Italy time)</p>
        <p><strong>Format:</strong> Semicolon-separated CSV, UTF-8</p>
    </div>
    
    <h3>📊 Sample Products</h3>
    <table>
        <tr><th>EAN</th><th>SKU</th><th>Title</th><th>Price</th><th>Stock</th></tr>"""
            
            for i, (prod, offer) in enumerate(zip(product_data[:20], offer_data[:20])):
                title = prod['title'][:50] + '...' if len(prod['title']) > 50 else prod['title']
                html += f"""
        <tr>
            <td>{prod['ean']}</td>
            <td>{offer['id_offer']}</td>
            <td>{title}</td>
            <td>{offer['currency']}{offer['price']}</td>
            <td><strong>{offer['quantity']}</strong></td>
        </tr>"""
            
            html += """
    </table>
</body>
</html>"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ HTML Error: {e}")
            return False


def main():
    """Main execution"""
    print("🚀 KAUFLAND SEPARATED FEED GENERATOR")
    print("=" * 70)
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ BIGBUY_API_KEY environment variable not set")
        return
    
    # Get country configuration
    country_code = os.getenv('COUNTRY_CODE', 'IT').upper()
    country_config = CountryConfig.get(country_code)
    if not country_config:
        print(f"❌ Unsupported country: {country_code}")
        return
    
    print(f"🌍 Country: {country_config.name}")
    print(f"💱 Currency: {country_config.currency}")
    print(f"🗣️ Language: {country_config.language}")
    
    # Initialize components
    config = Config()
    api = BigBuyAPI(api_key)
    validator = ProductValidator(config, country_config)
    aggregator = DataAggregator()
    generator = FeedGenerator(config, country_config)
    stock_calc = StockCalculator()
    
    # Set random seed
    seed = datetime.now().hour + datetime.now().day * 24
    random.seed(seed)
    print(f"🎲 Random seed: {seed}")
    
    # Get categories
    categories = api.get_categories(config.categories_limit)
    if not categories:
        print("❌ No categories found")
        return
    
    print(f"📊 Processing {len(categories)} categories")
    
    # Collect all data
    all_products = []
    all_data = {'info': [], 'images': [], 'stock': [], 'var_stock': [], 'variations': []}
    
    print("\n🔄 Collecting data...")
    for i, category in enumerate(categories, 1):
        print(f"  {i}/{len(categories)}: {category['name']}")
        
        data = api.get_category_data(category['id'], country_config.language)
        
        # Limit products per category
        products = data['products'][:config.products_per_category]
        random.shuffle(products)
        all_products.extend(products)
        
        all_data['info'].extend(data['info'])
        all_data['images'].extend(data['images'])
        all_data['stock'].extend(data['stock'])
        all_data['var_stock'].extend(data['var_stock'])
        all_data['variations'].extend(data['variations'])
        
        time.sleep(0.5)
    
    print(f"✅ Collected {len(all_products)} products")
    
    # Build lookup maps
    prod_stock, var_stock = aggregator.build_stock_map(all_data['stock'], all_data['var_stock'])
    info_map = aggregator.build_info_map(all_data['info'])
    image_map = aggregator.build_image_map(all_data['images'])
    variation_map = aggregator.build_variation_map(all_data['variations'])
    
    print(f"📊 Stock entries: {len(prod_stock)} products, {len(var_stock)} variations")
    
    # Process products
    print("\n🔍 Validating products...")
    product_data = []
    offer_data = []
    seen_eans = set()
    random.shuffle(all_products)
    
    for product in all_products:
        if len(product_data) >= config.sample_size:
            break
        
        sku = product.get('sku')
        if not sku or sku not in info_map:
            continue
        
        # Calculate stock
        total_stock = aggregator.calculate_total_stock(
            product, variation_map, prod_stock, var_stock
        )
        
        # Validate
        is_valid, msg = validator.validate(product, info_map[sku], total_stock)
        if not is_valid:
            continue
        
        # Check for duplicates
        ean = str(product.get('ean13', ''))
        if ean in seen_eans:
            continue
        seen_eans.add(ean)
        
        # Calculate safe quantity
        safe_qty = stock_calc.calculate_safe_quantity(total_stock)
        if safe_qty <= 0:
            continue
        
        # Create rows
        images = image_map.get(product.get('id'), [])
        product_row = generator.create_product_row(product, info_map[sku], images)
        offer_row = generator.create_offer_row(product, safe_qty)
        
        product_data.append(product_row)
        offer_data.append(offer_row)
        
        if validator.stats['total'] % 1000 == 0:
            print(f"  Processed {validator.stats['total']:,}, found {validator.stats['valid']:,} valid")
    
    # Print stats
    print(f"\n📈 Validation Results:")
    for key, value in validator.stats.items():
        if value > 0:
            print(f"   {key}: {value:,}")
    
    if not product_data:
        print("❌ No valid products found")
        return
    
    print(f"\n✅ {len(product_data)} products ready")
    print(f"✅ {len(offer_data)} offers ready")
    
    # Generate filenames
    suffix = '' if country_code == 'IT' else f'_{country_code.lower()}'
    product_file = f'kaufland_products{suffix}.csv'
    offer_file = f'kaufland_offers{suffix}.csv'
    html_file = f'index{suffix}.html'
    json_file = f'feed_info{suffix}.json'
    
    # Save files
    print("\n📁 Creating files...")
    generator.save_csv(product_data, product_file, separator=';')
    generator.save_csv(offer_data, offer_file, separator=';')
    generator.save_json(len(product_data), len(offer_data), validator.stats, 
                       json_file, product_file, offer_file)
    generator.save_html(product_data, offer_data, validator.stats, 
                       html_file, product_file, offer_file)
    
    # Summary
    print("\n" + "=" * 70)
    print("🎉 SEPARATED FEEDS GENERATION COMPLETE")
    print("=" * 70)
    print(f"📦 Product Feed: {product_file} ({len(product_data)} products)")
    print(f"💰 Offer Feed: {offer_file} ({len(offer_data)} offers)")
    print(f"\n📋 Upload Instructions:")
    print(f"   1. Product Feed (manual, rare): Upload {product_file} to Kaufland")
    print(f"      - Contains translations in {country_config.language}")
    print(f"      - Upload when products change or weekly")
    print(f"   2. Offer Feed (automatic, 3x daily): Set auto-upload for {offer_file}")
    print(f"      - Times: 02:00, 10:00, 18:00 (Italy time)")
    print(f"      - NO translation needed - just price/stock!")
    print(f"\n🌐 Feed URLs:")
    print(f"   📦 https://poppulseemporium.github.io/kaufland-feed/{product_file}")
    print(f"   💰 https://poppulseemporium.github.io/kaufland-feed/{offer_file}")
    print(f"   🌐 https://poppulseemporium.github.io/kaufland-feed/{html_file}")
    print(f"\n✅ Format: Semicolon-separated (;) CSV, UTF-8 encoding")
    print(f"✅ All products have stock ≥2 units for safety")


if __name__ == "__main__":
    main()
