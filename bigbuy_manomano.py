import requests
import csv
import json
import os
import random
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ------------------------- Configs -------------------------

@dataclass
class Config:
    """Configuration for feed generation"""
    margin: float = 0.45
    vat: float = 0.22
    base_price: float = 0.25
    max_price_eur: float = 1000.0
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
            'CZ': cls('cs-CZ', 'cs', 'Czech Republic', 'CZK', 24.0),
        }
        return configs.get(country_code.upper())


# ------------------------- API -------------------------

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

    def get_categories(self, limit: int = 20) -> List[Dict]:
        """Get filtered and randomized categories"""
        result = self._request("/rest/catalog/taxonomies.json?firstLevel")
        if not result:
            return []
        # filter adult content
        erotic_keywords = ['erotic', 'erotico', 'adult', 'sex', 'sexy', 'intimate', 'lingerie']
        filtered = [t for t in result if not any(kw in t.get('name', '').lower() for kw in erotic_keywords)]
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


# ------------------------- Helpers -------------------------

class StockCalculator:
    """Calculate safe stock quantities"""
    @staticmethod
    def calculate_safe_quantity(bigbuy_stock: int) -> int:
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
    """Validate products against business rules"""
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
        self.stats['total'] += 1

        # EAN
        ean = str(product.get('ean13', '')).strip()
        if len(ean) != 13 or not ean.isdigit():
            self.stats['invalid_ean'] += 1
            return False, f"Invalid EAN: {ean}"

        # Condition
        if product.get('condition', '').upper() != 'NEW':
            self.stats['not_new'] += 1
            return False, "Not NEW condition"

        # Stock
        if total_stock <= 1:
            self.stats['no_stock'] += 1
            return False, "Insufficient stock"

        # Info
        if not info or len(info.get('name', '').strip()) < 3:
            self.stats['no_info'] += 1
            return False, "Missing product info"

        # Weight
        weight = float(product.get('weight', 0) or 0)
        if weight > self.config.max_weight_kg:
            self.stats['weight_high'] += 1
            return False, f"Weight too high: {weight}kg"

        # Volume
        volume = (float(product.get('width', 0) or 0) *
                  float(product.get('height', 0) or 0) *
                  float(product.get('depth', 0) or 0))
        if volume > self.config.max_volume_cm3:
            self.stats['volume_high'] += 1
            return False, f"Volume too high: {volume}cm³"

        # Price
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
        price_eur = (wholesale_eur * (1 + self.config.vat) *
                     (1 + self.config.margin) + self.config.base_price)
        return price_eur * self.country.rate


class DataAggregator:
    """Aggregate and organize API data"""
    @staticmethod
    def build_stock_map(stock_data: List, var_stock_data: List) -> Tuple[Dict, Dict]:
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
        return {item['sku']: item for item in info_data}

    @staticmethod
    def build_image_map(image_data: List) -> Dict:
        result = {}
        for img_set in image_data:
            images = img_set.get('images', [])
            if images:
                result[img_set['id']] = [img.get('url', '') for img in images[:5]]
        return result

    @staticmethod
    def build_variation_map(var_data: List) -> Dict:
        result = {}
        for var in var_data:
            pid = var.get('product')
            if pid:
                result.setdefault(pid, []).append(var)
        return result

    @staticmethod
    def calculate_total_stock(product: Dict, variations: Dict,
                              prod_stock: Dict, var_stock: Dict) -> int:
        sku = product.get('sku')
        pid = product.get('id')

        direct_stock = prod_stock.get(sku, 0)
        variation_stock = 0

        if pid in variations:
            for var in variations[pid]:
                var_sku = var.get('sku')
                variation_stock += var_stock.get(var_sku, 0)

        return direct_stock + variation_stock


# ------------------------- ManoMano generator -------------------------

