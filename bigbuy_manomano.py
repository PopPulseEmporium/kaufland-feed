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

def calculate_real_quantity(bigbuy_stock, min_required=2):
    """Calculate real quantity with HIGHER quality threshold"""
    stock = safe_int(bigbuy_stock, 0)
    
    # QUALITY FILTER: Require minimum 2 units for reliability
    if stock < min_required:
        return 0
    elif stock <= 5:
        return min(2, stock - 1)
    elif stock <= 10:
        return min(5, stock - 1)
    elif stock <= 20:
        return min(10, stock - 2)
    else:
        return min(50, int(stock * 0.9))

def validate_sellable_item(sku, price, stock_quantity, ean13="", min_stock=2):
    """Validate if item can be sold with QUALITY requirements"""
    
    if not sku:
        return False, "Missing SKU"
    
    if safe_float(price, 0) <= 0:
        return False, "Invalid price"
    
    # QUALITY REQUIREMENT: Minimum 2 units stock
    if stock_quantity < min_stock:
        return False, f"Insufficient stock (need ≥{min_stock}, have: {stock_quantity})"
    
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
    
    # Use variation price
    wholesale_eur = safe_float(variation.get('wholesalePrice', 0))
    price_eur = (wholesale_eur * (1 + vat) * (1 + margin)) + base_price
    
    # Use variation dimensions
    width = safe_float(variation.get('width', 0)) or safe_float(parent_product.get('width', 0) if parent_product else 0)
    height = safe_float(variation.get('height', 0)) or safe_float(parent_product.get('height', 0) if parent_product else 0)
    depth = safe_float(variation.get('depth', 0)) or safe_float(parent_product.get('depth', 0) if parent_product else 0)
    
    # Calculate weight
    base_weight = safe_float(parent_product.get('weight', 0) if parent_product else 0)
    extra_weight = safe_float(variation.get('extraWeight', 0))
    total_weight = base_weight + extra_weight
    
    # Create title that includes variation info
    base_title = safe_str(parent_info.get('name', 'Product Variation'))
    variation_title = f"{base_title} - {variation_sku}"
    
    return {
        'sku': str(variation_sku),
        'ean': safe_str(variation.get('ean13')),
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
        'weight': round(total_weight, 2),
        'volume': round(depth * width * height, 2),
        'DisplayWeight': round(total_weight, 2),
        'Parent_SKU': str(parent_product['sku']) if parent_product else str(variation_sku),
        'parent_title': safe_str(parent_info.get('name', 'Product'))
    }

