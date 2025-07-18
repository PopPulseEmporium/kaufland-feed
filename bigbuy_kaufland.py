import requests
import json
import csv
import os
import random
from datetime import datetime
import time
import hashlib

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
        # Add timestamp to prevent caching
        separator = '&' if '?' in endpoint else '?'
        cache_buster = f"{separator}t={int(time.time())}"
        url = f"{self.base_url}{endpoint}{cache_buster}"
        
        try:
            response = requests.get(url, headers=self.headers)
            print(f"Request: {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 401:
                print("❌ Authentication Error")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def get_taxonomies(self, limit=None):
        """Get product categories with optional limit"""
        result = self._make_request("/rest/catalog/taxonomies.json?firstLevel")
        if result:
            # Filter out erotic categories
            filtered = []
            erotic_keywords = ['erotic', 'erotico', 'adult', 'sex', 'sexy', 'intimate', 'lingerie']
            for taxonomy in result:
                name = taxonomy.get('name', '').lower()
                if not any(keyword in name for keyword in erotic_keywords):
                    filtered.append(taxonomy)
                else:
                    print(f"🚫 Filtered: {taxonomy['name']}")
            
            # IMPROVED: Randomize categories and increase limit
            random.shuffle(filtered)
            if limit:
                filtered = filtered[:limit]
            
            print(f"📊 Using {len(filtered)} categories (out of {len(result)} total)")
            return filtered
        return []

    def get_products(self, taxonomy_id, page=1, page_size=100):
        """Get products for category with pagination"""
        endpoint = f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}&pageSize={page_size}&page={page}"
        return self._make_request(endpoint)

    def get_all_products_for_taxonomy(self, taxonomy_id, max_products=1000):
        """Get all products for a taxonomy with pagination"""
        all_products = []
        page = 1
        
        while len(all_products) < max_products:
            products = self.get_products(taxonomy_id, page, 100)
            if not products or len(products) == 0:
                break
                
            all_products.extend(products)
            print(f"   📦 Page {page}: +{len(products)} products (total: {len(all_products)})")
            
            if len(products) < 100:  # Last page
                break
                
            page += 1
            time.sleep(0.3)  # Rate limiting
            
        return all_products[:max_products]

    def get_product_info(self, taxonomy_id, language="it"):
        """Get product descriptions in specified language"""
        return self._make_request(f"/rest/catalog/productsinformation.json?isoCode={language}&parentTaxonomy={taxonomy_id}")

    def get_product_images(self, taxonomy_id):
        """Get product images"""
        return self._make_request(f"/rest/catalog/productsimages.json?parentTaxonomy={taxonomy_id}")

def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        return float(value) if value else default
    except:
        return default

def safe_str(value, default=""):
    """Safely convert to string"""
    try:
        return str(value) if value else default
    except:
        return default

def safe_int(value, default=0):
    """Safely convert to int"""
    try:
        return int(value) if value else default
    except:
        return default

def get_currency_info(country):
    """Get currency and conversion info for country"""
    currency_config = {
        'AT': {'currency': 'EUR', 'rate': 1.0},
        'DE': {'currency': 'EUR', 'rate': 1.0},
        'IT': {'currency': 'EUR', 'rate': 1.0},
        'SK': {'currency': 'EUR', 'rate': 1.0},
        'PL': {'currency': 'PLN', 'rate': 4.5},
        'CZ': {'currency': 'CZK', 'rate': 24.0}
    }
    return currency_config.get(country, {'currency': 'EUR', 'rate': 1.0})

def calculate_real_quantity(bigbuy_stock):
    """Calculate real quantity based on BigBuy stock with safety margins"""
    stock = safe_int(bigbuy_stock, 0)
    
    if stock <= 0:
        return 0
    elif stock <= 2:
        return 1
    elif stock <= 5:
        return min(2, stock - 1)
    elif stock <= 10:
        return min(5, stock - 2)
    elif stock <= 20:
        return min(10, stock - 3)
    elif stock <= 50:
        return min(25, stock - 5)
    else:
        return min(50, int(stock * 0.9))

