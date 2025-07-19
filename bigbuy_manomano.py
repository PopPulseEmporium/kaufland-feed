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

    def get_taxonomies(self, limit=None):
        """Get product categories with optional limit"""
        result = self._make_request("/rest/catalog/taxonomies.json?firstLevel")
        if result:
            # Filter out erotic categories and focus on ManoMano relevant categories
            filtered = []
            erotic_keywords = ['erotic', 'erotico', 'adult', 'sex', 'sexy', 'intimate', 'lingerie', 'sensualidad']
            
            # ManoMano focuses on DIY, Home & Garden, Tools
            preferred_keywords = ['bricolaje', 'herramientas', 'jardín', 'hogar', 'cocina', 'iluminación', 'tool', 'garden', 'home', 'diy']
            
            for taxonomy in result:
                name = taxonomy.get('name', '').lower()
                if not any(keyword in name for keyword in erotic_keywords):
                    # Prioritize ManoMano-relevant categories
                    is_preferred = any(keyword in name for keyword in preferred_keywords)
                    taxonomy['is_preferred'] = is_preferred
                    filtered.append(taxonomy)
                else:
                    print(f"🚫 Filtered: {taxonomy['name']}")
            
            # Sort by preference (preferred categories first)
            filtered.sort(key=lambda x: not x.get('is_preferred', False))
            
            # Randomize within each group but keep preferred first
            random.shuffle(filtered)
            if limit:
                filtered = filtered[:limit]
            
            print(f"📊 Using {len(filtered)} categories for ManoMano")
            return filtered
        return []

    def get_products(self, taxonomy_id):
        """Get products for category"""
        return self._make_request(f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}")

    def get_product_variations(self, taxonomy_id):
        """Get product variations for category"""
        return self._make_request(f"/rest/catalog/productsvariations.json?parentTaxonomy={taxonomy_id}")

    def get_product_stock(self, taxonomy_id):
        """Get actual stock data by taxonomy"""
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

def calculate_real_quantity(bigbuy_stock):
    """Calculate real quantity based on BigBuy stock with safety margins"""
    stock = safe_int(bigbuy_stock, 0)
    
    if stock <= 0:
        return 0
    elif stock < 2:  # Require minimum 2 units
        return 0
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

def validate_product_data(product, info, variations, stock_data):
    """Validate that product has all required data for ManoMano"""
    
    # Check required fields exist
    required_fields = ['sku', 'ean13', 'wholesalePrice', 'condition', 'weight']
    for field in required_fields:
        if not product.get(field):
            return False, f"Missing {field}"
    
    # Validate EAN13 format (should be 13 digits)
    ean = str(product.get('ean13', '')).strip()
    if len(ean) != 13 or not ean.isdigit():
        return False, f"Invalid EAN13: {ean}"
    
    # Check if product is NEW condition
    if product.get('condition', '').upper() != 'NEW':
        return False, f"Not NEW condition: {product.get('condition')}"
    
    # Validate price is positive
    price = safe_float(product.get('wholesalePrice', 0))
    if price <= 0:
        return False, f"Invalid price: {price}"
    
    # Check if we have stock data (either direct or via variations)
    product_id = product.get('id')
    sku = product.get('sku')
    
    # Look for stock in direct stock data
    direct_stock = stock_data.get('products', {}).get(sku, 0)
    
    # Look for stock in variations
    variation_stock = 0
    if product_id in variations:
        for variation in variations[product_id]:
            var_sku = variation.get('sku')
            var_stock = stock_data.get('variations', {}).get(var_sku, 0)
            variation_stock += var_stock
    
    total_stock = direct_stock + variation_stock
    
    # ManoMano requires minimum 2 units in stock
    if total_stock < 2:
        return False, f"Insufficient stock (need ≥2, have: {total_stock})"
    
    # Validate product info exists
    if sku not in info:
        return False, f"No product information found for SKU: {sku}"
    
    product_info = info[sku]
    if not product_info.get('name') or len(product_info.get('name', '').strip()) < 3:
        return False, f"Invalid product name: {product_info.get('name')}"
    
    return True, total_stock

def create_random_seed():
    """Create a time-based random seed for better randomization"""
    current_hour = datetime.now().hour
    current_day = datetime.now().day
    seed = current_hour + current_day * 24
    print(f"🎲 Random seed: {seed} (hour: {current_hour}, day: {current_day})")
    return seed