def main():
    """Main function - OPTIMIZED: Quality + Quantity"""
    print("🚀 MANOMANO FEED - OPTIMIZED FOR QUALITY + QUANTITY")
    print("=" * 80)
    print("🎯 OPTIMIZATION STRATEGY:")
    print("   ✅ Extract ALL products + variations (complete dataset)")
    print("   ✅ Apply QUALITY filters (min 2 units stock)")
    print("   ✅ Random selection for variety")
    print("   ✅ Limit to 75,000 best products")
    print("   ✅ Better stock reliability, manageable feed size")
    print("=" * 80)
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found in BIGBUY_API_KEY environment variable")
        return
    
    print(f"🔑 API key found (length: {len(api_key)})")
    
    api = BigBuyAPI(api_key)
    
    # OPTIMIZED Configuration - Quality + Quantity balance
    margin = 0.40
    vat = 0.22
    base_price = 0.50
    min_price_eur = 0.50
    max_price_eur = 5000.0
    max_content_volume = 10000000000
    max_weight = 1000.0
    
    # QUALITY CONTROLS
    MIN_STOCK_REQUIRED = 2  # Higher quality threshold
    MAX_FINAL_PRODUCTS = 75000  # Manageable feed size
    
    print(f"💰 Price range: €{min_price_eur} - €{max_price_eur}")
    print(f"📦 Minimum stock required: {MIN_STOCK_REQUIRED} units (quality filter)")
    print(f"🎯 Maximum final products: {MAX_FINAL_PRODUCTS:,}")
    print(f"🎲 Random selection: Enabled for variety")
    
    # Set random seed for reproducibility within same day
    current_day = datetime.now().day
    random_seed = current_day * 1000 + datetime.now().hour
    random.seed(random_seed)
    print(f"🎲 Random seed: {random_seed}")
    
    # Get ALL taxonomies
    taxonomies = api.get_all_taxonomies()
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories")
    
    # Collect complete dataset first
    all_products = []
    all_variations_list = []
    all_info = []
    all_images = []
    all_stock_data = {'products': {}, 'variations': {}}
    
    print("\n🔄 PHASE 1: Collecting Complete Dataset...")
    
    for i, taxonomy in enumerate(taxonomies):
        tax_id = taxonomy['id']
        tax_name = taxonomy['name']
        
        print(f"📦 {i+1}/{len(taxonomies)}: {tax_name}")
        
        # Get ALL products and variations (no limits in extraction phase)
        products = api.get_products(tax_id)
        if products:
            all_products.extend(products)
        
        variations = api.get_product_variations(tax_id)
        if variations:
            for variation in variations:
                variation['taxonomy'] = tax_id
                variation['taxonomy_name'] = tax_name
                all_variations_list.append(variation)
        
        # Get stock data
        product_stock = api.get_product_stock(tax_id)
        if product_stock:
            for stock_item in product_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['products'][sku] = total_quantity
        
        variation_stock = api.get_variations_stock(tax_id)
        if variation_stock:
            for stock_item in variation_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['variations'][sku] = total_quantity
        
        # Get info and images
        info = api.get_product_info(tax_id, 'it')
        if info:
            all_info.extend(info)
        
        images = api.get_product_images(tax_id)
        if images:
            all_images.extend(images)
        
        time.sleep(0.5)
        
        # Progress update
        if (i + 1) % 20 == 0:
            print(f"   📈 Progress: {len(all_products):,} products, {len(all_variations_list):,} variations")
    
    print(f"\n✅ COMPLETE DATASET COLLECTED:")
    print(f"   📦 Main products: {len(all_products):,}")
    print(f"   🔄 Variations: {len(all_variations_list):,}")
    print(f"   📊 Product stock entries: {len(all_stock_data['products']):,}")
    print(f"   📊 Variation stock entries: {len(all_stock_data['variations']):,}")
    
    # Create lookup dictionaries
    info_dict = {item['sku']: item for item in all_info}
    image_dict = {}
    product_dict = {product['id']: product for product in all_products}
    taxonomy_dict = {tax['id']: tax['name'] for tax in taxonomies}
    
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
    
    print("\n🔍 PHASE 2: Quality Filtering and Processing...")
    
    # Collect all valid items in one list for random selection
    valid_items = []
    validation_stats = {
        'main_products_processed': 0,
        'variations_processed': 0,
        'main_products_valid': 0,
        'variations_valid': 0,
        'insufficient_stock': 0,
        'invalid_price': 0,
        'missing_sku': 0,
        'filtered_by_constraints': 0
    }
    
    # Process main products
    print("📦 Processing main products with quality filters...")
    for product in all_products:
        validation_stats['main_products_processed'] += 1
        
        sku = product.get('sku')
        if not sku:
            validation_stats['missing_sku'] += 1
            continue
            
        stock_quantity = all_stock_data['products'].get(sku, 0)
        
        # QUALITY VALIDATION with higher threshold
        is_valid, stock_or_reason = validate_sellable_item(
            sku, product.get('wholesalePrice', 0), stock_quantity, 
            product.get('ean13'), MIN_STOCK_REQUIRED
        )
        
        if not is_valid:
            if "stock" in stock_or_reason.lower():
                validation_stats['insufficient_stock'] += 1
            elif "price" in stock_or_reason.lower():
                validation_stats['invalid_price'] += 1
            continue
        
        real_quantity = calculate_real_quantity(stock_quantity, MIN_STOCK_REQUIRED)
        if real_quantity < MIN_STOCK_REQUIRED:
            validation_stats['insufficient_stock'] += 1
            continue
            
        # Create potential CSV row
        taxonomy_name = taxonomy_dict.get(product.get('taxonomy'), '')
        row = create_csv_row_from_product(product, info_dict, image_dict, taxonomy_name, margin, vat, base_price)
        row['quantity'] = real_quantity
        
        # Apply additional quality filters
        if (row['product_price_vat_inc'] < min_price_eur or 
            row['product_price_vat_inc'] > max_price_eur or
            row['weight'] > max_weight or 
            row['volume'] > max_content_volume):
            validation_stats['filtered_by_constraints'] += 1
            continue
            
        valid_items.append(('main', row))
        validation_stats['main_products_valid'] += 1
    
    # Process variations
    print("🔄 Processing variations with quality filters...")
    for variation in all_variations_list:
        validation_stats['variations_processed'] += 1
        
        variation_sku = variation.get('sku')
        if not variation_sku:
            validation_stats['missing_sku'] += 1
            continue
        
        stock_quantity = all_stock_data['variations'].get(variation_sku, 0)
        
        # QUALITY VALIDATION with higher threshold
        is_valid, stock_or_reason = validate_sellable_item(
            variation_sku, variation.get('wholesalePrice', 0), stock_quantity,
            variation.get('ean13'), MIN_STOCK_REQUIRED
        )
        
        if not is_valid:
            if "stock" in stock_or_reason.lower():
                validation_stats['insufficient_stock'] += 1
            elif "price" in stock_or_reason.lower():
                validation_stats['invalid_price'] += 1
            continue
        
        real_quantity = calculate_real_quantity(stock_quantity, MIN_STOCK_REQUIRED)
        if real_quantity < MIN_STOCK_REQUIRED:
            validation_stats['insufficient_stock'] += 1
            continue
        
        # Create potential CSV row
        parent_product = product_dict.get(variation.get('product'))
        taxonomy_name = variation.get('taxonomy_name', '')
        row = create_csv_row_from_variation(variation, parent_product, info_dict, image_dict, taxonomy_name, margin, vat, base_price)
        row['quantity'] = real_quantity
        
        # Apply additional quality filters
        if (row['product_price_vat_inc'] < min_price_eur or 
            row['product_price_vat_inc'] > max_price_eur or
            row['weight'] > max_weight or 
            row['volume'] > max_content_volume):
            validation_stats['filtered_by_constraints'] += 1
            continue
            
        valid_items.append(('variation', row))
        validation_stats['variations_valid'] += 1
    
    print(f"\n📊 QUALITY FILTERING RESULTS:")
    print(f"   📦 Main products valid: {validation_stats['main_products_valid']:,}")
    print(f"   🔄 Variations valid: {validation_stats['variations_valid']:,}")
    print(f"   📊 Total valid items: {len(valid_items):,}")
    print(f"   ❌ Insufficient stock (< {MIN_STOCK_REQUIRED}): {validation_stats['insufficient_stock']:,}")
    print(f"   ❌ Other filters: {validation_stats['filtered_by_constraints']:,}")
    
    if len(valid_items) == 0:
        print("❌ No valid products found after quality filtering!")
        return
    
    print("\n🎲 PHASE 3: Random Selection and Final Processing...")
    
    # Random shuffle for variety
    random.shuffle(valid_items)
    print(f"🎲 Shuffled {len(valid_items):,} valid items")
    
    # Select best products up to limit
    final_products = []
    for item_type, row in valid_items[:MAX_FINAL_PRODUCTS]:
        final_products.append(row)
    
    print(f"✅ Selected {len(final_products):,} products for final feed")
    
    # Remove duplicates by SKU
    seen_skus = set()
    unique_data = []
    for row in final_products:
        sku = row['sku']
        if sku not in seen_skus:
            seen_skus.add(sku)
            unique_data.append(row)
    
    print(f"✅ Final unique products: {len(unique_data):,}")
    
    # Create output files
    print("\n📁 Creating Optimized ManoMano Feed...")
    
    filename = 'manomano_optimized_feed.csv'
    html_filename = 'manomano_optimized_index.html'
    info_filename = 'manomano_optimized_info.json'
    
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
            "total_products": len(unique_data),
            "extraction_method": "OPTIMIZED_QUALITY_QUANTITY",
            "quality_filters": {
                "min_stock_required": MIN_STOCK_REQUIRED,
                "max_final_products": MAX_FINAL_PRODUCTS,
                "random_selection": True,
                "quality_thresholds_applied": True
            },
            "validation_stats": validation_stats,
            "random_seed": random_seed,
            "includes_variations": True,
            "marketplace": "ManoMano",
            "country": "Italy",
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}"
        }
        
        with open(info_filename, 'w') as f:
            json.dump(info_data, f, indent=2)
        print(f"✅ Created {info_filename}")
    except Exception as e:
        print(f"❌ Error creating JSON: {e}")
    
    # Create HTML summary
    try:
        main_count = sum(1 for item in valid_items if item[0] == 'main')
        variation_count = sum(1 for item in valid_items if item[0] == 'variation')
        
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>ManoMano Feed OTTIMIZZATO - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: #ff6b35; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .optimization {{ background: #007bff; color: white; padding: 25px; border-radius: 10px; margin: 30px 0; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .quality-box {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #007bff; }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 30px 0; }}
        .feed-url code {{ background: #fff; padding: 10px; border-radius: 5px; font-size: 14px; word-break: break-all; display: block; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 30px; background: white; border-radius: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff6b35; color: white; }}
        .price {{ color: #4caf50; font-weight: bold; }}
        .high-stock {{ color: #28a745; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Feed ManoMano OTTIMIZZATO</h1>
        <p><strong>Pop Pulse Emporium</strong> - Qualità + Quantità</p>
        <p>Ultimo Aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
    
    <div class="optimization">
        <h2>⚡ STRATEGIA DI OTTIMIZZAZIONE</h2>
        <p><strong>Estrazione Completa → Filtri Qualità → Selezione Casuale → Feed Ottimale</strong></p>
        <p>Risultato: {len(unique_data):,} prodotti di alta qualità da {len(valid_items):,} disponibili</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Prodotti Finali</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{MIN_STOCK_REQUIRED}+</div>
            <div class="stat-label">Stock Minimo</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{main_count:,}</div>
            <div class="stat-label">Prodotti Principali</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{variation_count:,}</div>
            <div class="stat-label">Variazioni</div>
        </div>
    </div>
    
    <div class="quality-box">
        <h3>🏆 CONTROLLI QUALITÀ APPLICATI</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4>📦 Filtri Stock:</h4>
                <ul>
                    <li>✅ Minimo {MIN_STOCK_REQUIRED} unità per prodotto</li>
                    <li>✅ Riduzione rischio overselling</li>
                    <li>✅ Maggiore affidabilità consegne</li>
                </ul>
            </div>
            <div>
                <h4>🎯 Ottimizzazioni:</h4>
                <ul>
                    <li>✅ Selezione casuale per varietà</li>
                    <li>✅ Limite {MAX_FINAL_PRODUCTS:,} prodotti</li>
                    <li>✅ Feed size gestibile</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed ManoMano OTTIMIZZATO:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{filename}</code>
        <p><strong>🎯 QUALITÀ PREMIUM: Solo prodotti con stock ≥{MIN_STOCK_REQUIRED} unità</strong></p>
    </div>
    
    <h2>📊 Prodotti Premium (Primi 20)</h2>
    <table>
        <tr>
            <th>SKU</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Parent_SKU</th>
            <th>Prezzo</th>
            <th>Stock</th>
            <th>Peso</th>
        </tr>"""
        
        # Show first 20 products with quality indicators
        for row in unique_data[:20]:
            sku = row.get("sku", "")
            parent_sku = row.get("Parent_SKU", "")
            title = safe_str(row.get("title", ""))[:45]
            if len(title) > 42:
                title += "..."
                
            ean = safe_str(row.get("ean", ""))
            price = row.get("product_price_vat_inc", 0)
            quantity = row.get("quantity", 0)
            weight = row.get("weight", 0)
            
            # Highlight high stock items
            stock_class = "high-stock" if quantity >= 5 else ""
            
            html_content += f"""
        <tr>
            <td><strong>{sku}</strong></td>
            <td>{title}</td>
            <td>{ean}</td>
            <td>{parent_sku}</td>
            <td class="price">€{price:.2f}</td>
            <td class="{stock_class}"><strong>{quantity}</strong></td>
            <td>{weight}kg</td>
        </tr>"""
        
        total_processed = validation_stats['main_products_processed'] + validation_stats['variations_processed']
        success_rate = (len(valid_items) / total_processed * 100) if total_processed > 0 else 0
        
        html_content += f"""
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>📈 Statistiche Ottimizzazione</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
            <div>
                <h4>📊 Numeri Chiave:</h4>
                <ul>
                    <li>Prodotti analizzati: {total_processed:,}</li>
                    <li>Prodotti validi: {len(valid_items):,}</li>
                    <li>Prodotti finali: {len(unique_data):,}</li>
                    <li>Tasso successo: {success_rate:.1f}%</li>
                </ul>
            </div>
            <div>
                <h4>❌ Filtri Applicati:</h4>
                <ul>
                    <li>Stock insufficiente: {validation_stats['insufficient_stock']:,}</li>
                    <li>Filtri qualità: {validation_stats['filtered_by_constraints']:,}</li>
                    <li>Prezzi non validi: {validation_stats['invalid_price']:,}</li>
                    <li>SKU mancanti: {validation_stats['missing_sku']:,}</li>
                </ul>
            </div>
        </div>
        
        <div style="background: #d1ecf1; padding: 20px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #0c5460;">
            <h4>🎯 STRATEGIA OTTIMALE RAGGIUNTA</h4>
            <p><strong>✅ Qualità:</strong> Ogni prodotto ha almeno {MIN_STOCK_REQUIRED} unità di stock per evitare overselling</p>
            <p><strong>✅ Quantità:</strong> {len(unique_data):,} prodotti selezionati da pool completo di {len(valid_items):,}</p>
            <p><strong>✅ Varietà:</strong> Selezione casuale garantisce mix diversificato di categorie</p>
            <p><strong>✅ Gestibilità:</strong> Feed ottimizzato per processing ManoMano (max {MAX_FINAL_PRODUCTS:,})</p>
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
    print("🎉 SUCCESS! OPTIMIZED MANOMANO FEED COMPLETE")
    print("=" * 80)
    print(f"📁 Files created:")
    print(f"   📄 CSV: {filename}")
    print(f"   🌐 HTML: {html_filename}")  
    print(f"   📋 JSON: {info_filename}")
    
    print(f"\n🎯 OPTIMIZATION RESULTS:")
    print(f"   📊 Total items analyzed: {total_processed:,}")
    print(f"   ✅ Quality items found: {len(valid_items):,}")
    print(f"   🎲 Final selection: {len(unique_data):,}")
    print(f"   📈 Quality success rate: {success_rate:.1f}%")
    
    if unique_data:
        prices = [row['product_price_vat_inc'] for row in unique_data]
        quantities = [row['quantity'] for row in unique_data]
        avg_stock = sum(quantities) / len(quantities)
        
        print(f"\n💰 Price range: €{min(prices):.2f} - €{max(prices):.2f}")
        print(f"📦 Stock range: {min(quantities)} - {max(quantities)} units")
        print(f"📊 Average stock: {avg_stock:.1f} units")
    
    print(f"\n🏆 QUALITY ACHIEVEMENTS:")
    print(f"   ✅ Every product has ≥{MIN_STOCK_REQUIRED} units stock (better reliability)")
    print(f"   ✅ Random selection ensures variety across categories")
    print(f"   ✅ {len(unique_data):,} products from complete dataset extraction")
    print(f"   ✅ Manageable feed size for ManoMano processing")
    print(f"   ✅ Balanced approach: Quality + Quantity optimization")
    
    # Performance assessment
    if len(unique_data) >= 50000:
        print(f"\n🎉 EXCELLENT! {len(unique_data):,} high-quality products!")
    elif len(unique_data) >= 25000:
        print(f"\n👍 VERY GOOD! {len(unique_data):,} quality products!")
    elif len(unique_data) >= 10000:
        print(f"\n✅ GOOD! {len(unique_data):,} quality products!")
    else:
        print(f"\n⚠️ Lower than expected: {len(unique_data):,} products")
        print("   🔍 Possible causes:")
        print("   - Higher stock requirements (≥2) filtering out many items")
        print("   - BigBuy stock levels generally low")
        print("   - API limitations or account restrictions")

if __name__ == "__main__":
    main()
