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
    def get_all_countries(cls) -> Dict[str, 'CountryConfig']:
        """Get all country configurations"""
        return {
            'AT': cls('de-AT', 'de', 'Austria', 'EUR', 1.0),
            'DE': cls('de-DE', 'de', 'Germany', 'EUR', 1.0),
            'SK': cls('sk-SK', 'sk', 'Slovakia', 'EUR', 1.0),
            'PL': cls('pl-PL', 'pl', 'Poland', 'PLN', 4.5),
            'CZ': cls('cs-CZ', 'cs', 'Czech Republic', 'CZK', 24.0)
        }

    @classmethod
    def get(cls, country_code: str) -> Optional['CountryConfig']:
        return cls.get_all_countries().get(country_code.upper())


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
        """Get all data for a category"""
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
        """Apply safety margins - min 2 units in feed"""
        if bigbuy_stock <= 2:
            return 0
        elif bigbuy_stock <= 5:
            return 2
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
    
    def __init__(self, config: Config):
        self.config = config
        self.stats = {
            'total': 0, 'invalid_ean': 0, 'not_new': 0,
            'no_stock': 0, 'no_info': 0, 'price_high': 0,
            'price_low': 0, 'weight_high': 0, 'volume_high': 0,
            'valid': 0
        }

    def validate(self, product: Dict, info: Dict, total_stock: int) -> Tuple[bool, str]:
        """Validate product against all rules (price in EUR)"""
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
        
        # Price check (in EUR)
        wholesale_eur = float(product.get('wholesalePrice', 0) or 0)
        price_eur = (wholesale_eur * (1 + self.config.vat) * 
                    (1 + self.config.margin) + self.config.base_price)
        
        if price_eur > self.config.max_price_eur:
            self.stats['price_high'] += 1
            return False, f"Price too high: {price_eur}"
        
        if price_eur < self.config.min_price_eur:
            self.stats['price_low'] += 1
            return False, f"Price too low: {price_eur}"
        
        self.stats['valid'] += 1
        return True, "Valid"


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
    
    def __init__(self, config: Config):
        self.config = config

    def create_product_row(self, product: Dict, info_by_lang: Dict, 
                          images: List, locale: str) -> Dict:
        """Create product catalog row for specific locale"""
        info = info_by_lang.get(locale.split('-')[0], {})  # Get language from locale
        
        return {
            'ean': str(product.get('ean13', '')),
            'locale': locale,
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

    def create_offer_row(self, product: Dict, quantity: int, 
                        country_config: CountryConfig) -> Dict:
        """Create offer row for specific country"""
        wholesale_eur = float(product.get('wholesalePrice', 0) or 0)
        price_eur = (wholesale_eur * (1 + self.config.vat) * 
                    (1 + self.config.margin) + self.config.base_price)
        price_local = price_eur * country_config.rate
        
        return {
            'ean': str(product.get('ean13', '')),
            'id_offer': str(product.get('sku', '')),
            'condition': '100',
            'price': str(round(price_local, 2)),
            'currency': country_config.currency,
            'quantity': str(quantity),
            'handling_time': '2',
            'delivery_time_min': '3',
            'delivery_time_max': '8'
        }

    def save_csv(self, data: List[Dict], filename: str, separator: str = ';') -> bool:
        """Save CSV file with Kaufland format"""
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

    def save_json(self, product_count: int, offer_counts: Dict, stats: Dict, 
                  filename: str) -> bool:
        """Save metadata JSON"""
        try:
            info = {
                "last_updated": datetime.now().isoformat(),
                "feed_type": "MULTI_LANGUAGE_PRODUCT_SEPARATED_OFFERS",
                "product_count": product_count,
                "offer_counts": offer_counts,
                "validation_stats": stats,
                "stock_validation_enabled": True,
                "min_stock_in_feed": 2,
                "max_price_eur": self.config.max_price_eur,
                "min_price_eur": self.config.min_price_eur,
                "countries": list(offer_counts.keys()),
                "product_feed_info": "ONE file with ALL languages - upload manually",
                "offer_feed_info": "SEPARATE files per country for FX - auto-upload 3x daily"
            }
            
            with open(filename, 'w') as f:
                json.dump(info, f, indent=2)
            print(f"✅ Created {filename}")
            return True
        except Exception as e:
            print(f"❌ JSON Error: {e}")
            return False


def main():
    """Main execution - generates multi-language product feed + per-country offers"""
    print("🚀 KAUFLAND MULTI-LANGUAGE FEED GENERATOR")
    print("=" * 70)
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ BIGBUY_API_KEY environment variable not set")
        return
    
    # Get all country configurations
    all_countries = CountryConfig.get_all_countries()
    
    print(f"🌍 Generating feeds for: {', '.join(all_countries.keys())}")
    
    # Initialize components
    config = Config()
    api = BigBuyAPI(api_key)
    validator = ProductValidator(config)
    aggregator = DataAggregator()
    generator = FeedGenerator(config)
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
    
    # Collect data for ALL languages
    all_products = []
    all_data_by_lang = {}
    
    print("\n🔄 Collecting data for all languages...")
    
    # Collect for each language
    for country_code, country_config in all_countries.items():
        lang = country_config.language
        if lang in all_data_by_lang:
            print(f"  ⏭️ Skipping {country_code} - already have {lang} data")
            continue
        
        print(f"  📚 Collecting {lang} ({country_code})...")
        all_data_by_lang[lang] = {'info': [], 'images': [], 'stock': [], 'var_stock': [], 'variations': []}
        
        for i, category in enumerate(categories, 1):
            if i % 5 == 0:
                print(f"     Category {i}/{len(categories)}...")
            
            data = api.get_category_data(category['id'], lang)
            
            # Collect products only once (from first language)
            if not all_products:
                products = data['products'][:config.products_per_category]
                random.shuffle(products)
                all_products.extend(products)
            
            all_data_by_lang[lang]['info'].extend(data['info'])
            all_data_by_lang[lang]['images'].extend(data['images'])
            all_data_by_lang[lang]['stock'].extend(data['stock'])
            all_data_by_lang[lang]['var_stock'].extend(data['var_stock'])
            all_data_by_lang[lang]['variations'].extend(data['variations'])
            
            time.sleep(0.3)
    
    print(f"✅ Collected {len(all_products)} products")
    print(f"✅ Collected data for languages: {', '.join(all_data_by_lang.keys())}")
    
    # Use German data for building maps (any language works for stock/images)
    de_data = all_data_by_lang.get('de', all_data_by_lang[list(all_data_by_lang.keys())[0]])
    
    prod_stock, var_stock = aggregator.build_stock_map(de_data['stock'], de_data['var_stock'])
    image_map = aggregator.build_image_map(de_data['images'])
    variation_map = aggregator.build_variation_map(de_data['variations'])
    
    # Build info maps for each language
    info_maps = {}
    for lang, data in all_data_by_lang.items():
        info_maps[lang] = aggregator.build_info_map(data['info'])
    
    print(f"📊 Stock entries: {len(prod_stock)} products, {len(var_stock)} variations")
    
    # Process products
    print("\n🔍 Validating products...")
    valid_products = []
    seen_eans = set()
    random.shuffle(all_products)
    
    for product in all_products:
        if len(valid_products) >= config.sample_size:
            break
        
        sku = product.get('sku')
        if not sku:
            continue
        
        # Check if we have info in at least one language
        has_info = any(sku in info_maps[lang] for lang in info_maps)
        if not has_info:
            continue
        
        # Use German info for validation (or first available)
        info_for_validation = info_maps.get('de', {}).get(sku) or next(
            (info_maps[lang].get(sku) for lang in info_maps if sku in info_maps[lang]), None
        )
        
        if not info_for_validation:
            continue
        
        # Calculate stock
        total_stock = aggregator.calculate_total_stock(
            product, variation_map, prod_stock, var_stock
        )
        
        # Validate
        is_valid, msg = validator.validate(product, info_for_validation, total_stock)
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
        
        valid_products.append({
            'product': product,
            'quantity': safe_qty,
            'images': image_map.get(product.get('id'), [])
        })
        
        if validator.stats['total'] % 1000 == 0:
            print(f"  Processed {validator.stats['total']:,}, found {validator.stats['valid']:,} valid")
    
    # Print stats
    print(f"\n📈 Validation Results:")
    for key, value in validator.stats.items():
        if value > 0:
            print(f"   {key}: {value:,}")
    
    if not valid_products:
        print("❌ No valid products found")
        return
    
    print(f"\n✅ {len(valid_products)} valid products")
    
    # Generate multi-language product feed
    print("\n📦 Creating multi-language product feed...")
    product_rows = []
    
    for item in valid_products:
        product = item['product']
        images = item['images']
        
        # Create one row per language/locale
        for country_code, country_config in all_countries.items():
            lang = country_config.language
            
            # Get info for this language
            info_by_lang = {}
            for l in info_maps:
                sku = product.get('sku')
                if sku in info_maps[l]:
                    info_by_lang[l] = info_maps[l][sku]
            
            row = generator.create_product_row(product, info_by_lang, images, country_config.locale)
            product_rows.append(row)
    
    print(f"✅ Created {len(product_rows)} product rows (multiple languages)")
    
    # Generate per-country offer feeds
    print("\n💰 Creating per-country offer feeds...")
    offer_data_by_country = {}
    
    for country_code, country_config in all_countries.items():
        offers = []
        for item in valid_products:
            offer_row = generator.create_offer_row(item['product'], item['quantity'], country_config)
            offers.append(offer_row)
        offer_data_by_country[country_code] = offers
        print(f"✅ {country_code}: {len(offers)} offers")
    
    # Save files
    print("\n📁 Saving files...")
    
    # Save single multi-language product feed
    product_file = 'kaufland_products_all.csv'
    generator.save_csv(product_rows, product_file, separator=';')
    
    # Save per-country offer feeds
    offer_counts = {}
    for country_code, offers in offer_data_by_country.items():
        offer_file = f'kaufland_offers_{country_code.lower()}.csv'
        generator.save_csv(offers, offer_file, separator=';')
        offer_counts[country_code] = len(offers)
    
    # Save metadata
    generator.save_json(len(valid_products), offer_counts, validator.stats, 'feed_info.json')
    
    # Summary
    print("\n" + "=" * 70)
    print("🎉 MULTI-LANGUAGE FEED GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n📦 ONE Product Feed (all languages):")
    print(f"   {product_file} ({len(product_rows)} rows = {len(valid_products)} products × {len(all_countries)} languages)")
    print(f"   Upload manually to Kaufland - contains ALL translations!")
    
    print(f"\n💰 Offer Feeds (per country):")
    for country_code, count in offer_counts.items():
        country = all_countries[country_code]
        print(f"   kaufland_offers_{country_code.lower()}.csv - {count} offers ({country.currency})")
    print(f"   Auto-upload 3x daily - NO translation needed!")
    
    print(f"\n🌐 URLs:")
    print(f"   📦 https://poppulseemporium.github.io/kaufland-feed/{product_file}")
    for country_code in offer_counts:
        print(f"   💰 https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_{country_code.lower()}.csv")
    
    print(f"\n📋 Setup:")
    print(f"   1. Upload {product_file} manually to Kaufland (rare)")
    print(f"   2. Configure auto-upload for offer files per country")
    print(f"   3. Done! Offers update 3x daily automatically")


if __name__ == "__main__":
    main()
