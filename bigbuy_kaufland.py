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

def create_html_page(unique_data, margin, files_created, country, config):
    """Create HTML page with product data"""
    
    print(f"🔄 Creating HTML for {len(unique_data)} products...")
    
    # Safety check
    if not unique_data:
        print("❌ No data to create HTML page")
        return "<html><body><h1>Nessun prodotto disponibile</h1></body></html>"
    
    # Calculate price range safely
    try:
        prices = [row['price_cs'] for row in unique_data if 'price_cs' in row and row['price_cs']]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        print(f"💰 Price range calculated: €{min_price:.2f} - €{max_price:.2f}")
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
        <p><strong>Lingua:</strong> {config['language'].upper()} | <strong>Locale:</strong> {config['locale']}</p>
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
            <div class="stat-number">€{min_price:.2f}</div>
            <div class="stat-label">Prezzo Min</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">€{max_price:.2f}</div>
            <div class="stat-label">Prezzo Max</div>
        </div>
    </div>
    
    <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 30px 0;">
        <h3>✅ Pronto per Kaufland {config['name']}!</h3>
        <p>Feed ottimizzato per {config['name']} con {len(unique_data):,} prodotti (max €300 ciascuno).</p>
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
            <th>Titolo</th>
            <th>EAN</th>
            <th>Prezzo</th>
            <th>Descrizione</th>
        </tr>"""
    
    # Add first 50 products to table
    for i, row in enumerate(unique_data[:50]):
        img_url = row.get("picture_1", "")
        img_tag = f'<img src="{img_url}" class="image" alt="Prodotto">' if img_url else "No img"
        
        title = safe_str(row.get("title", ""))[:50]
        if len(title) > 47:
            title += "..."
            
        ean = safe_str(row.get("ean", ""))
        price = row.get("price_cs", 0)
        description = safe_str(row.get("description", ""))[:100]
        if len(description) > 97:
            description += "..."
        
        html_content += f"""
        <tr>
            <td>{img_tag}</td>
            <td><strong>{title}</strong></td>
            <td>{ean}</td>
            <td class="price">€{price:.2f}</td>
            <td>{description}</td>
        </tr>"""
    
    # Close the HTML
    html_content += """
    </table>
    
    <div style="background: white; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3>📋 Informazioni</h3>
        <ul>
            <li><strong>Aggiornamento:</strong> Ogni 6 ore automaticamente</li>
            <li><strong>Selezione:</strong> Casuale dal catalogo BigBuy</li>
            <li><strong>Filtro prezzo:</strong> Massimo €300 per prodotto</li>
            <li><strong>Filtro stock:</strong> Minimo 2 unità disponibili</li>
            <li><strong>Condizione:</strong> Solo prodotti NUOVI</li>
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
    print(f"🌍 Processing for {config['name']} ({country})")
    
    api = BigBuyAPI(api_key)
    
    # Configuration
    margin = 0.20
    vat = 0.22
    base_price = 0.75
    max_price_limit = 300.0  # Maximum price filter
    sample_size = 25000  # 25k products per country
    stock_minimum = 2  # Minimum stock required
    
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
        
        # Calculate price
        wholesale = safe_float(product.get('wholesalePrice', 0))
        price = round((wholesale * (1 + vat) * (1 + margin)) + base_price, 2)
        
        # Filter by maximum price
        if price > max_price_limit:
            continue
        
        # Create row with country-specific locale
        row = {
            'id_offer': str(product_id),
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
            'price_cs': price,
            'quantity': min(100, int(stock_quantity)),  # Use actual stock, max 100
            'condition': 'NEW',
            'length': round(safe_float(product.get('depth')), 2),
            'width': round(safe_float(product.get('width')), 2),
            'height': round(safe_float(product.get('height')), 2),
            'weight': round(safe_float(product.get('weight')), 2),
            'content_volume': round(safe_float(product.get('width')) * safe_float(product.get('height')) * safe_float(product.get('depth')), 2),
            'currency': 'EUR',
            'handling_time': 2,
            'delivery_time_max': 5,
            'delivery_time_min': 3
        }
        
        csv_data.append(row)
    
    print(f"✅ Created {len(csv_data)} products under €{max_price_limit} for {config['name']}")
    
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
    
    # Write files
    if unique_data:
        # Create country-specific CSV file
        if country == 'IT':
            filename = 'kaufland_feed.csv'  # Keep Italy as main file
        else:
            filename = f'kaufland_feed_{country.lower()}.csv'
            
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
            writer.writeheader()
            writer.writerows(unique_data)
        
        files_created = [filename]
        print(f"✅ Created {filename} with {len(unique_data)} products")
        
        # Create info file
        if country == 'IT':
            info_filename = 'feed_info.json'
        else:
            info_filename = f'feed_info_{country.lower()}.json'
            
        info_data = {
            "last_updated": datetime.now().isoformat(),
            "product_count": len(unique_data),
            "total_products_available": len(csv_data),
            "max_price_filter": max_price_limit,
            "stock_minimum": stock_minimum,
            "margin_applied": f"{margin*100}%",
            "country": country,
            "locale": config['locale'],
            "language": config['language'],
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}"
        }
        
        with open(info_filename, 'w') as f:
            json.dump(info_data, f, indent=2)
        print("✅ JSON info file created")
        
        # Create HTML page
        print("🔄 Creating HTML page...")
        try:
            html_content = create_html_page(unique_data, margin, files_created, country, config)
            
            # Create country-specific HTML filename
            if country == 'IT':
                html_filename = 'index.html'  # Keep Italy as main page
            else:
                html_filename = f'index_{country.lower()}.html'
            
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"✅ HTML page created: {html_filename}")
            
        except Exception as e:
            print(f"❌ Error creating HTML: {e}")
            # Create simple fallback
            html_filename = f'index_{country.lower()}.html' if country != 'IT' else 'index.html'
            simple_html = f"""<!DOCTYPE html>
<html><head><title>Feed Kaufland {config['name']}</title></head>
<body>
<h1>Feed Kaufland - {len(unique_data)} Prodotti</h1>
<p>Paese: {config['name']} ({country})</p>
<p>URL Feed: <a href="{filename}">{filename}</a></p>
</body></html>"""
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(simple_html)
            print(f"✅ Simple HTML created: {html_filename}")
        
        # Stats
        prices = [row['price_cs'] for row in unique_data]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        print("✅ SUCCESSO!")
        country_name = config['name']
        country_locale = config['locale']
        print(f"📁 Creato {filename} con {len(unique_data):,} prodotti per {country_name}")
        print(f"📡 URL: https://poppulseemporium.github.io/kaufland-feed/{filename}")
        print(f"💰 Gamma prezzi: €{min_price:.2f} - €{max_price:.2f} (max €{max_price_limit})")
        print(f"🌍 Configurato per: {country_name} ({country_locale})")
        
    else:
        print("❌ Nessun prodotto da esportare")

if __name__ == "__main__":
    main()
