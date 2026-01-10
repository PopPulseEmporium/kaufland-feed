# Windows UTF-8 encoding fix
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import csv
import json
import os
import random
import time
import yaml
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path


# Kaufland Category Mapping (BigBuy → Kaufland categories)
# Based on category_tree_int_all_languages.xlsx - Italian Level 1 categories
# ALL 21 BigBuy categories (excluding adult content 17088 and services 31548)
KAUFLAND_CATEGORIES = {
    # DIY, Tools, Garden, Industrial
    19651: "Giardinaggio e fai da te",      # Bricolaje y herramientas (DIY & Tools)
    19661: "Giardinaggio e fai da te",      # Jardín (Garden)
    19658: "Giardinaggio e fai da te",      # Industria, empresas y ciencia (Industrial)

    # Home & Furniture
    19656: "Casa e arredamento",             # Hogar y cocina (Home & Kitchen)
    19657: "Casa e arredamento",             # Iluminación (Lighting)
    19664: "Casa e arredamento",             # Oficina y papelería (Office)
    19654: "Casa e arredamento",             # Equipaje (Luggage)

    # Automotive
    19652: "Auto e moto",                    # Coche y moto (Automotive)

    # Electronics & IT
    19653: "Elettronica e computer",         # Electrónica (Electronics)
    19685: "Elettronica e computer",         # Informática (IT/Computing)

    # Sports & Outdoor
    19756: "Sport e attività all'aperto",   # Deportes y aire libre (Sports & Outdoor)

    # Kitchen/Home articles, Pets
    19666: "Articoli da cucina e per la casa", # Productos para mascotas (Pet Products)

    # Food
    19648: "Generi alimentari",              # Alimentación y bebidas (Food & Drinks)

    # Fashion & Accessories
    19668: "Moda e accessori",               # Ropa (Clothing)
    19671: "Moda e accessori",               # Zapatos y complementos (Shoes & Accessories)
    19662: "Moda e accessori",               # Joyería (Jewelry)
    19667: "Moda e accessori",               # Relojes (Watches)

    # Beauty & Health
    19650: "Cura del corpo e salute",        # Belleza (Beauty)
    19669: "Cura del corpo e salute",        # Salud y cuidado personal (Health & Personal Care)

    # Baby & Toys
    19649: "Neonati e bambini",              # Bebé (Baby)
    19663: "Neonati e bambini",              # Juguetes y juegos (Toys & Games)

    # Services (skip - not physical products)
    # 31548: excluded - Servicios (Services)
}

# Kaufland category IDs (from category tree - Level 1 only)
KAUFLAND_CATEGORY_IDS = {
    "Giardinaggio e fai da te": 23671,
    "Casa e arredamento": 1931,
    "Auto e moto": 56091,
    "Elettronica e computer": 34331,
    "Sport e attività all'aperto": 69055,
    "Articoli da cucina e per la casa": 9541,
    "Generi alimentari": 68972,
    "Moda e accessori": 1711,
    "Cura del corpo e salute": 11,
    "Neonati e bambini": 8321,
}


def load_config_from_yaml(country_code: str) -> dict:
    """Load configuration from YAML file for the specified country"""
    script_dir = Path(__file__).parent
    config_path = script_dir / 'config' / f'kaufland_{country_code.lower()}.yaml'

    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {}


