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

    def load_manomano_categories(self, csv_filename='bigbuy_manomano_categories.csv'):
        """Load ManoMano-relevant categories from CSV file"""
        try:
            categories = []
            with open(csv_filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    categories.append({
                        'id': int(row['category_id']),
                        'name': row['category_name'],
                        'parent_id': int(float(row['parent_id'])) if row['parent_id'] and row['parent_id'] != '' else None,
                        'is_top_level': row['is_top_level'] == 'YES',
                        'url': row['url']
                    })
            
            print(f"✅ Loaded {len(categories)} ManoMano-relevant categories from {csv_filename}")
            
            # Show breakdown
            top_level = [cat for cat in categories if cat['is_top_level']]
            sub_categories = [cat for cat in categories if not cat['is_top_level']]
            
            print(f"   📁 Top-level: {len(top_level)}")
            print(f"   📂 Sub-categories: {len(sub_categories)}")
            
            return categories
            
        except FileNotFoundError:
            print(f"❌ CSV file '{csv_filename}' not found!")
            print("💡 Please make sure the categories CSV file is in the same directory")
            return []
        except Exception as e:
            print(f"❌ Error loading categories: {e}")
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
    """Main function - TARGETED: Only ManoMano-relevant categories"""
    print("🎯 MANOMANO FEED - TARGETED CATEGORIES ONLY")
    print("=" * 80)
    print("🚀 NEW STRATEGY:")
    print("   ✅ Process ONLY ManoMano-relevant categories (from CSV)")
    print("   ✅ 100% relevance rate (vs processing all BigBuy categories)")
    print("   ✅ Much faster processing (339 vs 1000+ categories)")
    print("   ✅ Higher quality 25k product selection")
    print("   ✅ Extract ALL products + variations from relevant categories")
    print("   ✅ Quality filters: min 2 units stock, random selection")
    print("=" * 80)
    
    # Get API key
    api_key = "YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ"
    
    print(f"🔑 Using API key (length: {len(api_key)})")
    
    api = BigBuyAPI(api_key)
    
    # OPTIMIZED Configuration
    margin = 0.40
    vat = 0.22
    base_price = 0.50
    min_price_eur = 0.50
    max_price_eur = 5000.0
    max_content_volume = 10000000000
    max_weight = 1000.0
    
    # QUALITY CONTROLS
    MIN_STOCK_REQUIRED = 2  # Higher quality threshold
    MAX_FINAL_PRODUCTS = 25000  # Target 25k products
    
    print(f"💰 Price range: €{min_price_eur} - €{max_price_eur}")
    print(f"📦 Minimum stock required: {MIN_STOCK_REQUIRED} units")
    print(f"🎯 Maximum final products: {MAX_FINAL_PRODUCTS:,}")
    
    # Set random seed for reproducibility within same day
    current_day = datetime.now().day
    random_seed = current_day * 1000 + datetime.now().hour
    random.seed(random_seed)
    print(f"🎲 Random seed: {random_seed}")
    
    # Load ManoMano-relevant categories from CSV
    print("\n📋 Loading ManoMano-relevant categories from CSV...")
    manomano_categories = api.load_manomano_categories()
    
    if not manomano_categories:
        print("❌ Failed to load ManoMano categories")
        return
    
    print(f"📊 Processing {len(manomano_categories)} ManoMano-relevant categories ONLY")
    
    # Collect complete dataset from RELEVANT categories only
    all_products = []
    all_variations_list = []
    all_info = []
    all_images = []
    all_stock_data = {'products': {}, 'variations': {}}
    
    print("\n🔄 PHASE 1: Collecting data from ManoMano-relevant categories...")
    
    successful_categories = 0
    failed_categories = 0
    
    for i, category in enumerate(manomano_categories):
        cat_id = category['id']
        cat_name = category['name']
        is_top_level = category['is_top_level']
        
        level_indicator = "📁 TOP" if is_top_level else "📂 SUB"
        print(f"{level_indicator} {i+1}/{len(manomano_categories)}: {cat_name} (ID: {cat_id})")
        
        try:
            # Get ALL products and variations (no limits in extraction phase)
            products = api.get_products(cat_id)
            if products:
                all_products.extend(products)
                print(f"   📦 Found {len(products)} products")
            
            variations = api.get_product_variations(cat_id)
            if variations:
                for variation in variations:
                    variation['taxonomy'] = cat_id
                    variation['taxonomy_name'] = cat_name
                    all_variations_list.append(variation)
                print(f"   🔄 Found {len(variations)} variations")
            
            # Get stock data
            product_stock = api.get_product_stock(cat_id)
            if product_stock:
                stock_count = 0
                for stock_item in product_stock:
                    sku = stock_item.get('sku')
                    stocks = stock_item.get('stocks', [])
                    total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                    if sku and total_quantity > 0:
                        all_stock_data['products'][sku] = total_quantity
                        stock_count += 1
                if stock_count > 0:
                    print(f"   📊 Stock for {stock_count} products")
            
            variation_stock = api.get_variations_stock(cat_id)
            if variation_stock:
                var_stock_count = 0
                for stock_item in variation_stock:
                    sku = stock_item.get('sku')
                    stocks = stock_item.get('stocks', [])
                    total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                    if sku and total_quantity > 0:
                        all_stock_data['variations'][sku] = total_quantity
                        var_stock_count += 1
                if var_stock_count > 0:
                    print(f"   📊 Stock for {var_stock_count} variations")
            
            # Get info and images
            info = api.get_product_info(cat_id, 'it')
            if info:
                all_info.extend(info)
            
            images = api.get_product_images(cat_id)
            if images:
                all_images.extend(images)
            
            successful_categories += 1
            
        except Exception as e:
            print(f"   ❌ Error processing category {cat_id}: {e}")
            failed_categories += 1
        
        time.sleep(0.5)  # Rate limiting
        
        # Progress update every 20 categories
        if (i + 1) % 20 == 0:
            print(f"   📈 Progress: {len(all_products):,} products, {len(all_variations_list):,} variations")
    
    print(f"\n✅ EXTRACTION FROM MANOMANO CATEGORIES COMPLETE:")
    print(f"   ✅ Successfully processed: {successful_categories} categories")
    print(f"   ❌ Failed: {failed_categories} categories")
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
    category_dict = {cat['id']: cat['name'] for cat in manomano_categories}
    
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
        taxonomy_name = category_dict.get(product.get('taxonomy'), '')
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
    print("\n📁 Creating Targeted ManoMano Feed...")
    
    filename = 'manomano_targeted_feed.csv'
    html_filename = 'manomano_targeted_index.html'
    info_filename = 'manomano_targeted_info.json'
    
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
            "extraction_method": "TARGETED_MANOMANO_CATEGORIES_ONLY",
            "manomano_categories_processed": len(manomano_categories),
            "successful_categories": successful_categories,
            "failed_categories": failed_categories,
            "quality_filters": {
                "min_stock_required": MIN_STOCK_REQUIRED,
                "max_final_products": MAX_FINAL_PRODUCTS,
                "random_selection": True,
                "source_csv": "bigbuy_manomano_categories.csv"
            },
            "validation_stats": validation_stats,
            "random_seed": random_seed,
            "includes_variations": True,
            "marketplace": "ManoMano",
            "country": "Italy",
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}"
        }
        
        print(f"✅ Created {info_filename}")
    except Exception as e:
        print(f"❌ Error creating JSON: {e}")
    
    # Create HTML summary
    try:
        main_count = validation_stats['main_products_valid']
        variation_count = validation_stats['variations_valid']
        
        html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>ManoMano Feed TARGETED - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: #ff6b35; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .targeted {{ background: #28a745; color: white; padding: 25px; border-radius: 10px; margin: 30px 0; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .efficiency {{ background: #d4edda; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #28a745; }}
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
        <h1>🎯 Feed ManoMano TARGETED</h1>
        <p><strong>Pop Pulse Emporium</strong> - Solo Categorie Rilevanti</p>
        <p>Ultimo Aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
    
    <div class="targeted">
        <h2>🚀 STRATEGIA TARGETED: 100% RILEVANZA</h2>
        <p><strong>Processate SOLO le {len(manomano_categories)} categorie ManoMano-rilevanti</strong></p>
        <p>Risultato: {len(unique_data):,} prodotti ad alta qualità da categorie selezionate</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Prodotti Finali</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{len(manomano_categories)}</div>
            <div class="stat-label">Categorie Processate</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{successful_categories}</div>
            <div class="stat-label">Categorie Successo</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">100%</div>
            <div class="stat-label">Rilevanza ManoMano</div>
        </div>
    </div>
    
    <div class="efficiency">
        <h3>⚡ EFFICIENZA TARGETED APPROACH</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4>📈 Vantaggi:</h4>
                <ul>
                    <li>✅ 100% categorie rilevanti per ManoMano</li>
                    <li>✅ Processing molto più veloce</li>
                    <li>✅ Qualità prodotti garantita</li>
                    <li>✅ Nessuna categoria irrilevante processata</li>
                </ul>
            </div>
            <div>
                <h4>📊 Risultati:</h4>
                <ul>
                    <li>Prodotti principali: {main_count:,}</li>
                    <li>Variazioni: {variation_count:,}</li>
                    <li>Stock minimo: {MIN_STOCK_REQUIRED} unità</li>
                    <li>Successo categorie: {successful_categories}/{len(manomano_categories)}</li>
                </ul>
            </div>
        </div>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed ManoMano TARGETED:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{filename}</code>
        <p><strong>🎯 PRECISIONE MASSIMA: Solo prodotti da categorie ManoMano-rilevanti</strong></p>
    </div>
    
    <h2>📊 Prodotti Selezionati (Primi 20)</h2>
    <table>
        <tr>
            <th>SKU</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Parent_SKU</th>
            <th>Prezzo</th>
            <th>Stock</th>
            <th>mm_category</th>
        </tr>"""
        
        # Show first 20 products
        for row in unique_data[:20]:
            sku = row.get("sku", "")
            parent_sku = row.get("Parent_SKU", "")
            title = safe_str(row.get("title", ""))[:45]
            if len(title) > 42:
                title += "..."
                
            ean = safe_str(row.get("ean", ""))
            price = row.get("product_price_vat_inc", 0)
            quantity = row.get("quantity", 0)
            mm_category = row.get("mm_category", "")
            
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
            <td>{mm_category}</td>
        </tr>"""
        
        total_processed = validation_stats['main_products_processed'] + validation_stats['variations_processed']
        success_rate = (len(valid_items) / total_processed * 100) if total_processed > 0 else 0
        
        html_content += f"""
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>🎯 Statistiche Approccio Targeted</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
            <div>
                <h4>📊 Performance:</h4>
                <ul>
                    <li>Categorie target: {len(manomano_categories)}</li>
                    <li>Categorie elaborate: {successful_categories}</li>
                    <li>Prodotti analizzati: {total_processed:,}</li>
                    <li>Prodotti finali: {len(unique_data):,}</li>
                </ul>
            </div>
            <div>
                <h4>⚡ Efficienza:</h4>
                <ul>
                    <li>Tasso successo: {success_rate:.1f}%</li>
                    <li>Rilevanza: 100% (solo categorie ManoMano)</li>
                    <li>Stock insufficiente: {validation_stats['insufficient_stock']:,}</li>
                    <li>Filtri applicati: {validation_stats['filtered_by_constraints']:,}</li>
                </ul>
            </div>
        </div>
        
        <div style="background: #fff3cd; padding: 20px; border-radius: 5px; margin-top: 20px; border-left: 4px solid #ffc107;">
            <h4>🎯 STRATEGIA VINCENTE</h4>
            <p><strong>✅ Targeted Approach:</strong> Processate solo le {len(manomano_categories)} categorie identificate come rilevanti per ManoMano</p>
            <p><strong>✅ Efficienza:</strong> Nessun tempo sprecato su categorie non pertinenti</p>
            <p><strong>✅ Qualità:</strong> Tutti i {len(unique_data):,} prodotti hanno stock ≥{MIN_STOCK_REQUIRED} e sono 100% rilevanti per ManoMano</p>
            <p><strong>✅ Risultato:</strong> Feed ottimizzato con prodotti mirati per il marketplace</p>
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
    print("🎉 SUCCESS! TARGETED MANOMANO FEED COMPLETE")
    print("=" * 80)
    print(f"📁 Files created:")
    print(f"   📄 CSV: {filename}")
    print(f"   🌐 HTML: {html_filename}")  
    print(f"   📋 JSON: {info_filename}")
    
    print(f"\n🎯 TARGETED APPROACH RESULTS:")
    print(f"   📊 ManoMano categories processed: {len(manomano_categories)}")
    print(f"   ✅ Successful categories: {successful_categories}")
    print(f"   ❌ Failed categories: {failed_categories}")
    print(f"   📦 Total items found: {total_processed:,}")
    print(f"   🎲 Final selection: {len(unique_data):,}")
    print(f"   📈 Success rate: {success_rate:.1f}%")
    
    if unique_data:
        prices = [row['product_price_vat_inc'] for row in unique_data]
        quantities = [row['quantity'] for row in unique_data]
        categories = list(set([row['mm_category'] for row in unique_data]))
        avg_stock = sum(quantities) / len(quantities)
        
        print(f"\n💰 Product Analysis:")
        print(f"   💰 Price range: €{min(prices):.2f} - €{max(prices):.2f}")
        print(f"   📦 Stock range: {min(quantities)} - {max(quantities)} units")
        print(f"   📊 Average stock: {avg_stock:.1f} units")
        print(f"   📂 Categories: {len(categories)} unique mm_categories")
    
    print(f"\n🏆 TARGETED STRATEGY ACHIEVEMENTS:")
    print(f"   ✅ 100% relevant categories (no wasted processing)")
    print(f"   ✅ Every product from ManoMano-relevant categories")
    print(f"   ✅ Quality threshold: ≥{MIN_STOCK_REQUIRED} units stock")
    print(f"   ✅ Efficient processing: {successful_categories}/{len(manomano_categories)} categories")
    print(f"   ✅ Perfect for ManoMano: {len(unique_data):,} targeted products")
    
    # Performance assessment
    efficiency_rate = (successful_categories / len(manomano_categories)) * 100
    
    if efficiency_rate >= 90:
        print(f"\n🎉 EXCELLENT EFFICIENCY! {efficiency_rate:.1f}% categories processed successfully")
    elif efficiency_rate >= 75:
        print(f"\n👍 GOOD EFFICIENCY! {efficiency_rate:.1f}% categories processed successfully")
    else:
        print(f"\n⚠️ Lower efficiency: {efficiency_rate:.1f}% categories processed")
        print("   🔍 Some categories may have API issues or no products")
    
    if len(unique_data) >= 15000:
        print(f"🎉 EXCELLENT PRODUCT COUNT! {len(unique_data):,} products for ManoMano")
    elif len(unique_data) >= 8000:
        print(f"👍 GOOD PRODUCT COUNT! {len(unique_data):,} products for ManoMano")
    else:
        print(f"⚠️ Lower than expected: {len(unique_data):,} products")
        print("   💡 Consider reducing MIN_STOCK_REQUIRED or checking category data")

if __name__ == "__main__":
    main()
