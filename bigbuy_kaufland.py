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
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        
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

    def get_taxonomies(self):
        """Get product categories"""
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
            return filtered[:10]  # Limit to 10 categories
        return []

    def get_products(self, taxonomy_id):
        """Get products for category"""
        return self._make_request(f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}")

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
        'SK': {'currency': 'EUR', 'rate': 1.0},  # Slovakia uses EUR
        'PL': {'currency': 'PLN', 'rate': 4.5},  # More realistic PLN rate
        'CZ': {'currency': 'CZK', 'rate': 24.0}  # More realistic CZK rate
    }
    return currency_config.get(country, {'currency': 'EUR', 'rate': 1.0})

def calculate_real_quantity(bigbuy_stock):
    """Calculate real quantity based on BigBuy stock with safety margins"""
    stock = safe_int(bigbuy_stock, 0)
    
    if stock <= 0:
        return 0
    elif stock <= 2:
        return 1  # Very low stock
    elif stock <= 5:
        return min(2, stock - 1)  # Leave 1 as safety margin
    elif stock <= 10:
        return min(5, stock - 2)  # Leave 2 as safety margin
    elif stock <= 20:
        return min(10, stock - 3)  # Leave 3 as safety margin
    elif stock <= 50:
        return min(25, stock - 5)  # Leave 5 as safety margin
    else:
        # For high stock, offer up to 50 but leave 10% margin
        return min(50, int(stock * 0.9))

def create_html_page(unique_data, margin, files_created, country, config):
    """Create HTML page with product data"""
    
    print(f"🔄 Creating HTML for {len(unique_data)} products...")
    
    # Safety check
    if not unique_data:
        print("❌ No data to create HTML page")
        return "<html><body><h1>Nessun prodotto disponibile</h1></body></html>"
    
    # Get currency info
    currency_info = get_currency_info(country)
    currency_symbol = currency_info['currency']
    
    # Calculate price range safely
    try:
        prices = [row['price_cs'] for row in unique_data if 'price_cs' in row and row['price_cs']]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        print(f"💰 Price range calculated: {currency_symbol}{min_price:.2f} - {currency_symbol}{max_price:.2f}")
    except Exception as e:
        print(f"❌ Error calculating prices: {e}")
        min_price = 0
        max_price = 0
    
    # Create HTML content step by step to avoid f-string issues
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    html_content = f"""<!DOCTYPE html>
<html lang="{config['language']}">
<head>
    <meta charset="UTF-8">
    <title>Feed Prodotti Kaufland - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: #667eea; color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 30px 0; }}
        .feed-url code {{ background: #fff; padding: 10px; border-radius: 5px; font-size: 14px; word-break: break-all; display: block; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 30px; background: white; border-radius: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #667eea; color: white; }}
        .price {{ color: #4caf50; font-weight: bold; }}
        .image {{ max-width: 60px; max-height: 60px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ Feed Prodotti Kaufland</h1>
        <p><strong>Pop Pulse Emporium</strong> - Ultimo Aggiornamento: {current_time}</p>
    </div>
    
    <div>
        <h2>🇪🇺 Paese: {config['name']} ({country})</h2>
        <p><strong>Lingua:</strong> {config['language'].upper()} | <strong>Locale:</strong> {config['locale']} | <strong>Valuta:</strong> {currency_symbol}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Prodotti</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{margin*100:.0f}%</div>
            <div class="stat-label">Margine</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{currency_symbol}{min_price:.2f}</div>
            <div class="stat-label">Prezzo Min</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{currency_symbol}{max_price:.2f}</div>
            <div class="stat-label">Prezzo Max</div>
        </div>
    </div>
    
    <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 30px 0;">
        <h3>✅ Pronto per Kaufland {config['name']}!</h3>
        <p>Feed ottimizzato per {config['name']} con {len(unique_data):,} prodotti (max {currency_symbol}200 equivalente).</p>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed per Kaufland:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{files_created[0]}</code>
        <p><small>Copia questo URL nel campo "Percorso del file" di Kaufland</small></p>
    </div>
    
    <h2>📊 Anteprima Prodotti (Primi 50)</h2>
    <table>
        <tr>
            <th>Immagine</th>
            <th>SKU</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Prezzo</th>
            <th>Quantità</th>
            <th>Descrizione</th>
        </tr>"""
    
    # Add first 50 products to table
    for i, row in enumerate(unique_data[:50]):
        img_url = row.get("picture_1", "")
        img_tag = f'<img src="{img_url}" class="image" alt="Prodotto">' if img_url else "No img"
        
        sku = safe_str(row.get("id_offer", ""))
        title = safe_str(row.get("title", ""))[:40]
        if len(title) > 37:
            title += "..."
            
        ean = safe_str(row.get("ean", ""))
        price = row.get("price_cs", 0)
        quantity = row.get("quantity", 0)
        currency = row.get("currency", currency_symbol)
        description = safe_str(row.get("description", ""))[:80]
        if len(description) > 77:
            description += "..."
        
        html_content += f"""
        <tr>
            <td>{img_tag}</td>
            <td><strong>{sku}</strong></td>
            <td><strong>{title}</strong></td>
            <td>{ean}</td>
            <td class="price">{currency}{price:.2f}</td>
            <td>{quantity}</td>
            <td>{description}</td>
        </tr>"""
    
    # Close the HTML
    html_content += f"""
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>📋 Informazioni</h3>
        <ul>
            <li><strong>Aggiornamento:</strong> Ogni 6 ore automaticamente</li>
            <li><strong>Selezione:</strong> Casuale dal catalogo BigBuy</li>
            <li><strong>Filtro prezzo:</strong> Massimo {currency_symbol}200 equivalente per prodotto</li>
            <li><strong>Filtro stock:</strong> Minimo 2 unità disponibili</li>
            <li><strong>Filtro volume:</strong> Massimo 70,000 cm³</li>
            <li><strong>Condizione:</strong> Solo prodotti NUOVI</li>
            <li><strong>Quantità:</strong> Stock reale con margine di sicurezza</li>
            <li><strong>Valuta:</strong> {currency_symbol}</li>
        </ul>
    </div>
</body>
</html>"""
    
    return html_content