@dataclass
class Config:
    """Configuration for feed generation"""
    margin: float = 0.43
    vat: float = 0.22
    base_price: float = 2
    max_price_eur: float = 1000.0
    min_price_eur: float = 15.0
    max_volume_cm3: int = 150000
    max_weight_kg: float = 28.0
    max_handling_days: int = 2  # Stock filtering: only include warehouses with 0-2 day handling
    sample_size: int = 10000  # Kaufland has 10MB file size limit (22MB/25k products ≈ 0.88KB/product → 11k products ≈ 9.7MB)
    # Kaufland allows all categories - no limit on products per category

    # BLACK FRIDAY SETTINGS - Set to True to enable, False to disable
    enable_black_friday: bool = False
    black_friday_prefix: str = "Black Friday OFFER - "

    # Shipping settings
    handling_time: int = 2
    delivery_time_min: int = 3
    delivery_time_max: int = 8

    @classmethod
    def from_yaml(cls, country_code: str) -> 'Config':
        """Create Config from YAML file"""
        yaml_config = load_config_from_yaml(country_code)

        if not yaml_config:
            return cls()

        pricing = yaml_config.get('pricing', {})
        filters = yaml_config.get('filters', {})
        promotions = yaml_config.get('promotions', {})
        shipping = yaml_config.get('shipping', {})

        return cls(
            margin=pricing.get('margin', 0.43),
            vat=pricing.get('vat', 0.22),
            base_price=pricing.get('base_price', 2),
            max_price_eur=pricing.get('max_price_eur', 1000.0),
            min_price_eur=pricing.get('min_price_eur', 15.0),
            max_volume_cm3=filters.get('max_volume_cm3', 150000),
            max_weight_kg=filters.get('max_weight_kg', 28.0),
            max_handling_days=filters.get('max_handling_days', 2),
            sample_size=filters.get('sample_size', 10000),
            enable_black_friday=promotions.get('enable_black_friday', False),
            black_friday_prefix=promotions.get('black_friday_prefix', "Black Friday OFFER - "),
            handling_time=shipping.get('handling_time', 2),
            delivery_time_min=shipping.get('delivery_time_min', 3),
            delivery_time_max=shipping.get('delivery_time_max', 8),
        )


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
            'FR': cls('fr-FR', 'fr', 'France', 'EUR', 1.0),
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

    def get_categories(self) -> List[Dict]:
        """Get whitelisted Kaufland-relevant categories"""
        # Return specific categories from KAUFLAND_CATEGORIES mapping
        # User note: "in kaufland we can upload all the categories!"
        return [
            {'id': cat_id, 'name': KAUFLAND_CATEGORIES.get(cat_id, 'Unknown')}
            for cat_id in KAUFLAND_CATEGORIES.keys()
        ]

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
        """Apply safety margins to prevent overselling"""
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
        
        # Stock check
        if total_stock <= 1:
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
        """Calculate final price in local currency ensuring margin after VAT and fees"""
        price_eur = (wholesale_eur * (1 + self.config.margin) + self.config.base_price) / (1 - self.config.vat)
        return price_eur * self.country.rate