class ManoManoFeedGenerator:
    """
    Generate rows matching ManoMano format:
    ['sku','ean','sku_manufacturer','brand','category','title','description',
     'picture_1','picture_2','picture_3','picture_4','picture_5',
     'product_price_vat_inc','min_quantity','increment','quantity',
     'use_grid','carrier_grid_1','shipping_time_carrier_grid_1',
     'weight','length','width','height','DisplayWeight','volume',
     'parent_sku','parent_title']
    """
    COLS = [
        'sku','ean','sku_manufacturer','brand','category','title','description',
        'picture_1','picture_2','picture_3','picture_4','picture_5',
        'product_price_vat_inc','min_quantity','increment','quantity',
        'use_grid','carrier_grid_1','shipping_time_carrier_grid_1',
        'weight','length','width','height','DisplayWeight','volume',
        'parent_sku','parent_title'
    ]

    def __init__(self, config: Config, country_config: CountryConfig):
        self.config = config
        self.country = country_config

    def _price_local(self, wholesale_eur: float) -> float:
        price_eur = (wholesale_eur * (1 + self.config.vat) *
                     (1 + self.config.margin) + self.config.base_price)
        return price_eur * self.country.rate

    def create_row(self, product: Dict, info: Dict, images: List, quantity: int,
                   parent_sku: Optional[str] = None, parent_title: Optional[str] = None) -> Dict:
        price = self._price_local(float(product.get('wholesalePrice', 0) or 0))
        weight = float(product.get('weight', 0) or 0)
        length = float(product.get('depth', 0) or 0)
        width  = float(product.get('width', 0) or 0)
        height = float(product.get('height', 0) or 0)
        volume = width * height * length

        # ManoMano specifics / safe defaults
        min_qty = 1
        increment = 1
        use_grid = 0
        carrier_grid_1 = "standard"
        shipping_time = "3#8"  # 3–8 days

        imgs = (images + ["", "", "", "", ""])[:5]
        brand = info.get('brand') or "Pop Pulse Emporium"

        return {
            'sku': str(product.get('sku', '')),
            'ean': str(product.get('ean13', '')),
            'sku_manufacturer': str(product.get('sku', '')),
            'brand': brand,
            'category': 'Gardening & DIY',
            'title': (info.get('name', 'Product') or 'Product')[:150],
            'description': (info.get('description', '') or '')[:5000],
            'picture_1': imgs[0],
            'picture_2': imgs[1],
            'picture_3': imgs[2],
            'picture_4': imgs[3],
            'picture_5': imgs[4],
            'product_price_vat_inc': round(price, 2),
            'min_quantity': min_qty,
            'increment': increment,
            'quantity': quantity,
            'use_grid': use_grid,
            'carrier_grid_1': carrier_grid_1,
            'shipping_time_carrier_grid_1': shipping_time,
            'weight': round(weight, 2),
            'length': round(length, 2),
            'width': round(width, 2),
            'height': round(height, 2),
            'DisplayWeight': round(weight, 2),
            'volume': round(volume, 2),
            'parent_sku': str(parent_sku or product.get('id', '') or ''),
            'parent_title': parent_title or (info.get('name', '') or '')
        }

    def save_csv(self, rows: List[Dict], filename: str) -> bool:
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=self.COLS)
                w.writeheader()
                for r in rows:
                    w.writerow({k: r.get(k, "") for k in self.COLS})
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ CSV Error: {e}")
            return False

    def save_json(self, data: List[Dict], stats: Dict, filename: str, csv_filename: str) -> bool:
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

    def save_html(self, data: List[Dict], stats: Dict, filename: str, csv_filename: str) -> bool:
        try:
            prices = [row['product_price_vat_inc'] for row in data]
            min_price = min(prices) if prices else 0
            max_price = max(prices) if prices else 0
            html = f"""<!DOCTYPE html>
<html lang="{self.country.language}">
<head>
<meta charset="UTF-8">
<title>ManoMano Feed - {self.country.name}</title>
<style>
 body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
 .header {{ background: #0ea5e9; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
 .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
 .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
 .stat-number {{ font-size: 28px; font-weight: bold; color: #0ea5e9; }}
 .stat-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
 .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; }}
 .feed-url code {{ background: white; padding: 10px; border-radius: 5px; display: block; word-break: break-all; margin: 10px 0; }}
 table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 10px; margin-top: 20px; }}
 th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
 th {{ background: #0ea5e9; color: white; }}
 .price {{ color: #16a34a; font-weight: bold; }}
 img {{ max-width: 60px; max-height: 60px; }}
</style>
</head>
<body>
 <div class="header">
   <h1>🛍️ ManoMano Product Feed</h1>
   <p><strong>Pop Pulse Emporium</strong> - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
 </div>
 <h2>🇪🇺 {self.country.name}</h2>
 <div class="stats">
   <div class="stat-box"><div class="stat-number">{len(data):,}</div><div class="stat-label">Valid Products</div></div>
   <div class="stat-box"><div class="stat-number">{self.config.margin*100:.0f}%</div><div class="stat-label">Margin</div></div>
   <div class="stat-box"><div class="stat-number">{self.country.currency}{min_price:.2f}</div><div class="stat-label">Min Price</div></div>
   <div class="stat-box"><div class="stat-number">{self.country.currency}{max_price:.2f}</div><div class="stat-label">Max Price</div></div>
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
     <td>{row['sku']}</td>
     <td>{title}</td>
     <td>{row['ean']}</td>
     <td class="price">{self.country.currency}{row['product_price_vat_inc']:.2f}</td>
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


# ------------------------- Main -------------------------

def main():
    print("🚀 MANOMANO FEED GENERATOR (BigBuy)")
    print("=" * 70)

    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ BIGBUY_API_KEY environment variable not set")
        return

    country_code = os.getenv('COUNTRY_CODE', 'IT').upper()
    country_config = CountryConfig.get(country_code)
    if not country_config:
        print(f"❌ Unsupported country: {country_code}")
        return

    print(f"🌍 Country: {country_config.name}")
    print(f"💱 Currency: {country_config.currency}")

    config = Config()
    api = BigBuyAPI(api_key)
    validator = ProductValidator(config, country_config)
    aggregator = DataAggregator()
    generator = ManoManoFeedGenerator(config, country_config)
    stock_calc = StockCalculator()

    seed = datetime.now().hour + datetime.now().day * 24
    random.seed(seed)
    print(f"🎲 Random seed: {seed}")

    categories = api.get_categories(config.categories_limit)
    if not categories:
        print("❌ No categories found")
        return
    print(f"📊 Processing {len(categories)} categories")

    all_products = []
    all_data = {'info': [], 'images': [], 'stock': [], 'var_stock': [], 'variations': []}

    print("\n🔄 Collecting data...")
    for i, category in enumerate(categories, 1):
        print(f"  {i}/{len(categories)}: {category['name']}")
        data = api.get_category_data(category['id'], country_config.language)

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

    prod_stock, var_stock = aggregator.build_stock_map(all_data['stock'], all_data['var_stock'])
    info_map = aggregator.build_info_map(all_data['info'])
    image_map = aggregator.build_image_map(all_data['images'])
    variation_map = aggregator.build_variation_map(all_data['variations'])

    print(f"📊 Stock entries: {len(prod_stock)} products, {len(var_stock)} variations")

    print("\n🔍 Validating products...")
    rows = []
    seen_eans = set()
    random.shuffle(all_products)

    for product in all_products:
        if len(rows) >= config.sample_size:
            break

        sku = product.get('sku')
        if not sku or sku not in info_map:
            continue

        total_stock = aggregator.calculate_total_stock(product, variation_map, prod_stock, var_stock)
        is_valid, _ = validator.validate(product, info_map[sku], total_stock)
        if not is_valid:
            continue

        ean = str(product.get('ean13', ''))
        if ean in seen_eans:
            continue
        seen_eans.add(ean)

        safe_qty = stock_calc.calculate_safe_quantity(total_stock)
        if safe_qty <= 0:
            continue

        images = image_map.get(product.get('id'), [])
        row = generator.create_row(
            product, info_map[sku], images, safe_qty,
            parent_sku=product.get('id'),
            parent_title=info_map[sku].get('name')
        )
        rows.append(row)

        if validator.stats['total'] % 1000 == 0:
            print(f"  Processed {validator.stats['total']:,}, found {validator.stats['valid']:,} valid")

    print(f"\n📈 Validation Results:")
    for key, value in validator.stats.items():
        if value > 0:
            print(f"   {key}: {value:,}")

    if not rows:
        print("❌ No valid products found")
        return

    print(f"\n✅ {len(rows)} unique products ready")

    # Always use _cc suffix (matches your workflow checks)
    cc = country_code.lower()
    csv_file  = f'manomano_feed_{cc}.csv'
    html_file = f'manomano_index_{cc}.html'
    json_file = f'manomano_info_{cc}.json'

    print("\n📁 Creating files...")
    generator.save_csv(rows, csv_file)
    generator.save_json(rows, validator.stats, json_file, csv_file)
    generator.save_html(rows, validator.stats, html_file, csv_file)

    print("\n" + "=" * 70)
    print("🎉 FEED GENERATION COMPLETE")
    print("=" * 70)
    print(f"📊 Products: {len(rows)}")
    print(f"🌐 Feed URL: https://poppulseemporium.github.io/kaufland-feed/{csv_file}")
    print(f"✅ All products have validated stock and complete data")


if __name__ == "__main__":
    main()
