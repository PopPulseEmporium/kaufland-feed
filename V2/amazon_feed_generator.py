"""
Amazon NA Feed Generator - BigBuy to Amazon USA/Canada/Mexico
Generates tab-delimited feed files for Amazon Seller Central

Supports two Amazon templates:
- Template 1: Home & Kitchen, Lighting, Tools (504 columns)
- Template 2: Electronics, Auto, Health, Sexual Wellness, etc. (999 columns)
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json
import os
import re
import time
import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from html import unescape
from openpyxl import Workbook

# ------------------------- Configuration -------------------------

@dataclass
class MarketConfig:
    """Market-specific configuration"""
    marketplace_id: str
    currency: str
    exchange_rate: float  # EUR to local currency
    language: str
    name: str
    vat_rate: float = 0.0  # VAT/IVA rate for price calculation

    @classmethod
    def get_all(cls) -> Dict[str, 'MarketConfig']:
        return {
            'US': cls('ATVPDKIKX0DER', 'USD', 1.08, 'en', 'USA', 0.0),
            'CA': cls('A2EUQ1WTGCTBG2', 'CAD', 1.47, 'en', 'Canada', 0.0),
            'MX': cls('A1AM78C64UM0Y8', 'MXN', 18.50, 'es', 'Mexico', 0.16),  # 16% IVA
        }


@dataclass
class Config:
    """Global configuration for feed generation"""
    # Pricing parameters
    margin: float = 0.70  # n% margin (same as Kaufland)
    vat: float = 0.22  # 22% VAT for base price calculation (applied before market-specific)
    base_price: float = 2.25  # Base handling fee in EUR (same as ManoMano/Kaufland)

    # Price limits (in EUR)
    max_price_eur: float = 500.0  # Maximum price threshold
    min_price_eur: float = 10.0  # Minimum price threshold

    # Product limits
    max_volume_cm3: int = 30000  # Maximum volume (larger for Amazon)
    max_weight_kg: float = 10.0  # Maximum weight
    max_handling_days: int = 2  # Include stock with 0-2 day handling
    max_products: int = 9997  # Maximum products per feed (Amazon limit is 10k rows, minus 3 header rows)

    # Fulfillment
    default_brand: str = "Pop Pulse Emporium"
    lead_time_days: int = 7  # Days to ship (BigBuy processing + shipping)

    # Promotions - BLACK FRIDAY SETTINGS
    enable_black_friday: bool = False  # Set to True to enable
    black_friday_prefix: str = "Black Friday OFFER - "
    black_friday_discount: float = 30.0  # Additional discount (0.10 = 10% off)


# BigBuy Category to Amazon Template/Product Type Mapping
# Format: bigbuy_id: (template_num, feed_product_type, item_type)
CATEGORY_MAPPING = {
    # Template 1 categories (Home & Kitchen, Lighting, Tools)
    19656: (1, 'home', 'bathroom-accessories'),  # Hogar y cocina
    19657: (1, 'lightsandfixtures', 'pendant-lights'),  # Iluminación
    19651: (1, 'home', 'electrical-ballasts'),  # Bricolaje y herramientas
    19658: (1, 'home', 'electrical-ballasts'),  # Industria
    19649: (1, 'home', 'bathroom-accessories'),  # Bebé (limited)
    19654: (1, 'home', 'bathroom-accessories'),  # Equipaje (limited)

    # Template 2 categories
    19661: (2, 'gardentoolset', 'garden-tool-sets'),  # Jardín
    19664: (2, 'officeelectronics', 'cash-registers'),  # Oficina
    19652: (2, 'carelectronics', 'vehicle-remote-start'),  # Coche y moto
    19668: (2, 'protectivegear', 'powersports-helmet-hardware'),  # Ropa
    19671: (2, 'protectivegear', 'powersports-knee-sliders'),  # Zapatos
    19662: (2, 'bracelet', 'link-bracelets'),  # Joyería
    19667: (2, 'watches', 'watches'),  # Relojes
    19653: (2, 'securityelectronics', 'security-electronics'),  # Electrónica
    19685: (2, 'officeelectronics', 'cash-registers'),  # Informática
    19650: (2, 'beautymisc', 'lip-care-products'),  # Belleza
    19669: (2, 'healthmisc', 'massage-tools-and-equipment'),  # Salud
    19666: (2, 'petfeeder', 'pet-feeders'),  # Mascotas
    19754: (2, 'sportinggoods', 'sports-fan-billiard-lighting'),  # Deportes
    19663: (2, 'sportinggoods', 'sports-fan-billiard-lighting'),  # Juguetes

    # Sexual Wellness (Template 2 - healthmisc)
    17088: (2, 'healthmisc', 'vibrators'),  # Sexo y sensualidad (main)
    17172: (2, 'healthmisc', 'vibrators'),  # Vibradores
    17173: (2, 'healthmisc', 'vibrators'),  # Balas y huevos
    17176: (2, 'healthmisc', 'vibrators'),  # Vibradores anales
    17177: (2, 'healthmisc', 'vibrators'),  # Vibradores clásicos
    17178: (2, 'healthmisc', 'vibrators'),  # Vibradores de pareja
    17179: (2, 'healthmisc', 'vibrators'),  # Vibradores dobles
    17180: (2, 'healthmisc', 'vibrators'),  # Vibradores Punto G
    17181: (2, 'healthmisc', 'vibrators'),  # Vibradores realistas
    17190: (2, 'healthmisc', 'sex-toys'),  # Potenciadores sexuales
    17208: (2, 'healthmisc', 'sex-toys'),  # Sexo seguro
}

# Default mapping for unmapped categories
DEFAULT_MAPPING = (2, 'home', 'home')


# ------------------------- BigBuy API -------------------------

class BigBuyAPI:
    """BigBuy API client - reused from ManoMano generator"""

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
            r = requests.get(url, headers=self.headers, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"  API Error ({endpoint}): {e}")
            return None

    def get_category_data(self, taxonomy_id: int, language: str) -> Dict:
        """Get all data for a category"""
        print(f"  Fetching data for category {taxonomy_id} (lang={language})...")
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


class TextProcessor:
    """Process text for Amazon requirements"""

    @staticmethod
    def strip_html(text: str) -> str:
        """Remove HTML tags and decode entities"""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', ' ', text)
        # Decode HTML entities
        clean = unescape(clean)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean

    @staticmethod
    def truncate(text: str, max_length: int) -> str:
        """Truncate text to max length"""
        if not text or len(text) <= max_length:
            return text or ""
        return text[:max_length-3] + "..."

    @staticmethod
    def extract_bullet_points(description: str, count: int = 5) -> List[str]:
        """Extract bullet points from description"""
        if not description:
            return [""] * count

        clean = TextProcessor.strip_html(description)
        sentences = re.split(r'[.!?]', clean)
        bullets = []

        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 20 and len(sent) < 500:
                bullets.append(TextProcessor.truncate(sent, 500))
                if len(bullets) >= count:
                    break

        # Pad with empty strings if not enough
        while len(bullets) < count:
            bullets.append("")

        return bullets[:count]


class DataAggregator:
    """Aggregate and organize API data"""

    @staticmethod
    def build_stock_map(stock_data: List, var_stock_data: List, max_handling_days: int = 2) -> Tuple[Dict, Dict]:
        """Build stock maps filtering by handling days"""
        product_stock = {}
        variation_stock = {}

        for item in stock_data:
            sku = item.get('sku')
            if sku:
                total = sum(
                    s.get('quantity', 0)
                    for s in item.get('stocks', [])
                    if s.get('maxHandlingDays', 999) <= max_handling_days
                )
                product_stock[sku] = total

        for item in var_stock_data:
            sku = item.get('sku')
            if sku:
                total = sum(
                    s.get('quantity', 0)
                    for s in item.get('stocks', [])
                    if s.get('maxHandlingDays', 999) <= max_handling_days
                )
                variation_stock[sku] = total

        return product_stock, variation_stock

    @staticmethod
    def build_info_map(info_data: List) -> Dict:
        return {item['sku']: item for item in info_data if 'sku' in item}

    @staticmethod
    def build_image_map(image_data: List) -> Dict:
        result = {}
        for img_set in image_data:
            images = img_set.get('images', [])
            if images:
                result[img_set['id']] = [img.get('url', '') for img in images[:8]]
        return result

    @staticmethod
    def build_variation_map(var_data: List) -> Dict:
        """Map variations by parent product ID"""
        result = {}
        for var in var_data:
            pid = var.get('product')
            if pid:
                result.setdefault(pid, []).append(var)
        return result


# ------------------------- Amazon Feed Generator -------------------------

class AmazonFeedGenerator:
    """Generate Amazon feed rows"""

    def __init__(self, config: Config, market: MarketConfig, template_num: int):
        self.config = config
        self.market = market
        self.template_num = template_num
        self.stats = {
            'total': 0,
            'valid': 0,
            'invalid_ean': 0,
            'no_stock': 0,
            'price_error': 0,
            'parents': 0,
            'children': 0
        }

    def calculate_price(self, wholesale_eur: float) -> float:
        """Calculate final price in market currency

        Formula: (wholesale * (1 + VAT) * (1 + margin) + base_price) * exchange_rate

        For markets with their own VAT (like Mexico 16% IVA),
        the market VAT is applied on top.
        """
        # Apply base VAT (EU standard)
        price_with_vat = wholesale_eur * (1 + self.config.vat)
        # Apply margin
        price_with_margin = price_with_vat * (1 + self.config.margin)
        # Add base price/fee
        price_eur = price_with_margin + self.config.base_price

        # Apply market-specific VAT if applicable (e.g., Mexico IVA)
        if self.market.vat_rate > 0:
            price_eur = price_eur * (1 + self.market.vat_rate)

        # Apply Black Friday discount if enabled
        if self.config.enable_black_friday and self.config.black_friday_discount > 0:
            price_eur = price_eur * (1 - self.config.black_friday_discount)

        # Convert to market currency
        return round(price_eur * self.market.exchange_rate, 2)

    def validate_product(self, product: Dict, info: Dict, stock: int) -> Tuple[bool, str]:
        """Validate product for Amazon listing"""
        self.stats['total'] += 1

        # EAN validation
        ean = str(product.get('ean13', '')).strip()
        if not ean or ean == 'None' or len(ean) != 13 or not ean.isdigit():
            self.stats['invalid_ean'] += 1
            return False, f"Invalid EAN: {ean}"

        # Condition check
        if product.get('condition', '').upper() != 'NEW':
            return False, "Not NEW condition"

        # Stock check - must have at least 2 units (same as Kaufland)
        if stock is None or stock <= 1:
            self.stats['no_stock'] += 1
            return False, "Insufficient stock"

        # Info check
        if not info or len(info.get('name', '').strip()) < 3:
            return False, "Missing product info"

        # Weight check
        weight = float(product.get('weight', 0) or 0)
        if weight > self.config.max_weight_kg:
            return False, f"Weight too high: {weight}kg"

        # Volume check
        volume = (float(product.get('width', 0) or 0) *
                  float(product.get('height', 0) or 0) *
                  float(product.get('depth', 0) or 0))
        if volume > self.config.max_volume_cm3:
            return False, f"Volume too high: {volume}cm3"

        # Price check
        wholesale = float(product.get('wholesalePrice', 0) or 0)
        if wholesale < self.config.min_price_eur or wholesale > self.config.max_price_eur:
            self.stats['price_error'] += 1
            return False, f"Price out of range: {wholesale}"

        self.stats['valid'] += 1
        return True, "Valid"

    def generate_row(self, product: Dict, info: Dict, images: List[str], stock: int,
                     category_mapping: Tuple, parent_sku: str = None,
                     is_parent: bool = False) -> Dict:
        """Generate a single Amazon feed row"""

        template_num, feed_product_type, item_type = category_mapping

        sku = product.get('sku', '')
        ean = str(product.get('ean13', ''))
        name = info.get('name', '') if info else ''
        description = info.get('description', '') if info else ''

        # Extract brand from name or use default
        brand = self.config.default_brand
        if name:
            # Try to extract brand from beginning of name
            parts = name.split(' ')
            if len(parts) > 1 and len(parts[0]) > 2:
                potential_brand = parts[0]
                # Check if it looks like a brand (capitalized, no numbers)
                if potential_brand[0].isupper() and not any(c.isdigit() for c in potential_brand):
                    brand = potential_brand

        # Apply Black Friday prefix to title if enabled
        display_name = name
        if self.config.enable_black_friday:
            display_name = self.config.black_friday_prefix + name

        # Get wholesale price for market-specific calculations below
        wholesale = float(product.get('wholesalePrice', 0) or 0)

        # Get dimensions (round to 2 decimal places)
        height = product.get('height', '')
        if height:
            height = round(float(height), 2)
        width = product.get('width', '')
        if width:
            width = round(float(width), 2)
        depth = product.get('depth', '')  # Used as length
        if depth:
            depth = round(float(depth), 2)
        weight = product.get('weight', '')
        if weight:
            weight = round(float(weight), 2)  # Amazon requires max 2 decimal places

        # Safe stock
        safe_stock = StockCalculator.calculate_safe_quantity(stock)

        # Bullet points
        bullets = TextProcessor.extract_bullet_points(description, 5)

        # Clean description
        clean_description = TextProcessor.truncate(TextProcessor.strip_html(description), 2000)

        # Parent/child relationship
        parent_child = ""
        relationship_type = ""
        variation_theme = ""
        if is_parent:
            parent_child = "Parent"
            self.stats['parents'] += 1
        elif parent_sku:
            parent_child = "Child"
            relationship_type = "Variation"
            variation_theme = "Color"  # Default theme
            self.stats['children'] += 1

        # Build row dictionary (common fields for both templates)
        row = {
            'feed_product_type': feed_product_type,
            'item_sku': sku,
            'brand_name': brand,
            'item_name': TextProcessor.truncate(display_name, 200),
            'product_description': clean_description,
            'manufacturer': brand,
            'external_product_id': ean,
            'external_product_id_type': 'EAN',
            'part_number': sku,
            'item_type': item_type,
            'condition_type': 'New',

            # Images
            'main_image_url': images[0] if len(images) > 0 else '',
            'other_image_url1': images[1] if len(images) > 1 else '',
            'other_image_url2': images[2] if len(images) > 2 else '',
            'other_image_url3': images[3] if len(images) > 3 else '',
            'other_image_url4': images[4] if len(images) > 4 else '',
            'other_image_url5': images[5] if len(images) > 5 else '',
            'other_image_url6': images[6] if len(images) > 6 else '',
            'other_image_url7': images[7] if len(images) > 7 else '',

            # Variations
            'parent_child': parent_child,
            'parent_sku': parent_sku or '',
            'relationship_type': relationship_type,
            'variation_theme': variation_theme,

            # Bullet points
            'bullet_point1': bullets[0],
            'bullet_point2': bullets[1],
            'bullet_point3': bullets[2],
            'bullet_point4': bullets[3],
            'bullet_point5': bullets[4],

            # Dimensions
            'item_height': height,
            'item_height_unit_of_measure': 'CM' if height else '',
            'item_length': depth,
            'item_length_unit_of_measure': 'CM' if depth else '',
            'item_width': width,
            'item_width_unit_of_measure': 'CM' if width else '',
            'item_weight': weight,
            'item_weight_unit_of_measure': 'KG' if weight else '',

            # Fulfillment (MFN)
            'fulfillment_availability#1.fulfillment_channel_code': 'DEFAULT',
            'fulfillment_availability#1.quantity': str(safe_stock),
            'fulfillment_availability#1.lead_time_to_ship_max_days': str(self.config.lead_time_days),

            # Package
            'item_package_quantity': '1',

            # Country of origin (default)
            'country_of_origin': 'CN',
        }

        # Add prices for ALL marketplaces (Amazon NA template expects all three)
        markets = MarketConfig.get_all()
        for _, mkt in markets.items():
            # Calculate price for this market
            price_with_vat = wholesale * (1 + self.config.vat)
            price_with_margin = price_with_vat * (1 + self.config.margin)
            price_eur = price_with_margin + self.config.base_price

            if mkt.vat_rate > 0:
                price_eur = price_eur * (1 + mkt.vat_rate)

            if self.config.enable_black_friday and self.config.black_friday_discount > 0:
                price_eur = price_eur * (1 - self.config.black_friday_discount)

            market_price = round(price_eur * mkt.exchange_rate, 2)

            price_field = f'purchasable_offer[marketplace_id={mkt.marketplace_id}]#1.our_price#1.schedule#1.value_with_tax'
            row[price_field] = str(market_price)

        return row


# ------------------------- Feed Writer -------------------------

class AmazonFeedWriter:
    """Write Amazon feed files"""

    def __init__(self, template_columns: List[Dict]):
        self.columns = template_columns
        self.field_names = [col['field'] for col in template_columns]
        # Build lookup for display names and metadata
        self.col_lookup = {col['field']: col for col in template_columns}

    def write_feed(self, rows: List[Dict], output_path: str):
        """Write tab-delimited text file for Amazon upload

        Amazon requires 3 header rows:
        - Row 1: Template metadata (TemplateType, Version, TemplateSignature, etc.)
        - Row 2: Display names (human-readable column names)
        - Row 3: Field names (API field names)
        - Row 4+: Product data
        """

        # Find columns that have at least one non-empty value
        non_empty_cols = []
        for col in self.columns:
            field = col['field']
            has_value = any(str(row.get(field, '')).strip() for row in rows)
            if has_value:
                non_empty_cols.append(col)

        with open(output_path, 'w', encoding='utf-8') as f:
            # Row 1: Metadata row (TemplateType, Version, TemplateSignature in first 3 columns)
            meta_values = [col.get('meta', '') for col in non_empty_cols]
            f.write('\t'.join(meta_values) + '\n')

            # Row 2: Display names (human-readable)
            display_values = [col.get('display', '') for col in non_empty_cols]
            f.write('\t'.join(display_values) + '\n')

            # Row 3: Field names (API field names)
            field_values = [col.get('field', '') for col in non_empty_cols]
            f.write('\t'.join(field_values) + '\n')

            # Data rows (Row 4+)
            for row in rows:
                values = [str(row.get(col['field'], '')) for col in non_empty_cols]
                f.write('\t'.join(values) + '\n')

        print(f"  Written {len(rows)} rows, {len(non_empty_cols)} columns (dropped {len(self.columns) - len(non_empty_cols)} empty) to {output_path}")


# ------------------------- Main Generator -------------------------

class AmazonNAFeedGenerator:
    """Main orchestrator for Amazon NA feed generation"""

    def __init__(self, api_key: str):
        self.api = BigBuyAPI(api_key)
        self.config = Config()
        self.markets = MarketConfig.get_all()

        # Load template column definitions
        self.template1_cols = self._load_template_columns('amazon_template1_columns.json')
        self.template2_cols = self._load_template_columns('amazon_template2_columns.json')

    def _load_template_columns(self, filename: str) -> List[Dict]:
        """Load template column definitions from JSON"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using minimal columns.")
            return []

    def get_category_mapping(self, bigbuy_category: int) -> Tuple:
        """Get Amazon mapping for BigBuy category"""
        return CATEGORY_MAPPING.get(bigbuy_category, DEFAULT_MAPPING)

    def process_category(self, category_id: int, language: str) -> Tuple[List[Dict], List[Dict]]:
        """Process a single BigBuy category and return rows for both templates"""

        print(f"\nProcessing category {category_id}...")

        # Get category mapping
        template_num, feed_product_type, item_type = self.get_category_mapping(category_id)
        category_mapping = (template_num, feed_product_type, item_type)

        # Fetch data from BigBuy
        data = self.api.get_category_data(category_id, language)

        if not data['products']:
            print(f"  No products found for category {category_id}")
            return [], []

        # Build lookup maps
        product_stock, var_stock = DataAggregator.build_stock_map(
            data['stock'], data['var_stock'], self.config.max_handling_days
        )
        info_map = DataAggregator.build_info_map(data['info'])
        image_map = DataAggregator.build_image_map(data['images'])
        variation_map = DataAggregator.build_variation_map(data['variations'])

        template1_rows = []
        template2_rows = []

        # Create generators for each market (we'll use the first one for validation)
        # The actual market-specific pricing will be applied when generating final feeds
        generator = AmazonFeedGenerator(self.config, list(self.markets.values())[0], template_num)

        for product in data['products']:
            product_id = product.get('id')
            sku = product.get('sku')

            if not sku:
                continue

            info = info_map.get(sku, {})
            images = image_map.get(product_id, [])
            stock = product_stock.get(sku, 0)
            variants = variation_map.get(product_id, [])

            # Check if this product has variants
            has_variants = len(variants) > 0

            if has_variants:
                # Validate at least one variant
                valid_variants = []
                for var in variants:
                    var_sku = var.get('sku')
                    var_stock_qty = var_stock.get(var_sku, 0)
                    var_info = info_map.get(var_sku, info)  # Use parent info as fallback

                    # Use parent product data merged with variant data
                    var_product = {**product, **var}
                    var_product['sku'] = var_sku
                    if var.get('ean13'):
                        var_product['ean13'] = var.get('ean13')

                    is_valid, _ = generator.validate_product(var_product, var_info, var_stock_qty)
                    if is_valid:
                        valid_variants.append((var_product, var_info, var_stock_qty))

                if valid_variants:
                    # Create parent row (stock = 0 for parent)
                    parent_row = generator.generate_row(
                        product, info, images, 0, category_mapping,
                        parent_sku=None, is_parent=True
                    )
                    parent_row['_template'] = template_num

                    if template_num == 1:
                        template1_rows.append(parent_row)
                    else:
                        template2_rows.append(parent_row)

                    # Create child rows
                    for var_product, var_info, var_stock_qty in valid_variants:
                        child_row = generator.generate_row(
                            var_product, var_info, images, var_stock_qty,
                            category_mapping, parent_sku=sku, is_parent=False
                        )
                        child_row['_template'] = template_num

                        if template_num == 1:
                            template1_rows.append(child_row)
                        else:
                            template2_rows.append(child_row)
            else:
                # Standalone product
                is_valid, reason = generator.validate_product(product, info, stock)
                if is_valid:
                    row = generator.generate_row(
                        product, info, images, stock, category_mapping
                    )
                    row['_template'] = template_num

                    if template_num == 1:
                        template1_rows.append(row)
                    else:
                        template2_rows.append(row)

        print(f"  Template 1 rows: {len(template1_rows)}, Template 2 rows: {len(template2_rows)}")
        print(f"  Stats: {generator.stats}")

        return template1_rows, template2_rows

    def generate_feeds(self, categories: List[int] = None):
        """Generate Amazon feeds - one per template with all marketplace prices included"""

        print("=" * 60)
        print("Amazon NA Feed Generator")
        print("=" * 60)

        # Default categories if none specified
        if categories is None:
            categories = list(CATEGORY_MAPPING.keys())

        # Collect all rows
        all_template1_rows = []
        all_template2_rows = []

        # Process categories - use English (Amazon NA template has all 3 marketplaces)
        print("\nFetching English product data...")
        for cat_id in categories:
            t1_rows, t2_rows = self.process_category(cat_id, 'en')
            all_template1_rows.extend(t1_rows)
            all_template2_rows.extend(t2_rows)

        print(f"\nTotal Template 1 rows: {len(all_template1_rows)}")
        print(f"Total Template 2 rows: {len(all_template2_rows)}")

        # Apply product limit if needed
        max_products = self.config.max_products
        if all_template1_rows and len(all_template1_rows) > max_products:
            print(f"Limiting Template 1 from {len(all_template1_rows)} to {max_products} products (random)")
            all_template1_rows = random.sample(all_template1_rows, max_products)
        if all_template2_rows and len(all_template2_rows) > max_products:
            print(f"Limiting Template 2 from {len(all_template2_rows)} to {max_products} products (random)")
            all_template2_rows = random.sample(all_template2_rows, max_products)

        # Generate timestamp for output files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Create writers and write feeds
        # Single file per template - prices for US, CA, MX are all included
        if all_template1_rows and self.template1_cols:
            writer1 = AmazonFeedWriter(self.template1_cols)
            output_file = f"amazon_feed_t1_{timestamp}.txt"
            writer1.write_feed(all_template1_rows, output_file)
            print(f"\nTemplate 1 feed: {output_file}")

        if all_template2_rows and self.template2_cols:
            writer2 = AmazonFeedWriter(self.template2_cols)
            output_file = f"amazon_feed_t2_{timestamp}.txt"
            writer2.write_feed(all_template2_rows, output_file)
            print(f"Template 2 feed: {output_file}")

        print("\n" + "=" * 60)
        print("Feed generation complete!")
        print("=" * 60)


# ------------------------- Main Entry Point -------------------------

def main():
    """Main entry point"""

    # Get API key from environment
    api_key = os.environ.get('BIGBUY_API_KEY')
    if not api_key:
        print("Error: BIGBUY_API_KEY environment variable not set")
        print("Set it with: set BIGBUY_API_KEY=your_key_here")
        return

    # Create generator
    generator = AmazonNAFeedGenerator(api_key)

    # Generate feeds for ALL mapped categories
    # Pass None to use all categories from CATEGORY_MAPPING
    generator.generate_feeds(None)


if __name__ == "__main__":
    main()

# $env:BIGBUY_API_KEY="YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"
# python amazon_feed_generator.py