def main():
    """Main function"""
    print("🚀 Starting BigBuy to Kaufland Multi-Country sync...")
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    # Get country from environment (for multi-country support)
    country = os.getenv('COUNTRY_CODE', 'IT').upper()
    
    # Country configuration - FIXED with Poland added
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
    
    # Configuration - UPDATED WITH YOUR REQUIREMENTS
    margin = 0.20
    vat = 0.22
    base_price = 0.75
    max_price_limit_eur = 200.0  # FIXED: €200 max price for all countries
    max_price_limit = max_price_limit_eur * currency_info['rate']  # Convert to local currency
    max_content_volume = 70000  # ADDED: Maximum content volume in cm³
    sample_size = 25000  # 25k products per country
    stock_minimum = 2  # Minimum stock required
    
    print(f"💰 Max price limit: {currency_info['currency']}{max_price_limit:.2f} (EUR {max_price_limit_eur})")
    print(f"📦 Max content volume: {max_content_volume:,} cm³")
    
    # Get data
    taxonomies = api.get_taxonomies()
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories for {config['name']}...")
    
    # Collect all data
    all_products = []
    all_info = []
    all_images = []
    
    for i, taxonomy in enumerate(taxonomies):
        tax_id = taxonomy['id']
        tax_name = taxonomy['name']
        
        print(f"📦 {i+1}/{len(taxonomies)}: {tax_name}")
        
        # Get products
        products = api.get_products(tax_id)
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
        else:
            print(f"   ⚠️  No descriptions found")
            
        # Get images
        images = api.get_product_images(tax_id)
        if images:
            all_images.extend(images)
            print(f"   ✅ Added {len(images)} image sets")
        else:
            print(f"   ⚠️  No images found")
        
        time.sleep(0.5)  # Rate limiting
    
    print(f"✅ Collected {len(all_products)} products for {config['name']}")
    
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
    
    # Create CSV with price and stock filtering
    csv_data = []
    
    for product in all_products:
        # Only NEW products
        if product.get('condition', '').upper() != 'NEW':
            continue
            
        # Filter out products with low stock
        stock_quantity = safe_float(product.get('inStock', 0))
        if stock_quantity < stock_minimum:
            continue
            
        sku = product['sku']
        product_id = product['id']
        
        # Get additional info
        info = info_dict.get(sku, {})
        images = image_dict.get(product_id, {})
        
        # Calculate dimensions and content volume
        width = safe_float(product.get('width', 0))
        height = safe_float(product.get('height', 0))
        depth = safe_float(product.get('depth', 0))
        content_volume = round(width * height * depth, 2)
        
        # ADDED: Filter by content volume
        if content_volume > max_content_volume:
            continue
            
        # Calculate price in EUR first
        wholesale_eur = safe_float(product.get('wholesalePrice', 0))
        price_eur = round((wholesale_eur * (1 + vat) * (1 + margin)) + base_price, 2)
        
        # Filter by maximum price in EUR
        if price_eur > max_price_limit_eur:
            continue
        
        # Convert price to local currency
        price_local = round(price_eur * currency_info['rate'], 2)
        
        # FIXED: Calculate real quantity based on actual stock
        real_quantity = calculate_real_quantity(stock_quantity)
        
        # Skip if calculated quantity is 0
        if real_quantity <= 0:
            continue
        
        # Create row with country-specific locale and currency
        row = {
            'id_offer': str(sku),  # FIXED: Use SKU instead of product_id
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
            'quantity': real_quantity,  # FIXED: Use calculated real quantity
            'condition': 'NEW',
            'length': round(depth, 2),  # Using depth as length
            'width': round(width, 2),
            'height': round(height, 2),
            'weight': round(safe_float(product.get('weight')), 2),
            'content_volume': content_volume,
            'currency': currency_info['currency'],  # Use country-specific currency
            'handling_time': 2,
            'delivery_time_max': 5,
            'delivery_time_min': 3
        }
        
        csv_data.append(row)
    
    print(f"✅ Created {len(csv_data)} products under {currency_info['currency']}{max_price_limit:.2f} and volume ≤{max_content_volume:,}cm³ for {config['name']}")
    
    # Remove duplicates and randomly select products
    seen_eans = set()
    unique_data = []
    
    for row in csv_data:
        ean = row['ean']
        if ean and ean not in seen_eans:
            seen_eans.add(ean)
            unique_data.append(row)
    
    print(f"✅ Found {len(unique_data)} unique products for {config['name']}")
    
    # Randomly select sample
    if len(unique_data) > sample_size:
        random.shuffle(unique_data)
        unique_data = unique_data[:sample_size]
        print(f"📊 Randomly selected {sample_size} products for {config['name']}")
    else:
        print(f"📊 Using all {len(unique_data)} products for {config['name']}")
    
    print(f"🔧 DEBUG: Country = {country}")
    print(f"🔧 DEBUG: Country config = {config}")
    print(f"🔧 DEBUG: Currency = {currency_info['currency']}")
    
    # Write files - FIXED file naming with DEBUG
    if unique_data:
        # Create country-specific files
        if country == 'IT':
            filename = 'kaufland_feed.csv'  # Keep Italy as main file
            html_filename = 'index.html'
            info_filename = 'feed_info.json'
        else:
            filename = f'kaufland_feed_{country.lower()}.csv'
            html_filename = f'index_{country.lower()}.html'
            info_filename = f'feed_info_{country.lower()}.json'
        
        print(f"🔧 DEBUG: Will create files:")
        print(f"   CSV: {filename}")
        print(f"   HTML: {html_filename}")
        print(f"   JSON: {info_filename}")
            
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
        
        files_created = [filename]
        
        # Create info file
        try:
            info_data = {
                "last_updated": datetime.now().isoformat(),
                "product_count": len(unique_data),
                "total_products_available": len(csv_data),
                "max_price_filter": max_price_limit,
                "max_price_filter_eur": max_price_limit_eur,
                "max_content_volume": max_content_volume,
                "currency": currency_info['currency'],
                "currency_rate": currency_info['rate'],
                "stock_minimum": stock_minimum,
                "margin_applied": f"{margin*100}%",
                "country": country,
                "locale": config['locale'],
                "language": config['language'],
                "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}"
            }
            
            with open(info_filename, 'w') as f:
                json.dump(info_data, f, indent=2)
            print(f"✅ JSON info file created: {info_filename}")
        except Exception as e:
            print(f"❌ Error creating JSON: {e}")
        
        # Create HTML page
        print(f"🔄 Creating HTML page: {html_filename}")
        try:
            html_content = create_html_page(unique_data, margin, files_created, country, config)
            
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ HTML page created: {html_filename}")
            
            # Verify file was actually created
            if os.path.exists(html_filename):
                size = os.path.getsize(html_filename)
                print(f"✅ HTML file verified: {html_filename} ({size} bytes)")
            else:
                print(f"❌ HTML file NOT found after creation: {html_filename}")
            
        except Exception as e:
            print(f"❌ Error creating HTML: {e}")
            import traceback
            traceback.print_exc()
            
            # Create simple fallback
            print("🔄 Creating fallback HTML...")
            try:
                simple_html = f"""<!DOCTYPE html>
<html><head><title>Feed Kaufland {config['name']}</title></head>
<body>
<h1>Feed Kaufland - {len(unique_data)} Prodotti</h1>
<p>Paese: {config['name']} ({country})</p>
<p>Valuta: {currency_info['currency']}</p>
<p>Prezzo max: {currency_info['currency']}{max_price_limit:.2f}</p>
<p>Volume max: {max_content_volume:,} cm³</p>
<p>URL Feed: <a href="{filename}">{filename}</a></p>
</body></html>"""
                with open(html_filename, 'w', encoding='utf-8') as f:
                    f.write(simple_html)
                print(f"✅ Simple HTML created: {html_filename}")
            except Exception as e2:
                print(f"❌ Even fallback HTML failed: {e2}")
        
        # Final file check
        print("🔧 DEBUG: Final file check:")
        print(f"   CSV exists: {os.path.exists(filename)}")
        print(f"   HTML exists: {os.path.exists(html_filename)}")  
        print(f"   JSON exists: {os.path.exists(info_filename)}")
        
        # List all files in current directory
        print("🔧 DEBUG: All files in current directory:")
        import glob
        all_files = glob.glob("*")
        for file in sorted(all_files):
            if os.path.isfile(file):
                print(f"   {file} ({os.path.getsize(file)} bytes)")
        
        # Stats
        prices = [row['price_cs'] for row in unique_data]
        quantities = [row['quantity'] for row in unique_data]
        volumes = [row['content_volume'] for row in unique_data]
        
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        avg_quantity = sum(quantities) / len(quantities) if quantities else 0
        max_volume = max(volumes) if volumes else 0
        
        print("✅ SUCCESSO!")
        country_name = config['name']
        country_locale = config['locale']
        print(f"📁 Creato {filename} con {len(unique_data):,} prodotti per {country_name}")
        print(f"📡 URL: https://poppulseemporium.github.io/kaufland-feed/{filename}")
        print(f"💰 Gamma prezzi: {currency_info['currency']}{min_price:.2f} - {currency_info['currency']}{max_price:.2f}")
        print(f"📦 Quantità media: {avg_quantity:.1f} unità")
        print(f"📏 Volume massimo: {max_volume:,.0f} cm³")
        print(f"🌍 Configurato per: {country_name} ({country_locale}) - {currency_info['currency']}")
        
    else:
        print("❌ Nessun prodotto da esportare")

if __name__ == "__main__":
    main()