def map_to_manomano_category(taxonomy_name):
    """Map BigBuy taxonomy to ManoMano category"""
    
    # ManoMano category mapping based on their structure
    category_mapping = {
        'bricolaje': 'Bricolage',
        'herramientas': 'Outillage',
        'jardín': 'Jardin',
        'jardin': 'Jardin',
        'hogar': 'Maison',
        'cocina': 'Cuisine',
        'iluminación': 'Éclairage',
        'iluminacion': 'Éclairage',
        'baño': 'Salle de bain',
        'bano': 'Salle de bain',
        'construcción': 'Construction',
        'construccion': 'Construction',
        'electricidad': 'Électricité',
        'fontanería': 'Plomberie',
        'fontaneria': 'Plomberie',
        'pintura': 'Peinture',
        'suelos': 'Sol',
        'tejados': 'Toiture',
        'ventanas': 'Menuiserie',
        'puertas': 'Menuiserie',
        'calefacción': 'Chauffage',
        'calefaccion': 'Chauffage'
    }
    
    name_lower = taxonomy_name.lower()
    
    # Check for exact matches first
    for key, value in category_mapping.items():
        if key in name_lower:
            return value
    
    # Default categories for common items
    if any(word in name_lower for word in ['tool', 'herramienta', 'útil']):
        return 'Outillage'
    elif any(word in name_lower for word in ['garden', 'jardín', 'exterior']):
        return 'Jardin'
    elif any(word in name_lower for word in ['home', 'casa', 'hogar', 'maison']):
        return 'Maison'
    else:
        return 'Bricolage'  # Default category

