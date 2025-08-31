import requests
import json
import csv
import os
import random
from datetime import datetime
import time

class BigBuyAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str):
        """Make API request with cache busting"""
        separator = '&' if '?' in endpoint else '?'
        cache_buster = f"{separator}t={int(time.time())}"
        url = f"{self.base_url}{endpoint}{cache_buster}"
        
        try:
            response = requests.get(url, headers=self.headers)
            print(f"Request: {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 401:
                print("❌ Authentication Error")
                return None
            elif response.status_code == 400:
                print(f"❌ Bad Request: {response.text}")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def get_all_taxonomies(self):
        """Get ALL product categories from BigBuy"""
        result = self._make_request("/rest/catalog/taxonomies.json")
        if result:
            filtered = []
            inappropriate_keywords = ['erotic', 'erotico', 'adult', 'sex', 'xxx', 'porn', 'lingerie']
            
            for taxonomy in result:
                name = taxonomy.get('name', '').lower()
                if not any(keyword in name for keyword in inappropriate_keywords):
                    filtered.append(taxonomy)
                else:
                    print(f"🚫 Filtered: {taxonomy['name']}")
            
            print(f"📊 Found {len(filtered)} total categories from BigBuy")
            return filtered
        return []

    def get_products(self, taxonomy_id):
        """Get ALL products for category"""
        return self._make_request(f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}")

    def get_product_variations(self, taxonomy_id):
        """Get product variations for category"""
        return self._make_request(f"/rest/catalog/productsvariations.json?parentTaxonomy={taxonomy_id}")

    def get_product_stock(self, taxonomy_id):
        """Get stock data by taxonomy"""
        return self._make_request(f"/rest/catalog/productsstockbyhandlingdays.json?parentTaxonomy={taxonomy_id}")

    def get_variations_stock(self, taxonomy_id):
        """Get variation stock data"""
        return self._make_request(f"/rest/catalog/productsvariationsstockbyhandlingdays.json?parentTaxonomy={taxonomy_id}")

    def get_product_info(self, taxonomy_id, language="it"):
        """Get product descriptions in specified language"""
        return self._make_request(f"/rest/catalog/productsinformation.json?isoCode={language}&parentTaxonomy={taxonomy_id}")

    def get_product_images(self, taxonomy_id):
        """Get product images"""
        return self._make_request(f"/rest/catalog/productsimages.json?parentTaxonomy={taxonomy_id}")

def safe_float(value, default=0.0):
    try:
        return float(value) if value else default
    except:
        return default

def safe_str(value, default=""):
    try:
        return str(value) if value else default
    except:
        return default

def safe_int(value, default=0):
    try:
        return int(value) if value else default
    except:
        return default

def calculate_real_quantity(bigbuy_stock):
    """Calculate real quantity - MINIMUM 1 UNIT REQUIRED"""
    stock = safe_int(bigbuy_stock, 0)
    
    if stock <= 0:
        return 0
    elif stock == 1:
        return 1
    elif stock <= 5:
        return min(stock, stock - 1) if stock > 1 else 1
    elif stock <= 10:
        return min(stock - 1, 8)
    elif stock <= 20:
        return min(stock - 2, 15)
    else:
        return min(50, int(stock * 0.9))

def validate_sellable_item(sku, price, stock_quantity, ean13=""):
    """Validate if item (product or variation) can be sold"""
    
    if not sku:
        return False, "Missing SKU"
    
    if safe_float(price, 0) <= 0:
        return False, "Invalid price"
    
    if stock_quantity < 1:
        return False, "Insufficient stock"
    
    return True, stock_quantity

def map_to_manomano_category_numeric(taxonomy_name, taxonomy_id):
    """Map BigBuy taxonomy to ManoMano numeric category"""
    name_lower = taxonomy_name.lower() if taxonomy_name else ""
    
    if any(word in name_lower for word in ['aspirapolvere', 'vacuum', 'cleaner']):
        return 20521
    elif any(word in name_lower for word in ['attrezzi', 'tool', 'drill', 'trapano']):
        return 22110
    elif any(word in name_lower for word in ['stendibiancheria', 'clothesline', 'laundry']):
        return 20221
    elif any(word in name_lower for word in ['giardino', 'garden', 'outdoor']):
        return 20280
    elif any(word in name_lower for word in ['cucina', 'kitchen', 'casa', 'home']):
        return 20277
    elif any(word in name_lower for word in ['bricolaje', 'bricolage', 'diy']):
        return 22110
    elif any(word in name_lower for word in ['illumina', 'light', 'lamp']):
        return 20280
    elif any(word in name_lower for word in ['bagno', 'bathroom']):
        return 20277
    else:
        return taxonomy_id if taxonomy_id else 22110

def create_csv_row_from_product(product, info_dict, image_dict, taxonomy_name, margin, vat, base_price):
    """Create CSV row from main product"""
    sku = product['sku']
    product_id = product['id']
    info = info_dict.get(sku, {})
    images = image_dict.get(product_id, {})
    
    # Calculate price
    wholesale_eur = safe_float(product.get('wholesalePrice', 0))
    price_eur = (wholesale_eur * (1 + vat) * (1 + margin)) + base_price
    
    # Get dimensions
    width = safe_float(product.get('width', 0))
    height = safe_float(product.get('height', 0))
    depth = safe_float(product.get('depth', 0))
    weight = safe_float(product.get('weight', 0))
    
    return {
        'sku': str(sku),
        'ean': safe_str(product.get('ean13')),
        'sku_manufacturer': str(sku),
        'brand': 'Autres',
        'mm_category': map_to_manomano_category_numeric(taxonomy_name, product.get('taxonomy')),
        'title': safe_str(info.get('name', 'Product'))[:100],
        'description': safe_str(info.get('description', ''))[:2000],
        'image_1': images.get('image1', ''),
        'image_2': images.get('image2', ''),
        'image_3': images.get('image3', ''),
        'image_4': images.get('image4', ''),
        'image_5': images.get('image5', ''),
        'product_price_vat_inc': round(price_eur, 2),
        'min_quantity': "1",
        'increment': "1",
        'quantity': 0,  # Will be set based on stock
        'use_grid': "1",
        'carrier_grid_1': "Generale",
        'shipping_time_carrier_grid_1': "5#7",
        'width': round(width, 2),
        'height': round(height, 2),
        'length': round(depth, 2),
        'weight': round(weight, 2),
        'volume': round(depth * width * height, 2),
        'DisplayWeight': round(weight, 2),
        'Parent_SKU': str(sku),
        'parent_title': safe_str(info.get('name', 'Product'))
    }

def create_csv_row_from_variation(variation, parent_product, info_dict, image_dict, taxonomy_name, margin, vat, base_price):
    """Create CSV row from product variation"""
    variation_sku = variation['sku']
    product_id = variation.get('product')  # Parent product ID
    
    # Use parent product info but variation-specific data
    parent_info = info_dict.get(parent_product['sku'], {}) if parent_product else {}
    images = image_dict.get(product_id, {})
    
    # Use variation price (variations can have different prices!)
    wholesale_eur = safe_float(variation.get('wholesalePrice', 0))
    price_eur = (wholesale_eur * (1 + vat) * (1 + margin)) + base_price
    
    # Use variation dimensions (can be different from parent)
    width = safe_float(variation.get('width', 0)) or safe_float(parent_product.get('width', 0) if parent_product else 0)
    height = safe_float(variation.get('height', 0)) or safe_float(parent_product.get('height', 0) if parent_product else 0)
    depth = safe_float(variation.get('depth', 0)) or safe_float(parent_product.get('depth', 0) if parent_product else 0)
    
    # Calculate weight (variation might have extra weight)
    base_weight = safe_float(parent_product.get('weight', 0) if parent_product else 0)
    extra_weight = safe_float(variation.get('extraWeight', 0))
    total_weight = base_weight + extra_weight
    
    # Create title that includes variation info
    base_title = safe_str(parent_info.get('name', 'Product Variation'))
    variation_title = f"{base_title} - {variation_sku}"  # Include variation SKU for differentiation
    
    return {
        'sku': str(variation_sku),  # Use variation SKU
        'ean': safe_str(variation.get('ean13')),  # Use variation EAN
        'sku_manufacturer': str(variation_sku),
        'brand': 'Autres',
        'mm_category': map_to_manomano_category_numeric(taxonomy_name, parent_product.get('taxonomy') if parent_product else None),
        'title': variation_title[:100],
        'description': safe_str(parent_info.get('description', ''))[:2000],
        'image_1': images.get('image1', ''),
        'image_2': images.get('image2', ''),
        'image_3': images.get('image3', ''),
        'image_4': images.get('image4', ''),
        'image_5': images.get('image5', ''),
        'product_price_vat_inc': round(price_eur, 2),  # Use variation price
        'min_quantity': "1",
        'increment': "1",
        'quantity': 0,  # Will be set based on stock
        'use_grid': "1",
        'carrier_grid_1': "Generale",
        'shipping_time_carrier_grid_1': "5#7",
        'width': round(width, 2),
        'height': round(height, 2),
        'length': round(depth, 2),
        'weight': round(total_weight, 2),
        'volume': round(depth * width * height, 2),
        'DisplayWeight': round(total_weight, 2),
        'Parent_SKU': str(parent_product['sku']) if parent_product else str(variation_sku),
        'parent_title': safe_str(parent_info.get('name', 'Product'))
    }

def main():
    """Main function - EXTRACT ALL PRODUCTS AND ALL VARIATIONS"""
    print("🚀 STARTING MANOMANO FEED - WITH PRODUCT VARIATIONS")
    print("=" * 80)
    print("🔧 MAJOR IMPROVEMENT:")
    print("   ✅ Process MAIN PRODUCTS as separate CSV rows")
    print("   ✅ Process EACH VARIATION as separate CSV rows")
    print("   ✅ Each variation = separate sellable product with own SKU/EAN/price")
    print("   ✅ This should MULTIPLY your product count by 2-5x!")
    print("   ✅ Minimum 1 unit stock requirement")
    print("   ✅ ALL taxonomies, no artificial limits")
    print("=" * 80)
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found in BIGBUY_API_KEY environment variable")
        return
    
    print(f"🔑 API key found (length: {len(api_key)})")
    
    api = BigBuyAPI(api_key)
    
    # Configuration
    margin = 0.40
    vat = 0.22
    base_price = 0.50
    min_price_eur = 0.50
    max_price_eur = 5000.0
    max_content_volume = 10000000000
    max_weight = 1000.0
    
    print(f"💰 Price range: €{min_price_eur} - €{max_price_eur}")
    print(f"🎯 Target: ALL PRODUCTS + ALL VARIATIONS")
    
    # Get ALL taxonomies
    taxonomies = api.get_all_taxonomies()
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories")
    
    # Collect all data
    all_products = []
    all_variations_list = []  # Store as flat list with parent info
    all_info = []
    all_images = []
    all_stock_data = {'products': {}, 'variations': {}}
    
    print("\n🔄 Collecting ALL Products AND Variations...")
    
    for i, taxonomy in enumerate(taxonomies):
        tax_id = taxonomy['id']
        tax_name = taxonomy['name']
        
        print(f"📦 {i+1}/{len(taxonomies)}: {tax_name}")
        
        # Get ALL products (no limits)
        products = api.get_products(tax_id)
        if products:
            print(f"   📊 Found {len(products)} main products")
            all_products.extend(products)
        
        # Get ALL variations and store with parent reference
        variations = api.get_product_variations(tax_id)
        if variations:
            print(f"   📊 Found {len(variations)} variations")
            for variation in variations:
                # Add taxonomy info to variation for later processing
                variation['taxonomy'] = tax_id
                variation['taxonomy_name'] = tax_name
                all_variations_list.append(variation)
        
        # Get stock data
        product_stock = api.get_product_stock(tax_id)
        if product_stock:
            stock_count = 0
            for stock_item in product_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['products'][sku] = total_quantity
                    stock_count += 1
            print(f"   📊 Stock for {stock_count} main products")
        
        # Get variation stock
        variation_stock = api.get_variations_stock(tax_id)
        if variation_stock:
            var_stock_count = 0
            for stock_item in variation_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['variations'][sku] = total_quantity
                    var_stock_count += 1
            print(f"   📊 Stock for {var_stock_count} variations")
        
        # Get product info
        info = api.get_product_info(tax_id, 'it')
        if info:
            all_info.extend(info)
        
        # Get images  
        images = api.get_product_images(tax_id)
        if images:
            all_images.extend(images)
        
        time.sleep(0.5)
    
    print(f"\n✅ EXTRACTION COMPLETE:")
    print(f"   📦 Main products: {len(all_products):,}")
    print(f"   🔄 Variations: {len(all_variations_list):,}")
    print(f"   📊 Product stock entries: {len(all_stock_data['products']):,}")
    print(f"   📊 Variation stock entries: {len(all_stock_data['variations']):,}")
    print(f"   📝 Descriptions: {len(all_info):,}")
    print(f"   🖼️ Images: {len(all_images):,}")
    
    # Create lookup dictionaries
    info_dict = {item['sku']: item for item in all_info}
    image_dict = {}
    product_dict = {product['id']: product for product in all_products}
    
    for img_set in all_images:
        product_id = img_set['id']
        images = img_set.get('images', [])
        if images:
            image_dict[product_id] = {
                'image1': images[0].get('url', '') if len(images) > 0 else '',
                'image2': images[1].get('url', '') if len(images) > 1 else '',
                'image3': images[2].get('url', '') if len(images) > 2 else '',
                'image4': images[3].get('url', '') if len(images) > 3 else '',
                'image5': images[4].get('url', '') if len(images) > 4 else ''
            }
    
    # Create taxonomy lookup
    taxonomy_dict = {tax['id']: tax['name'] for tax in taxonomies}
    
    print("\n🔍 Processing ALL Products AND Variations as Separate Items...")
    
    csv_data = []
    validation_stats = {
        'main_products_processed': 0,
        'variations_processed': 0,
        'main_products_valid': 0,
        'variations_valid': 0,
        'no_stock': 0,
        'invalid_price': 0,
        'missing_sku': 0
    }
    
    # Process MAIN PRODUCTS
    print("📦 Processing main products...")
    for product in all_products:
        validation_stats['main_products_processed'] += 1
        
        sku = product.get('sku')
        if not sku:
            validation_stats['missing_sku'] += 1
            continue
            
        # Get stock for main product
        stock_quantity = all_stock_data['products'].get(sku, 0)
        
        # Validate this main product
        is_valid, stock_or_reason = validate_sellable_item(
            sku, product.get('wholesalePrice', 0), stock_quantity, product.get('ean13')
        )
        
        if not is_valid:
            if "stock" in stock_or_reason.lower():
                validation_stats['no_stock'] += 1
            elif "price" in stock_or_reason.lower():
                validation_stats['invalid_price'] += 1
            continue
        
        # Calculate real quantity
        real_quantity = calculate_real_quantity(stock_quantity)
        if real_quantity < 1:
            validation_stats['no_stock'] += 1
            continue
            
        # Create CSV row for main product
        taxonomy_name = taxonomy_dict.get(product.get('taxonomy'), '')
        row = create_csv_row_from_product(product, info_dict, image_dict, taxonomy_name, margin, vat, base_price)
        row['quantity'] = real_quantity
        
        # Apply price filters
        if row['product_price_vat_inc'] < min_price_eur or row['product_price_vat_inc'] > max_price_eur:
            continue
        
        # Apply physical filters
        if row['weight'] > max_weight or row['volume'] > max_content_volume:
            continue
            
        csv_data.append(row)
        validation_stats['main_products_valid'] += 1
        
        if validation_stats['main_products_processed'] % 5000 == 0:
            print(f"   📊 Main products: {validation_stats['main_products_processed']:,} processed, {validation_stats['main_products_valid']:,} valid")
    
    # Process ALL VARIATIONS as separate products
    print("🔄 Processing product variations as separate products...")
    for variation in all_variations_list:
        validation_stats['variations_processed'] += 1
        
        variation_sku = variation.get('sku')
        if not variation_sku:
            validation_stats['missing_sku'] += 1
            continue
        
        # Get stock for this variation
        stock_quantity = all_stock_data['variations'].get(variation_sku, 0)
        
        # Validate this variation
        is_valid, stock_or_reason = validate_sellable_item(
            variation_sku, variation.get('wholesalePrice', 0), stock_quantity, variation.get('ean13')
        )
        
        if not is_valid:
            if "stock" in stock_or_reason.lower():
                validation_stats['no_stock'] += 1
            elif "price" in stock_or_reason.lower():
                validation_stats['invalid_price'] += 1
            continue
        
        # Calculate real quantity
        real_quantity = calculate_real_quantity(stock_quantity)
        if real_quantity < 1:
            validation_stats['no_stock'] += 1
            continue
        
        # Get parent product for additional info
        parent_product = product_dict.get(variation.get('product'))
        taxonomy_name = variation.get('taxonomy_name', '')
        
        # Create CSV row for variation
        row = create_csv_row_from_variation(variation, parent_product, info_dict, image_dict, taxonomy_name, margin, vat, base_price)
        row['quantity'] = real_quantity
        
        # Apply price filters
        if row['product_price_vat_inc'] < min_price_eur or row['product_price_vat_inc'] > max_price_eur:
            continue
        
        # Apply physical filters
        if row['weight'] > max_weight or row['volume'] > max_content_volume:
            continue
            
        csv_data.append(row)
        validation_stats['variations_valid'] += 1
        
        if validation_stats['variations_processed'] % 2000 == 0:
            print(f"   🔄 Variations: {validation_stats['variations_processed']:,} processed, {validation_stats['variations_valid']:,} valid")
    
    # Print detailed statistics
    print(f"\n🔍 DETAILED VALIDATION STATISTICS:")
    print(f"   📦 Main products processed: {validation_stats['main_products_processed']:,}")
    print(f"   📦 Main products valid: {validation_stats['main_products_valid']:,}")
    print(f"   🔄 Variations processed: {validation_stats['variations_processed']:,}")
    print(f"   🔄 Variations valid: {validation_stats['variations_valid']:,}")
    print(f"   📊 Total items created: {len(csv_data):,}")
    print(f"   ❌ No stock: {validation_stats['no_stock']:,}")
    print(f"   ❌ Invalid price: {validation_stats['invalid_price']:,}")
    print(f"   ❌ Missing SKU: {validation_stats['missing_sku']:,}")
    
    total_processed = validation_stats['main_products_processed'] + validation_stats['variations_processed']
    total_valid = validation_stats['main_products_valid'] + validation_stats['variations_valid']
    
    if total_processed > 0:
        success_rate = 100 * total_valid / total_processed
        print(f"   📈 Overall success rate: {success_rate:.1f}%")
    
    # Remove duplicates by EAN (but keep different SKUs)
    seen_skus = set()
    unique_data = []
    
    for row in csv_data:
        sku = row['sku']
        if sku not in seen_skus:
            seen_skus.add(sku)
            unique_data.append(row)
    
    print(f"\n✅ Final result: {len(unique_data):,} unique products (main + variations)")
    print(f"   📦 This includes both main products AND their variations")
    print(f"   🎯 Should be MUCH higher than before!")
    
    if not unique_data:
        print("❌ No valid products found!")
        return
    
    # Create output files
    print("\n📁 Creating ManoMano Output Files...")
    
    filename = 'manomano_with_variations.csv'
    html_filename = 'manomano_variations_index.html'
    info_filename = 'manomano_variations_info.json'
    
    # Create CSV
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
            writer.writeheader()
            writer.writerows(unique_data)
        print(f"✅ Created {filename} with {len(unique_data):,} products")
    except Exception as e:
        print(f"❌ Error creating CSV: {e}")
        return
    
    # Create info file
    try:
        info_data = {
            "last_updated": datetime.now().isoformat(),
            "total_items": len(unique_data),
            "main_products": validation_stats['main_products_valid'],
            "variations": validation_stats['variations_valid'],
            "total_taxonomies": len(taxonomies),
            "validation_stats": validation_stats,
            "includes_variations": True,
            "extraction_method": "COMPLETE_WITH_VARIATIONS",
            "marketplace": "ManoMano",
            "country": "Italy",
            "currency": "EUR",
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}",
            "note": "INCLUDES_ALL_PRODUCT_VARIATIONS_AS_SEPARATE_SELLABLE_ITEMS"
        }
        
        with open(info_filename, 'w') as f:
            json.dump(info_data, f, indent=2)
        print(f"✅ Created {info_filename}")
    except Exception as e:
        print(f"❌ Error creating JSON: {e}")
    
    # Create HTML summary
    try:
        variation_percentage = (validation_stats['variations_valid'] / len(unique_data) * 100) if unique_data else 0
        
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>ManoMano Feed CON VARIAZIONI - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: #ff6b35; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .breakthrough {{ background: #28a745; color: white; padding: 25px; border-radius: 10px; margin: 30px 0; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .variations-box {{ background: #e8f5e8; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 30px 0; }}
        .feed-url code {{ background: #fff; padding: 10px; border-radius: 5px; font-size: 14px; word-break: break-all; display: block; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 30px; background: white; border-radius: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff6b35; color: white; }}
        .price {{ color: #4caf50; font-weight: bold; }}
        .variation {{ background-color: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Feed ManoMano CON VARIAZIONI</h1>
        <p><strong>Pop Pulse Emporium</strong> - Estrazione Completa</p>
        <p>Ultimo Aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
    
    <div class="breakthrough">
        <h2>🎯 BREAKTHROUGH: VARIAZIONI INCLUSE!</h2>
        <p><strong>Ogni variazione di prodotto = Prodotto vendibile separato</strong></p>
        <p>Questo dovrebbe MOLTIPLICARE il numero di prodotti!</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Prodotti Totali</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{validation_stats['main_products_valid']:,}</div>
            <div class="stat-label">Prodotti Principali</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{validation_stats['variations_valid']:,}</div>
            <div class="stat-label">Variazioni</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{len(taxonomies)}</div>
            <div class="stat-label">Categorie BigBuy</div>
        </div>
    </div>
    
    <div class="variations-box">
        <h3>🔄 GESTIONE VARIAZIONI PRODOTTO</h3>
        <p><strong>Come funziona:</strong></p>
        <ul>
            <li>✅ <strong>Prodotto principale:</strong> Es. "T-shirt Blu" (SKU: S1234567)</li>
            <li>✅ <strong>Variazione 1:</strong> "T-shirt Blu - XL" (SKU: S1234568, EAN diverso)</li>
            <li>✅ <strong>Variazione 2:</strong> "T-shirt Blu - L" (SKU: S1234569, EAN diverso)</li>
            <li>✅ <strong>Ogni variazione:</strong> SKU unico, EAN unico, prezzo proprio, stock proprio</li>
            <li>📊 <strong>Risultato:</strong> {validation_stats['variations_valid']:,} variazioni ({variation_percentage:.1f}% del feed)</li>
        </ul>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed ManoMano CON VARIAZIONI:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{filename}</code>
        <p><strong>🎯 MASSIMA COPERTURA: Prodotti principali + Tutte le variazioni</strong></p>
    </div>
    
    <h2>📊 Sample Prodotti e Variazioni (Primi 20)</h2>
    <table>
        <tr>
            <th>Tipo</th>
            <th>SKU</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Parent_SKU</th>
            <th>Prezzo</th>
            <th>Stock</th>
        </tr>"""
        
        # Show mix of main products and variations
        for i, row in enumerate(unique_data[:20]):
            sku = row.get("sku", "")
            parent_sku = row.get("Parent_SKU", "")
            
            # Determine if this is a main product or variation
            is_variation = sku != parent_sku
            item_type = "Variazione" if is_variation else "Principale"
            row_class = "variation" if is_variation else ""
            
            title = safe_str(row.get("title", ""))[:50]
            if len(title) > 47:
                title += "..."
                
            ean = safe_str(row.get("ean", ""))
            price = row.get("product_price_vat_inc", 0)
            quantity = row.get("quantity", 0)
            
            html_content += f"""
        <tr class="{row_class}">
            <td><strong>{item_type}</strong></td>
            <td>{sku}</td>
            <td>{title}</td>
            <td>{ean}</td>
            <td>{parent_sku}</td>
            <td class="price">€{price:.2f}</td>
            <td><strong>{quantity}</strong></td>
        </tr>"""
        
        html_content += f"""
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>📋 Dettagli Estrazione CON VARIAZIONI</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4>📊 Statistiche Prodotti:</h4>
                <ul>
                    <li>Prodotti principali: {validation_stats['main_products_valid']:,}</li>
                    <li>Variazioni: {validation_stats['variations_valid']:,}</li>
                    <li>Totale final: {len(unique_data):,}</li>
                    <li>Success rate: {(100*total_valid/total_processed):.1f}%</li>
                </ul>
            </div>
            <div>
                <h4>🔧 Miglioramenti:</h4>
                <ul>
                    <li>✅ Variazioni = Prodotti separati</li>
                    <li>✅ SKU/EAN/prezzo unici per variazione</li>
                    <li>✅ Stock validation per ogni item</li>
                    <li>✅ Nessun limite artificiale</li>
                </ul>
            </div>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <strong>🎯 RISULTATO ATTESO:</strong> Questo feed dovrebbe avere 2-5x più prodotti rispetto alla versione precedente, 
            perché ogni variazione (taglia, colore, capacità, etc.) è ora un prodotto vendibile separato con il proprio SKU e stock.
        </div>
    </div>
</body>
</html>"""
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Created {html_filename}")
    except Exception as e:
        print(f"❌ Error creating HTML: {e}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("🎉 SUCCESS! MANOMANO FEED WITH VARIATIONS COMPLETE")
    print("=" * 80)
    print(f"📁 Files created:")
    print(f"   📄 CSV: {filename}")
    print(f"   🌐 HTML: {html_filename}")
    print(f"   📋 JSON: {info_filename}")
    
    print(f"\n📊 FINAL BREAKDOWN:")
    print(f"   📦 Main products: {validation_stats['main_products_valid']:,}")
    print(f"   🔄 Variations: {validation_stats['variations_valid']:,}")
    print(f"   📊 Total sellable items: {len(unique_data):,}")
    
    if unique_data:
        prices = [row['product_price_vat_inc'] for row in unique_data]
        quantities = [row['quantity'] for row in unique_data]
        categories = list(set([row['mm_category'] for row in unique_data]))
        
        print(f"💰 Price range: €{min(prices):.2f} - €{max(prices):.2f}")
        print(f"📦 Quantity range: {min(quantities)} - {max(quantities)} units")
        print(f"📂 Categories: {len(categories)} unique mm_category values")
    
    print(f"\n🚀 BREAKTHROUGH ACHIEVED:")
    print(f"   ✅ Each product variation is now a separate sellable item")
    print(f"   ✅ Variations have their own SKU, EAN, price, and stock")
    print(f"   ✅ This should MULTIPLY your product count significantly")
    print(f"   ✅ Much closer to your Excel target of 11,179+ products")
    
    # Comparison guidance
    if len(unique_data) < 5000:
        print(f"\n⚠️  Still low product count ({len(unique_data):,})")
        print(f"   🔍 Possible remaining issues:")
        print(f"     - Most products/variations don't have ≥1 stock")
        print(f"     - API rate limiting causing incomplete extraction")
        print(f"     - BigBuy account restrictions")
    elif len(unique_data) >= 10000:
        print(f"\n🎉 EXCELLENT! {len(unique_data):,} products - Much better!")
        print(f"   📈 Variations strategy working perfectly")
    else:
        print(f"\n👍 GOOD IMPROVEMENT: {len(unique_data):,} products")
        print(f"   📈 Significant increase from variations inclusion")

if __name__ == "__main__":
    main()