def create_random_seed():
    """Create a time-based random seed for better randomization"""
    current_hour = datetime.now().hour
    current_day = datetime.now().day
    seed = current_hour + current_day * 24
    print(f"🎲 Random seed: {seed} (hour: {current_hour}, day: {current_day})")
    return seed

def main():
    """Main function with improved randomization"""
    print("🚀 Starting BigBuy to Kaufland Multi-Country sync...")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # IMPROVED: Set random seed based on time for different results
    random_seed = create_random_seed()
    random.seed(random_seed)
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    # Get country from environment
    country = os.getenv('COUNTRY_CODE', 'IT').upper()
    
    # Country configuration
    country_config = {
        'AT': {'locale': 'de-AT', 'language': 'de', 'name': 'Austria'},
        'DE': {'locale': 'de-DE', 'language': 'de', 'name': 'Germany'}, 
        'PL': {'locale': 'pl-PL', 'language': 'pl', 'name': 'Poland'},
        'SK': {'locale': 'sk-SK', 'language': 'sk', 'name': 'Slovakia'},
        'CZ': {'locale': 'cs-CZ', 'language': 'cs', 'name': 'Czech Republic'},
        'IT': {'locale': 'it-IT', 'language': 'it', 'name': 'Italy'}
    }
    
    if country not in country_config:
        print(f"❌ Unsupported country: {country}")
        return
    
    config = country_config[country]
    currency_info = get_currency_info(country)
    
    print(f"🌍 Processing for {config['name']} ({country})")
    print(f"💱 Currency: {currency_info['currency']} (rate: {currency_info['rate']})")
    
    api = BigBuyAPI(api_key)
    
    # Configuration
    margin = 0.30
    vat = 0.22
    base_price = 0.75
    max_price_limit_eur = 200.0
    max_price_limit = max_price_limit_eur * currency_info['rate']
    max_content_volume = 70000
    max_weight = 25.0
    sample_size = 25000
    stock_minimum = 2
    
    # IMPROVED: Get more categories for better variety
    taxonomies = api.get_taxonomies(limit=20)  # Increased from 10 to 20
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories for {config['name']}...")
    
    # IMPROVED: Collect more products per category
    all_products = []
    all_info = []
    all_images = []
    
    max_products_per_category = 500  # Limit per category to avoid too much data
    
    for i, taxonomy in enumerate(taxonomies):
        tax_id = taxonomy['id']
        tax_name = taxonomy['name']
        
        print(f"📦 {i+1}/{len(taxonomies)}: {tax_name}")
        
        # IMPROVED: Get more products with pagination
        products = api.get_all_products_for_taxonomy(tax_id, max_products_per_category)
        if products:
            all_products.extend(products)
            print(f"   ✅ Added {len(products)} products")
        else:
            print(f"   ⚠️  No products found")
            
        # Get descriptions in local language
        info = api.get_product_info(tax_id, config['language'])
        if info:
            all_info.extend(info)
            print(f"   ✅ Added {len(info)} descriptions")
        
        # Get images
        images = api.get_product_images(tax_id)
        if images:
            all_images.extend(images)
            print(f"   ✅ Added {len(images)} image sets")
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"✅ Collected {len(all_products)} total products for {config['name']}")
    
    # IMPROVED: Shuffle all products before processing
    random.shuffle(all_products)
    print(f"🎲 Shuffled all products for randomization")
    
    # Create lookup dictionaries
    info_dict = {item['sku']: item for item in all_info}
    image_dict = {}
    
    # Process images
    for img_set in all_images:
        product_id = img_set['id']
        images = img_set.get('images', [])
        if images:
            image_dict[product_id] = {
                'image1': images[0].get('url', '') if len(images) > 0 else '',
                'image2': images[1].get('url', '') if len(images) > 1 else '',
                'image3': images[2].get('url', '') if len(images) > 2 else '',
                'image4': images[3].get('url', '') if len(images) > 3 else ''
            }
    
    # Apply filters and create CSV data
    csv_data = []
    filters_applied = {
        'total_products': 0,
        'condition_filtered': 0,
        'stock_filtered': 0,
        'weight_filtered': 0,
        'volume_filtered': 0,
        'price_filtered': 0,
        'quantity_filtered': 0,
        'final_products': 0
    }
    
    # IMPROVED: Process until we have enough products or run out
    processed_count = 0
    for product in all_products:
        processed_count += 1
        filters_applied['total_products'] += 1
        
        # Stop if we have enough products
        if len(csv_data) >= sample_size:
            print(f"🎯 Reached target of {sample_size} products, stopping processing")
            break
        
        # Only NEW products
        if product.get('condition', '').upper() != 'NEW':
            filters_applied['condition_filtered'] += 1
            continue
            
        # Filter out products with low stock
        stock_quantity = safe_float(product.get('inStock', 0))
        if stock_quantity < stock_minimum:
            filters_applied['stock_filtered'] += 1
            continue
            
        sku = product['sku']
        product_id = product['id']
        
        # Get additional info
        info = info_dict.get(sku, {})
        images = image_dict.get(product_id, {})
        
        # Filter by weight
        weight = safe_float(product.get('weight', 0))
        if weight > max_weight:
            filters_applied['weight_filtered'] += 1
            continue
        
        # Calculate dimensions and content volume
        width = safe_float(product.get('width', 0))
        height = safe_float(product.get('height', 0))
        depth = safe_float(product.get('depth', 0))
        content_volume = round(width * height * depth, 2)
        
        # Filter by content volume
        if content_volume > max_content_volume:
            filters_applied['volume_filtered'] += 1
            continue
            
        # Calculate price in EUR first
        wholesale_eur = safe_float(product.get('wholesalePrice', 0))
        price_eur = round((wholesale_eur * (1 + vat) * (1 + margin)) + base_price, 2)
        
        # Filter by maximum price in EUR
        if price_eur > max_price_limit_eur:
            filters_applied['price_filtered'] += 1
            continue
        
        # Convert price to local currency
        price_local = round(price_eur * currency_info['rate'], 2)
        
        # Calculate real quantity based on actual stock
        real_quantity = calculate_real_quantity(stock_quantity)
        
        # Skip if calculated quantity is 0
        if real_quantity <= 0:
            filters_applied['quantity_filtered'] += 1
            continue
        
        filters_applied['final_products'] += 1
        
        # Create row
        row = {
            'id_offer': str(sku),
            'ean': safe_str(product.get('ean13')),
            'locale': config['locale'],
            'category': 'Gardening & DIY',
            'title': safe_str(info.get('name', 'Product'))[:100],
            'short_description': safe_str(info.get('description', ''))[:150],
            'description': safe_str(info.get('description', ''))[:500],
            'manufacturer': 'Pop Pulse Emporium',
            'picture_1': images.get('image1', ''),
            'picture_2': images.get('image2', ''),
            'picture_3': images.get('image3', ''),
            'picture_4': images.get('image4', ''),
            'price_cs': price_local,
            'quantity': real_quantity,
            'condition': 'NEW',
            'length': round(depth, 2),
            'width': round(width, 2),
            'height': round(height, 2),
            'weight': round(weight, 2),
            'content_volume': content_volume,
            'currency': currency_info['currency'],
            'handling_time': 2,
            'delivery_time_max': 5,
            'delivery_time_min': 3
        }
        
        csv_data.append(row)
        
        # Progress update every 1000 products
        if processed_count % 1000 == 0:
            print(f"   📊 Processed {processed_count:,} products, accepted {len(csv_data):,}")
    
    # Print filter statistics
    print("🔍 FILTER STATISTICS:")
    print(f"   Total processed: {processed_count:,}")
    print(f"   ❌ Condition filtered: {filters_applied['condition_filtered']:,}")
    print(f"   ❌ Stock filtered: {filters_applied['stock_filtered']:,}")
    print(f"   ❌ Weight filtered (>{max_weight}kg): {filters_applied['weight_filtered']:,}")
    print(f"   ❌ Volume filtered (>{max_content_volume:,}cm³): {filters_applied['volume_filtered']:,}")
    print(f"   ❌ Price filtered (>{currency_info['currency']}{max_price_limit:.2f}): {filters_applied['price_filtered']:,}")
    print(f"   ❌ Quantity filtered (0 units): {filters_applied['quantity_filtered']:,}")
    print(f"   ✅ Final products: {len(csv_data):,}")
    
    # Remove duplicates by EAN
    seen_eans = set()
    unique_data = []
    
    for row in csv_data:
        ean = row['ean']
        if ean and ean not in seen_eans:
            seen_eans.add(ean)
            unique_data.append(row)
    
    print(f"✅ Found {len(unique_data)} unique products after deduplication")
    
    # IMPROVED: Create a hash of current data to detect changes
    data_hash = hashlib.md5(str(sorted([r['ean'] for r in unique_data])).encode()).hexdigest()[:8]
    print(f"🔧 Data fingerprint: {data_hash}")
    
    # Write files
    if unique_data:
        # Create country-specific files
        if country == 'IT':
            filename = 'kaufland_feed.csv'
            html_filename = 'index.html'
            info_filename = 'feed_info.json'
        else:
            filename = f'kaufland_feed_{country.lower()}.csv'
            html_filename = f'index_{country.lower()}.html'
            info_filename = f'feed_info_{country.lower()}.json'
        
        print(f"📁 Creating files for {config['name']}:")
        print(f"   CSV: {filename}")
        print(f"   HTML: {html_filename}")
        print(f"   JSON: {info_filename}")
        print(f"   Feed URL: https://poppulseemporium.github.io/kaufland-feed/{filename}")
            
        # Create CSV
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
                writer.writeheader()
                writer.writerows(unique_data)
            print(f"✅ Created {filename} with {len(unique_data)} products")
        except Exception as e:
            print(f"❌ Error creating CSV: {e}")
            return
        
        # Create info file
        try:
            info_data = {
                "last_updated": datetime.now().isoformat(),
                "product_count": len(unique_data),
                "total_products_processed": processed_count,
                "data_fingerprint": data_hash,
                "random_seed": random_seed,
                "max_price_filter": max_price_limit,
                "max_price_filter_eur": max_price_limit_eur,
                "max_content_volume": max_content_volume,
                "max_weight": max_weight,
                "currency": currency_info['currency'],
                "currency_rate": currency_info['rate'],
                "stock_minimum": stock_minimum,
                "margin_applied": f"{margin*100:.0f}%",
                "country": country,
                "locale": config['locale'],
                "language": config['language'],
                "filters_applied": filters_applied,
                "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}"
            }
            
            with open(info_filename, 'w') as f:
                json.dump(info_data, f, indent=2)
            print(f"✅ JSON info file created: {info_filename}")
        except Exception as e:
            print(f"❌ Error creating JSON: {e}")
        
        # Rest of the HTML creation code remains the same...
        # [HTML creation code would go here]
        
        print("✅ SUCCESS!")
        print(f"📁 Created {filename} with {len(unique_data):,} products for {config['name']}")
        print(f"📡 Feed URL: https://poppulseemporium.github.io/kaufland-feed/{filename}")
        print(f"🎲 Random seed used: {random_seed}")
        print(f"🔧 Data fingerprint: {data_hash}")
        
    else:
        print("❌ No products to export")

if __name__ == "__main__":
    main()