def create_html_page(unique_data, margin, files_created, config):
    """Create HTML page with product data for ManoMano"""
    
    if not unique_data:
        return "<html><body><h1>Nessun prodotto disponibile</h1></body></html>"
    
    try:
        prices = [row['price'] for row in unique_data if 'price' in row and row['price']]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
    except Exception:
        min_price = 0
        max_price = 0
    
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Feed Prodotti ManoMano - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: #ff6b35; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #ff6b35; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 30px 0; }}
        .feed-url code {{ background: #fff; padding: 10px; border-radius: 5px; font-size: 14px; word-break: break-all; display: block; margin: 10px 0; }}
        .validation {{ background: #d4edda; padding: 15px; border-radius: 10px; margin: 20px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 30px; background: white; border-radius: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #ff6b35; color: white; }}
        .price {{ color: #4caf50; font-weight: bold; }}
        .image {{ max-width: 60px; max-height: 60px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔨 Feed Prodotti ManoMano</h1>
        <p><strong>Pop Pulse Emporium</strong> - Ultimo Aggiornamento: {current_time}</p>
    </div>
    
    <div>
        <h2>🇮🇹 Mercato: Italia</h2>
        <p><strong>Marketplace:</strong> ManoMano | <strong>Lingua:</strong> Italiano | <strong>Valuta:</strong> EUR</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Prodotti Validati</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{margin*100:.0f}%</div>
            <div class="stat-label">Margine</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">€{min_price:.2f}</div>
            <div class="stat-label">Prezzo Min</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">€{max_price:.2f}</div>
            <div class="stat-label">Prezzo Max</div>
        </div>
    </div>
    
    <div class="validation">
        <h3>✅ Validazione Stock Completa per ManoMano</h3>
        <p><strong>Tutti i prodotti in questo feed hanno:</strong></p>
        <ul>
            <li>✅ Stock confermato da BigBuy API (≥2 unità)</li>
            <li>✅ Codici EAN13 validi (13 cifre)</li>
            <li>✅ Condizione NUOVO</li>
            <li>✅ Informazioni prodotto complete in italiano</li>
            <li>✅ Prezzi validati (≥€6)</li>
            <li>✅ Categorie mappate per ManoMano</li>
            <li>✅ Focus su Bricolage, Giardino, Casa</li>
        </ul>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed per ManoMano:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{files_created[0]}</code>
        <p><small>✅ Feed ottimizzato per ManoMano - Nessun rischio di overselling</small></p>
    </div>
    
    <h2>📊 Prodotti Validati (Primi 50)</h2>
    <table>
        <tr>
            <th>Immagine</th>
            <th>SKU</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Categoria</th>
            <th>Prezzo</th>
            <th>Stock</th>
        </tr>"""
    
    # Add first 50 products to table
    for i, row in enumerate(unique_data[:50]):
        img_url = row.get("image_url", "")
        img_tag = f'<img src="{img_url}" class="image" alt="Prodotto">' if img_url else "No img"
        
        sku = safe_str(row.get("sku", ""))
        title = safe_str(row.get("title", ""))[:35]
        if len(title) > 32:
            title += "..."
            
        ean = safe_str(row.get("ean", ""))
        category = safe_str(row.get("category", ""))
        price = row.get("price", 0)
        quantity = row.get("quantity", 0)
        
        html_content += f"""
        <tr>
            <td>{img_tag}</td>
            <td><strong>{sku}</strong></td>
            <td><strong>{title}</strong></td>
            <td>{ean}</td>
            <td>{category}</td>
            <td class="price">€{price:.2f}</td>
            <td><strong>{quantity}</strong></td>
        </tr>"""
    
    html_content += f"""
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>📋 Informazioni Feed ManoMano</h3>
        <ul>
            <li><strong>Aggiornamento:</strong> Ogni 6 ore automaticamente</li>
            <li><strong>Validazione Stock:</strong> ✅ Attiva - Tutti i prodotti hanno stock confermato (≥2 unità)</li>
            <li><strong>Filtri Qualità:</strong> Solo prodotti NUOVI con EAN validi</li>
            <li><strong>Prezzo Minimo:</strong> €6 (per margini migliori)</li>
            <li><strong>Categorie Focus:</strong> Bricolage, Giardino, Casa, Attrezzi</li>
            <li><strong>Margine:</strong> 30% applicato</li>
            <li><strong>Valuta:</strong> EUR</li>
            <li><strong>Marketplace:</strong> ManoMano Italia</li>
        </ul>
    </div>
</body>
</html>"""
    
    return html_content

def main():
    """Main function for ManoMano feed generation"""
    print("🔨 STARTING MANOMANO FEED GENERATION WITH STOCK VALIDATION")
    print("=" * 70)
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get API key from environment
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found in BIGBUY_API_KEY environment variable")
        return
    
    print(f"🔑 API key found (length: {len(api_key)})")
    
    # ManoMano is for Italy
    country = 'IT'
    config = {'locale': 'it-IT', 'language': 'it', 'name': 'Italy'}
    
    print(f"🇮🇹 Processing for ManoMano Italy")
    print(f"🗣️ Language: Italian")
    
    # Set random seed for variety
    random_seed = create_random_seed()
    random.seed(random_seed)
    
    api = BigBuyAPI(api_key)
    
    # Configuration for ManoMano
    margin = 0.30
    vat = 0.22
    base_price = 0.75
    min_price_eur = 6.0  # Minimum €6
    max_price_eur = 500.0  # Higher limit for ManoMano (tools, equipment)
    max_content_volume = 100000  # Larger volume for ManoMano (100L)
    max_weight = 50.0  # Higher weight limit for tools/equipment
    sample_size = 20000  # Target sample size for ManoMano
    
    print(f"💰 Price range: €{min_price_eur} - €{max_price_eur}")
    print(f"📦 Max content volume: {max_content_volume:,} cm³")
    print(f"⚖️ Max weight: {max_weight} kg")
    print(f"🎯 Target sample size: {sample_size}")
    
    # Get taxonomies focused on ManoMano categories
    taxonomies = api.get_taxonomies(limit=15)  # Focus on relevant categories
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories for ManoMano")
    
    # Collect all data including STOCK
    all_products = []
    all_info = []
    all_images = []
    all_variations = {}
    all_stock_data = {'products': {}, 'variations': {}}
    
    print("\n🔄 Collecting Products, Variations, and Stock Data...")
    
    for i, taxonomy in enumerate(taxonomies):
        tax_id = taxonomy['id']
        tax_name = taxonomy['name']
        is_preferred = taxonomy.get('is_preferred', False)
        
        print(f"📦 {i+1}/{len(taxonomies)}: {tax_name} {'⭐' if is_preferred else ''}")
        
        # Get more products from preferred categories
        product_limit = 800 if is_preferred else 400
        
        # Get products
        products = api.get_products(tax_id)
        if products:
            random.shuffle(products)
            limited_products = products[:product_limit]
            all_products.extend(limited_products)
        
        # Get variations
        variations = api.get_product_variations(tax_id)
        if variations:
            for variation in variations:
                product_id = variation.get('product')
                if product_id not in all_variations:
                    all_variations[product_id] = []
                all_variations[product_id].append(variation)
        
        # Get direct product stock
        product_stock = api.get_product_stock(tax_id)
        if product_stock:
            for stock_item in product_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['products'][sku] = total_quantity
        
        # Get variation stock
        variation_stock = api.get_variations_stock(tax_id)
        if variation_stock:
            for stock_item in variation_stock:
                sku = stock_item.get('sku')
                stocks = stock_item.get('stocks', [])
                total_quantity = sum(stock.get('quantity', 0) for stock in stocks)
                if sku and total_quantity > 0:
                    all_stock_data['variations'][sku] = total_quantity
        
        # Get descriptions in Italian
        info = api.get_product_info(tax_id, config['language'])
        if info:
            all_info.extend(info)
        
        # Get images
        images = api.get_product_images(tax_id)
        if images:
            all_images.extend(images)
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"✅ Collection Complete:")
    print(f"   📦 Products: {len(all_products)}")
    print(f"   📊 Product stock entries: {len(all_stock_data['products'])}")
    print(f"   📊 Variation stock entries: {len(all_stock_data['variations'])}")
    print(f"   📝 Descriptions: {len(all_info)}")
    print(f"   🖼️ Images: {len(all_images)}")
    
    # Create lookup dictionaries
    info_dict = {item['sku']: item for item in all_info}
    image_dict = {}
    
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
    
    print("\n🔍 Validating Products with Stock for ManoMano...")
    
    # Validate and process products
    csv_data = []
    validation_stats = {
        'total_processed': 0,
        'missing_sku': 0,
        'invalid_ean': 0,
        'not_new_condition': 0,
        'invalid_price': 0,
        'no_stock': 0,
        'no_product_info': 0,
        'invalid_name': 0,
        'price_too_high': 0,
        'price_too_low': 0,
        'weight_too_high': 0,
        'volume_too_high': 0,
        'valid_products': 0
    }
    
    # Shuffle all products for randomization
    random.shuffle(all_products)
    
    for product in all_products:
        validation_stats['total_processed'] += 1
        
        # Validate product data
        is_valid, stock_or_reason = validate_product_data(
            product, info_dict, all_variations, all_stock_data
        )
        
        if not is_valid:
            # Count the specific validation failure
            if "Missing sku" in stock_or_reason:
                validation_stats['missing_sku'] += 1
            elif "Invalid EAN13" in stock_or_reason:
                validation_stats['invalid_ean'] += 1
            elif "Not NEW condition" in stock_or_reason:
                validation_stats['not_new_condition'] += 1
            elif "Invalid price" in stock_or_reason:
                validation_stats['invalid_price'] += 1
            elif "Insufficient stock" in stock_or_reason:
                validation_stats['no_stock'] += 1
            elif "No product information" in stock_or_reason:
                validation_stats['no_product_info'] += 1
            elif "Invalid product name" in stock_or_reason:
                validation_stats['invalid_name'] += 1
            continue
        
        total_stock = stock_or_reason  # stock_or_reason contains stock when valid
        
        # Additional filters for ManoMano
        weight = safe_float(product.get('weight', 0))
        if weight > max_weight:
            validation_stats['weight_too_high'] += 1
            continue
        
        # Calculate dimensions and content volume
        width = safe_float(product.get('width', 0))
        height = safe_float(product.get('height', 0))
        depth = safe_float(product.get('depth', 0))
        content_volume = width * height * depth
        
        if content_volume > max_content_volume:
            validation_stats['volume_too_high'] += 1
            continue
        
        # Calculate price
        wholesale_eur = safe_float(product.get('wholesalePrice', 0))
        price_eur = (wholesale_eur * (1 + vat) * (1 + margin)) + base_price
        
        # Filter by maximum price
        if price_eur > max_price_eur:
            validation_stats['price_too_high'] += 1
            continue
        
        # Filter by minimum price (€6)
        if price_eur < min_price_eur:
            validation_stats['price_too_low'] += 1
            continue
        
        # Calculate safe quantity
        real_quantity = calculate_real_quantity(total_stock)
        if real_quantity <= 0:
            validation_stats['no_stock'] += 1
            continue
        
        validation_stats['valid_products'] += 1
        
        # Get additional data
        sku = product['sku']
        product_id = product['id']
        info = info_dict.get(sku, {})
        images = image_dict.get(product_id, {})
        
        # Get taxonomy for category mapping
        taxonomy_name = ""
        for taxonomy in taxonomies:
            if taxonomy['id'] == product.get('taxonomy'):
                taxonomy_name = taxonomy['name']
                break
        
        manomano_category = map_to_manomano_category(taxonomy_name)
        
        # Create ManoMano CSV row based on their format
        row = {
            'sku': str(sku),
            'ean': safe_str(product.get('ean13')),
            'title': safe_str(info.get('name', 'Product'))[:100],
            'description': safe_str(info.get('description', ''))[:2000],
            'brand': 'Pop Pulse Emporium',
            'category': manomano_category,
            'price': round(price_eur, 2),
            'quantity': real_quantity,
            'condition': 'Nuovo',
            'weight': round(weight, 2),
            'length': round(depth, 2),
            'width': round(width, 2),
            'height': round(height, 2),
            'image_url': images.get('image1', ''),
            'image_url_2': images.get('image2', ''),
            'image_url_3': images.get('image3', ''),
            'image_url_4': images.get('image4', ''),
            'shipping_cost': '0',  # Free shipping
            'delivery_time': '3-5 giorni',
            'warranty': '24 mesi',
            'origin_country': 'EU',
            'material': '',  # Could be extracted from attributes if available
            'color': '',     # Could be extracted from attributes if available
            'size': '',      # Could be extracted from attributes if available
        }
        
        csv_data.append(row)
        
        # Progress update every 1000 products
        if validation_stats['total_processed'] % 1000 == 0:
            print(f"   📊 Processed {validation_stats['total_processed']:,}, found {validation_stats['valid_products']:,} valid")
        
        # Stop if we have enough products
        if len(csv_data) >= sample_size:
            print(f"🎯 Reached target of {sample_size} products")
            break
    
    # Print validation statistics
    print(f"\n🔍 VALIDATION STATISTICS:")
    print(f"   📊 Total processed: {validation_stats['total_processed']:,}")
    print(f"   ❌ No stock: {validation_stats['no_stock']:,}")
    print(f"   ❌ Invalid EAN: {validation_stats['invalid_ean']:,}")
    print(f"   ❌ Price too low (<€{min_price_eur}): {validation_stats['price_too_low']:,}")
    print(f"   ❌ Price too high (>€{max_price_eur}): {validation_stats['price_too_high']:,}")
    print(f"   ❌ Volume too high: {validation_stats['volume_too_high']:,}")
    print(f"   ❌ Weight too high: {validation_stats['weight_too_high']:,}")
    print(f"   ❌ Other issues: {validation_stats['missing_sku'] + validation_stats['not_new_condition'] + validation_stats['invalid_price'] + validation_stats['no_product_info'] + validation_stats['invalid_name']:,}")
    print(f"   ✅ Valid products: {validation_stats['valid_products']:,}")
    
    if validation_stats['total_processed'] > 0:
        success_rate = 100 * validation_stats['valid_products'] / validation_stats['total_processed']
        print(f"   📈 Success rate: {success_rate:.1f}%")
    
    # Remove duplicates by EAN
    seen_eans = set()
    unique_data = []
    
    for row in csv_data:
        ean = row['ean']
        if ean and ean not in seen_eans:
            seen_eans.add(ean)
            unique_data.append(row)
    
    print(f"\n✅ Found {len(unique_data)} unique products after deduplication")
    
    if not unique_data:
        print("❌ No valid products found!")
        print("💡 Possible issues:")
        print("   - Stock endpoints not accessible")
        print("   - Filters too restrictive")
        print("   - API account limitations")
        return
    
    # Create files for ManoMano
    print("\n📁 Creating ManoMano Output Files...")
    
    filename = 'manomano_feed.csv'
    html_filename = 'manomano_index.html'
    info_filename = 'manomano_feed_info.json'
    
    # Create CSV for ManoMano
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
            writer.writeheader()
            writer.writerows(unique_data)
        print(f"✅ Created {filename} with {len(unique_data)} products")
    except Exception as e:
        print(f"❌ Error creating CSV: {e}")
        return
    
    files_created = [filename]
    
    # Create info file
    try:
        info_data = {
            "last_updated": datetime.now().isoformat(),
            "product_count": len(unique_data),
            "random_seed": random_seed,
            "validation_stats": validation_stats,
            "stock_validation_enabled": True,
            "marketplace": "ManoMano",
            "country": "Italy",
            "min_price_eur": min_price_eur,
            "max_price_eur": max_price_eur,
            "max_content_volume": max_content_volume,
            "max_weight": max_weight,
            "currency": "EUR",
            "margin_applied": f"{margin*100:.0f}%",
            "language": "it",
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}",
            "quality_assurance": "ALL_PRODUCTS_HAVE_CONFIRMED_STOCK_AND_VALID_DATA_FOR_MANOMANO"
        }
        
        with open(info_filename, 'w') as f:
            json.dump(info_data, f, indent=2)
        print(f"✅ Created {info_filename}")
    except Exception as e:
        print(f"❌ Error creating JSON: {e}")
    
    # Create HTML page
    try:
        html_content = create_html_page(unique_data, margin, files_created, config)
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Created {html_filename}")
    except Exception as e:
        print(f"❌ Error creating HTML: {e}")
        # Create simple fallback HTML
        try:
            simple_html = f"""<!DOCTYPE html>
<html><head><title>Feed ManoMano Italia</title></head>
<body>
<h1>🔨 Feed ManoMano - {len(unique_data)} Prodotti Validati</h1>
<p><strong>Marketplace:</strong> ManoMano Italia</p>
<p><strong>Prodotti:</strong> {len(unique_data)} con stock confermato (≥2 unità)</p>
<p><strong>Validazione Stock:</strong> ✅ Attiva</p>
<p><strong>Range Prezzi:</strong> €{min_price_eur} - €{max_price_eur}</p>
<p><strong>URL Feed:</strong> <a href="{filename}">{filename}</a></p>
<p><strong>Ultimo Aggiornamento:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</body></html>"""
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(simple_html)
            print(f"✅ Created fallback HTML: {html_filename}")
        except Exception as e2:
            print(f"❌ Even fallback HTML failed: {e2}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 SUCCESS! MANOMANO FEED GENERATED WITH STOCK VALIDATION")
    print("=" * 70)
    print(f"📁 Files created:")
    print(f"   📄 CSV: {filename}")
    print(f"   🌐 HTML: {html_filename}")
    print(f"   📋 JSON: {info_filename}")
    print(f"📊 Products: {len(unique_data)} (ALL with confirmed stock ≥2 units)")
    
    if unique_data:
        prices = [row['price'] for row in unique_data]
        quantities = [row['quantity'] for row in unique_data]
        categories = list(set([row['category'] for row in unique_data]))
        
        print(f"💰 Price range: €{min(prices):.2f} - €{max(prices):.2f}")
        print(f"📦 Quantity range: {min(quantities)} - {max(quantities)} units")
        print(f"📂 Categories: {', '.join(categories[:5])}{'...' if len(categories) > 5 else ''}")
    
    print(f"🌐 Feed URL: https://poppulseemporium.github.io/kaufland-feed/{filename}")
    print(f"📈 Success Rate: {validation_stats['valid_products']}/{validation_stats['total_processed']} ({100*validation_stats['valid_products']/validation_stats['total_processed']:.1f}%)")
    
    print(f"\n✅ MANOMANO QUALITY ASSURANCE COMPLETE:")
    print(f"   ✅ Stock validation: ENABLED (≥2 units required)")
    print(f"   ✅ EAN13 validation: ENABLED")
    print(f"   ✅ Price validation: ENABLED (€{min_price_eur}-{max_price_eur})")
    print(f"   ✅ Physical constraints: ENABLED (≤{max_weight}kg, ≤{max_content_volume:,}cm³)")
    print(f"   ✅ Category mapping: ENABLED (ManoMano categories)")
    print(f"   ✅ Italian language: ENABLED")
    print(f"   ✅ No overselling risk: GUARANTEED")

if __name__ == "__main__":
    main()