class DataAggregator:
    """Aggregate and organize API data"""
    
    @staticmethod
    def build_stock_map(stock_data: List, var_stock_data: List,
                       max_handling_days: int = 2) -> Tuple[Dict, Dict]:
        """Build stock lookup maps with handling day filtering"""
        product_stock = {}
        variation_stock = {}

        for item in stock_data:
            sku = item.get('sku')
            if sku:
                # Filter by handling days - only include warehouses within acceptable time window
                total = sum(
                    s.get('quantity', 0)
                    for s in item.get('stocks', [])
                    if s.get('maxHandlingDays', 999) <= max_handling_days
                )
                if total > 0:
                    product_stock[sku] = total

        for item in var_stock_data:
            sku = item.get('sku')
            if sku:
                # Filter by handling days - only include warehouses within acceptable time window
                total = sum(
                    s.get('quantity', 0)
                    for s in item.get('stocks', [])
                    if s.get('maxHandlingDays', 999) <= max_handling_days
                )
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
    """Generate feed files"""
    
    def __init__(self, config: Config, country_config: CountryConfig):
        self.config = config
        self.country = country_config

    def create_product_row(self, product: Dict, info: Dict, images: List,
                          quantity: int, category_name: str = 'Giardinaggio e fai da te') -> Dict:
        """Create CSV row for product"""
        price = self._calculate_price(float(product.get('wholesalePrice', 0) or 0))

        # Apply Black Friday prefix if enabled
        base_title = (info.get('name', 'Product') or 'Product')
        if self.config.enable_black_friday:
            title = (self.config.black_friday_prefix + base_title)[:100]
        else:
            title = base_title[:100]

        return {
            'id_offer': str(product.get('sku', '')),
            'ean': str(product.get('ean13', '')),
            'locale': self.country.locale,
            'category': category_name,
            'title': title,
            'short_description': (info.get('description', '') or '')[:150],
            'description': (info.get('description', '') or '')[:500],
            'manufacturer': 'Pop Pulse Emporium',
            'picture_1': images[0] if len(images) > 0 else '',
            'picture_2': images[1] if len(images) > 1 else '',
            'picture_3': images[2] if len(images) > 2 else '',
            'picture_4': images[3] if len(images) > 3 else '',
            'price_cs': round(price, 2),
            'quantity': quantity,
            'condition': 'NEW',
            'length': round(float(product.get('depth', 0) or 0), 2),
            'width': round(float(product.get('width', 0) or 0), 2),
            'height': round(float(product.get('height', 0) or 0), 2),
            'weight': round(float(product.get('weight', 0) or 0), 2),
            'content_volume': round(float(product.get('width', 0) or 0) * 
                                   float(product.get('height', 0) or 0) * 
                                   float(product.get('depth', 0) or 0), 2),
            'currency': self.country.currency,
            'handling_time': self.config.handling_time,
            'delivery_time_max': self.config.delivery_time_max,
            'delivery_time_min': self.config.delivery_time_min
        }

    def _calculate_price(self, wholesale_eur: float) -> float:
        """Calculate final price"""
        price_eur = (wholesale_eur * (1 + self.config.vat) * 
                    (1 + self.config.margin) + self.config.base_price)
        return price_eur * self.country.rate

    def save_csv(self, data: List[Dict], filename: str) -> bool:
        """Save CSV file"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ CSV Error: {e}")
            return False

    def save_json(self, data: List[Dict], stats: Dict, filename: str, 
                  csv_filename: str) -> bool:
        """Save metadata JSON"""
        try:
            info = {
                "last_updated": datetime.now().isoformat(),
                "product_count": len(data),
                "validation_stats": stats,
                "stock_validation_enabled": True,
                "max_price_eur": self.config.max_price_eur,
                "min_price_eur": self.config.min_price_eur,
                "max_volume": self.config.max_volume_cm3,
                "max_weight": self.config.max_weight_kg,
                "currency": self.country.currency,
                "margin": f"{self.config.margin*100:.0f}%",
                "country": self.country.name,
                "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{csv_filename}"
            }
            
            with open(filename, 'w') as f:
                json.dump(info, f, indent=2)
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ JSON Error: {e}")
            return False

    def save_html(self, data: List[Dict], stats: Dict, filename: str, 
                  csv_filename: str) -> bool:
        """Save HTML dashboard"""
        try:
            prices = [row['price_cs'] for row in data]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            
            html = f"""<!DOCTYPE html>
<html lang="{self.country.language}">
<head>
    <meta charset="UTF-8">
    <title>Kaufland Feed - {self.country.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #667eea; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .feed-url code {{ background: white; padding: 10px; border-radius: 5px; display: block; word-break: break-all; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 10px; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #667eea; color: white; }}
        .price {{ color: #4caf50; font-weight: bold; }}
        img {{ max-width: 60px; max-height: 60px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ Kaufland Product Feed</h1>
        <p><strong>Pop Pulse Emporium</strong> - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <h2>🇪🇺 {self.country.name}</h2>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(data):,}</div>
            <div class="stat-label">Valid Products</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{self.config.margin*100:.0f}%</div>
            <div class="stat-label">Margin</div>
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
    
    <div class="feed-url">
        <h3>📡 Feed URL:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{csv_filename}</code>
    </div>
    
    <h3>📊 Sample Products (First 50)</h3>
    <table>
        <tr><th>Image</th><th>SKU</th><th>Title</th><th>EAN</th><th>Price</th><th>Stock</th></tr>"""
            
            for row in data[:50]:
                img = f'<img src="{row["picture_1"]}" alt="Product">' if row.get('picture_1') else 'No image'
                title = row['title'][:40] + '...' if len(row['title']) > 40 else row['title']
                html += f"""
        <tr>
            <td>{img}</td>
            <td>{row['id_offer']}</td>
            <td>{title}</td>
            <td>{row['ean']}</td>
            <td class="price">{row['currency']}{row['price_cs']:.2f}</td>
            <td><strong>{row['quantity']}</strong></td>
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
    print("🚀 KAUFLAND FEED GENERATOR")
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

    # Initialize components - load config from YAML
    config = Config.from_yaml(country_code)
    print(f"📋 Config loaded: margin={config.margin*100:.0f}%, min_price={config.min_price_eur}EUR, max_price={config.max_price_eur}EUR")
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
    categories = api.get_categories()
    if not categories:
        print("❌ No categories found")
        return
    
    print(f"📊 Processing {len(categories)} categories")
    
    # Collect all data
    all_products = []
    all_data = {'info': [], 'images': [], 'stock': [], 'var_stock': [], 'variations': []}
    product_to_category = {}  # Track which category each product belongs to

    print("\n🔄 Collecting data...")
    for i, category in enumerate(categories, 1):
        print(f"  {i}/{len(categories)}: {category['name']}")

        data = api.get_category_data(category['id'], country_config.language)

        # Get ALL products from category (no limit like ManoMano)
        products = data['products']
        random.shuffle(products)

        # Track which category each product belongs to
        for product in products:
            product_id = product.get('id')
            if product_id:
                product_to_category[product_id] = category['name']

        all_products.extend(products)
        
        all_data['info'].extend(data['info'])
        all_data['images'].extend(data['images'])
        all_data['stock'].extend(data['stock'])
        all_data['var_stock'].extend(data['var_stock'])
        all_data['variations'].extend(data['variations'])
        
        time.sleep(0.5)
    
    print(f"✅ Collected {len(all_products)} products")
    
    # Build lookup maps
    prod_stock, var_stock = aggregator.build_stock_map(
        all_data['stock'], all_data['var_stock'], config.max_handling_days
    )
    info_map = aggregator.build_info_map(all_data['info'])
    image_map = aggregator.build_image_map(all_data['images'])
    variation_map = aggregator.build_variation_map(all_data['variations'])
    
    print(f"📊 Stock entries: {len(prod_stock)} products, {len(var_stock)} variations")
    
    # Process products
    print("\n🔍 Validating products...")
    csv_data = []
    seen_eans = set()
    random.shuffle(all_products)
    
    for product in all_products:
        if len(csv_data) >= config.sample_size:
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
        
        # Create row
        images = image_map.get(product.get('id'), [])
        # Get category for this product
        product_id = product.get('id')
        category_name = product_to_category.get(product_id, 'Giardinaggio e fai da te')
        row = generator.create_product_row(product, info_map[sku], images, safe_qty, category_name)
        csv_data.append(row)
        
        if validator.stats['total'] % 1000 == 0:
            print(f"  Processed {validator.stats['total']:,}, found {validator.stats['valid']:,} valid")
    
    # Print stats
    print(f"\n📈 Validation Results:")
    for key, value in validator.stats.items():
        if value > 0:
            print(f"   {key}: {value:,}")
    
    if not csv_data:
        print("❌ No valid products found")
        return
    
    print(f"\n✅ {len(csv_data)} unique products ready")
    
    # Generate filenames (consistent naming for all countries)
    csv_file = f'kaufland_feed_{country_code.lower()}.csv'
    html_file = f'index_{country_code.lower()}.html'
    json_file = f'feed_info_{country_code.lower()}.json'
    
    # Save files
    print("\n📁 Creating files...")
    generator.save_csv(csv_data, csv_file)
    generator.save_json(csv_data, validator.stats, json_file, csv_file)
    generator.save_html(csv_data, validator.stats, html_file, csv_file)
    
    # Summary
    print("\n" + "=" * 70)
    print("🎉 FEED GENERATION COMPLETE")
    print("=" * 70)
    print(f"📊 Products: {len(csv_data)}")
    print(f"🌐 Feed URL: https://poppulseemporium.github.io/kaufland-feed/{csv_file}")
    print(f"✅ All products have validated stock and complete data")


if __name__ == "__main__":
    main()

## HOW TO RUN:
# $env:BIGBUY_API_KEY="YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"; 
# $env:COUNTRY_CODE="IT"; 
# python bigbuy_kaufland.py
