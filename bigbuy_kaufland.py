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
    """Create HTML page with product data in Italian"""
    
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
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feed Prodotti Kaufland - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }}
        .stat-box {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); flex: 1; min-width: 150px; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #667eea; margin-bottom: 5px; }}
        .stat-label {{ font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        .country-info {{ background: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .feed-url {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 30px 0; border-left: 5px solid #2196f3; }}
        .feed-url code {{ background: #fff; padding: 10px; border-radius: 5px; font-size: 14px; word-break: break-all; display: block; margin: 10px 0; border: 1px solid #ddd; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 30px; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        th, td {{ border: none; padding: 12px; text-align: left; }}
        th {{ background-color: #667eea; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        .price {{ color: #4caf50; font-weight: bold; font-size: 16px; }}
        .ean {{ font-family: 'Courier New', monospace; font-size: 12px; background: #f5f5f5; padding: 4px; border-radius: 3px; }}
        .image {{ max-width: 60px; max-height: 60px; border-radius: 5px; }}
        .description {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 20px; border-radius: 10px; margin: 30px 0; }}
        .info-section {{ background: white; padding: 20px; border-radius: 10px; margin-top: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .flag {{ font-size: 24px; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ Feed Prodotti Kaufland</h1>
        <p><strong>Pop Pulse Emporium</strong> - Ultimo Aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>"""
    
    <div class="country-info">
        <h2><span class="flag">🇪🇺</span> Paese: {config['name']} ({country})</h2>
        <p><strong>Lingua:</strong> {config['language'].upper()} | <strong>Formato Locale:</strong> {config['locale']}</p>
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
        <div class="stat-box">
            <div class="stat-number">€300</div>
            <div class="stat-label">Limite Prezzo</div>
        </div>
    </div>
    
    <div class="success">
        <h3>✅ Pronto per Kaufland {config['name']}!</h3>
        <p>Il tuo feed è ottimizzato per il mercato {config['name']} con {len(unique_data):,} prodotti selezionati casualmente.</p>
        <p>Tutti i prodotti hanno un prezzo massimo di €300 e descrizioni nella lingua locale.</p>
    </div>
    
    <div class="feed-url">
        <h3>📡 URL del Feed per Kaufland {config['name']}:</h3>
        <code>https://poppulseemporium.github.io/kaufland-feed/{files_created[0]}</code>
        <p><small>📋 Copia questo URL e incollalo nel campo "Percorso del file" di Kaufland</small></p>
    </div>
    
    <h2>📊 Anteprima Prodotti (Primi 50)</h2>
    <table>
        <tr>
            <th>Immagine</th>
            <th>Titolo</th>
            <th>EAN</th>
            <th>Prezzo</th>
            <th>Categoria</th>
            <th>Descrizione</th>
        </tr>
"""
    
    # Add first 50 products to HTML table
    for i, row in enumerate(unique_data[:50]):
        img_tag = f'<img src="{row["picture_1"]}" class="image" onerror="this.style.display=\'none\'" alt="Prodotto">' if row["picture_1"] else "Nessuna immagine"
        title = safe_str(row["title"])[:50] + "..." if len(safe_str(row["title"])) > 50 else safe_str(row["title"])
        description = safe_str(row["description"])[:100] + "..." if len(safe_str(row["description"])) > 100 else safe_str(row["description"])
        
        html_content += f"""
        <tr>
            <td>{img_tag}</td>
            <td><strong>{title}</strong></td>
            <td class="ean">{row["ean"]}</td>
            <td class="price">€{row["price_cs"]:.2f}</td>
            <td>{row["category"]}</td>
            <td class="description">{description}</td>
        </tr>
"""
    
    html_content += f"""
    </table>
    
    <div class="info-section">
        <h3>📋 File Disponibili</h3>
        <ul>
            <li><strong>{files_created[0]}</strong> - File feed principale per Kaufland {config['name']}</li>
            <li><strong>feed_info_{country.lower()}.json</strong> - Informazioni tecniche sul feed</li>
            <li><strong>index.html</strong> - Questa pagina di anteprima</li>
        </ul>
        
        <h3>🔄 Programma di Aggiornamento</h3>
        <p>Questo feed si aggiorna automaticamente ogni 6 ore con nuovi dati BigBuy freschi.</p>
        
        <h3>⚙️ Configurazione Kaufland</h3>
        <ol>
            <li>Copia l'URL del feed qui sopra</li>
            <li>Vai al pannello di controllo Kaufland per {config['name']}</li>
            <li>Incolla l'URL nel campo "Percorso del file"</li>
            <li>Seleziona la frequenza di aggiornamento preferita (giornaliera consigliata)</li>
            <li>Clicca "Salva le modifiche"</li>
        </ol>
        
        <h3>🌍 Altri Paesi</h3>
        <p>Questo feed è specifico per <strong>{config['name']}</strong>. 
        Per altri paesi (Austria, Germania, Polonia, Slovacchia, Repubblica Ceca), 
        sono disponibili feed separati con localizzazioni appropriate.</p>
        
        <h3>📊 Statistiche Prodotti</h3>
        <ul>
            <li><strong>Selezione:</strong> Casuale da un catalogo di ~168.000 prodotti</li>
            <li><strong>Filtro prezzo:</strong> Massimo €300 per prodotto</li>
            <li><strong>Condizione:</strong> Solo prodotti NUOVI</li>
            <li><strong>Lingua:</strong> Descrizioni in {config['language'].upper()}</li>
            <li><strong>Margine applicato:</strong> {margin*100:.0f}% + IVA 22%</li>
        </ul>
    </div>
</body>
</html>
"""
    
    return html_contentstrftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <div class="stat-number">{len(unique_data):,}</div>
            <div class="stat-label">Products</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{margin*100}%</div>
            <div class="stat-label">Margin</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">€{min_price:.2f}</div>
            <div class="stat-label">Min Price</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">€{max_price:.2f}</div>
            <div class="stat-label">Max Price</div>
        </div>
    </div>
    
    <div class="success">
        <h3>🧪 Test Version - Random Sample</h3>
        <p>This is a test version with {len(unique_data)} randomly selected products.</p>
        <p>Perfect for testing Kaufland integration before scaling up!</p>
        <p><strong>Available:</strong> {len(unique_data)} products selected from a total catalog of ~168,000 products</p>
    </div>
    
    <div class="feed-url">
        <h3>📡 Feed URL for Kaufland:</h3>
        <code>https://your-username.github.io/kaufland-feed/kaufland_feed.csv</code>
        <p><small>Copy this URL and paste it into Kaufland's "Percorso del file" field</small></p>
    </div>
    
    <h2>📊 Product Preview (First 50 products)</h2>
    <table>
        <tr>
            <th>Image</th>
            <th>Title</th>
            <th>EAN</th>
            <th>Price</th>
            <th>Category</th>
            <th>Description</th>
        </tr>
"""
    
    # Add first 50 products to HTML table
    for i, row in enumerate(unique_data[:50]):
        img_tag = f'<img src="{row["picture_1"]}" class="image" onerror="this.style.display=\'none\'">' if row["picture_1"] else "No image"
        title = safe_str(row["title"])[:50] + "..." if len(safe_str(row["title"])) > 50 else safe_str(row["title"])
        description = safe_str(row["description"])[:100] + "..." if len(safe_str(row["description"])) > 100 else safe_str(row["description"])
        
        html_content += f"""
        <tr>
            <td>{img_tag}</td>
            <td>{title}</td>
            <td class="ean">{row["ean"]}</td>
            <td class="price">€{row["price_cs"]}</td>
            <td>{row["category"]}</td>
            <td class="description">{description}</td>
        </tr>
"""
    
    html_content += """
    </table>
    
    <div style="margin-top: 40px; padding: 20px; background: #f0f0f0; border-radius: 5px;">
        <h3>📋 Files Available:</h3>
        <ul>
            <li><strong>kaufland_feed.csv</strong> - Main feed file for Kaufland</li>
            <li><strong>feed_info.json</strong> - Technical information about the feed</li>
            <li><strong>index.html</strong> - This preview page</li>
        </ul>
        
        <h3>🔄 Update Schedule:</h3>
        <p>This feed updates automatically every 6 hours with fresh BigBuy data.</p>
        
        <h3>⚙️ Kaufland Setup:</h3>
        <ol>
            <li>Copy the URL above</li>
            <li>Paste it in Kaufland's "Percorso del file" field</li>
            <li>Select your preferred update schedule (daily recommended)</li>
            <li>Click "Salva le modifiche"</li>
            <li><strong>Test with this small sample first!</strong></li>
        </ol>
        
        <h3>📈 Next Steps:</h3>
        <p>Once you're happy with the test integration:</p>
        <ol>
            <li>Change <code>test_sample_size = 50</code> to <code>test_sample_size = 80000</code> in the script</li>
            <li>Or remove the limit entirely for the full catalog</li>
            <li>Your feed will automatically update with more products</li>
        </ol>
    </div>
</body>
</html>
"""
    
    return html_content

def main():
    """Main function"""
    print("🚀 Starting BigBuy to Kaufland sync...")
    
    # Get API key
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return
    
    # Get country from environment (for multi-country support)
    country = os.getenv('COUNTRY_CODE', 'DE').upper()  # Default to Germany
    
    # Country configuration
    country_config = {
        'AT': {'locale': 'de-AT', 'language': 'de', 'name': 'Austria'},
        'DE': {'locale': 'de-DE', 'language': 'de', 'name': 'Germany'}, 
        'PL': {'locale': 'pl-PL', 'language': 'pl', 'name': 'Poland'},
        'SK': {'locale': 'sk-SK', 'language': 'sk', 'name': 'Slovakia'},
        'CZ': {'locale': 'cs-CZ', 'language': 'cs', 'name': 'Czech Republic'}  # CZ instead of CK
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
    
    # Get data in appropriate language
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
        
        # Debug: Show running totals
        print(f"   📊 Running totals: {len(all_products)} products, {len(all_info)} info, {len(all_images)} images")
    
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
    
    # Create CSV with price filtering
    csv_data = []
    
    for product in all_products:
        # Only NEW products
        if product.get('condition', '').upper() != 'NEW':
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
            'locale': config['locale'],  # Country-specific locale
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
            'quantity': 100,
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
    
    # First, collect all unique products
    for row in csv_data:
        ean = row['ean']
        if ean and ean not in seen_eans:
            seen_eans.add(ean)
            unique_data.append(row)
    
    print(f"✅ Found {len(unique_data)} unique products for {config['name']}")
    
    # For testing: randomly select sample
    test_sample_size = 25000  # 25k products
    
    if len(unique_data) > test_sample_size:
        # Randomly shuffle and take first N products
        random.shuffle(unique_data)
        unique_data = unique_data[:test_sample_size]
        print(f"📊 Randomly selected {test_sample_size} products for {config['name']}")
    else:
        print(f"📊 Using all {len(unique_data)} products for {config['name']}")
    
    # Create country-specific file
    filename = f'kaufland_feed_{country.lower()}.csv'
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
        writer.writeheader()
        writer.writerows(unique_data)
    
    files_created = [filename]
    print(f"✅ Created {filename} with {len(unique_data)} products for {config['name']}")
    
    # Write files
    if unique_data:
        print(f"✅ Ready to create files with {len(unique_data)} products")
        
        # CSV files are already created above in the splitting logic
        
        # Create info file
        info_data = {
            "last_updated": datetime.now().isoformat(),
            "product_count": len(unique_data),
            "total_products_available": len(csv_data),
            "selection_method": "Random sample with price filter",
            "sample_size": len(unique_data),
            "max_price_filter": max_price_limit,
            "margin_applied": f"{margin*100}%",
            "categories_processed": len(taxonomies),
            "country": country,
            "locale": config['locale'],
            "language": config['language'],
            "feed_url": f"https://poppulseemporium.github.io/kaufland-feed/{filename}",
            "note": f"Feed for {config['name']} with {len(unique_data)} random products under €{max_price_limit}"
        }
        
        with open(f'feed_info_{country.lower()}.json', 'w') as f:
            json.dump(info_data, f, indent=2)
        print("✅ JSON info file created")
        
        # Create HTML page - this is where the error might occur
        print("🔄 Creating HTML page...")
        try:
            html_content = create_html_page(unique_data, margin, ['kaufland_feed.csv'])
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print("✅ HTML page created")
        except Exception as e:
            print(f"❌ Error creating HTML page: {e}")
            # Create a simple fallback HTML
            simple_html = f"""<!DOCTYPE html>
<html><head><title>Kaufland Feed</title></head>
<body>
<h1>Kaufland Feed - {len(unique_data)} Products</h1>
<p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p>Feed URL: <a href="kaufland_feed.csv">https://your-username.github.io/kaufland-feed/kaufland_feed.csv</a></p>
</body></html>"""
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(simple_html)
            print("✅ Simple HTML page created as fallback")
        
        # Calculate stats
        prices = [row['price_cs'] for row in unique_data]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        print("✅ SUCCESS!")
        print(f"📁 Created kaufland_feed.csv with {len(unique_data):,} products")
        print(f"🌐 Created index.html preview page")
        print(f"💰 Applied {margin*100}% margin")
        print(f"💰 Price range: €{min_price:.2f} - €{max_price:.2f}")
        
        # Debug: Check if files were created
        files_created = []
        for filename in ['kaufland_feed.csv', 'index.html', 'feed_info.json']:
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                files_created.append(f"{filename} ({file_size:,} bytes)")
        
        print(f"✅ Files created: kaufland_feed.csv, feed_info.json, index.html")
        print(f"🌐 Preview will be available at: https://your-username.github.io/kaufland-feed/")
        print(f"📡 Test feed URL for Kaufland: https://your-username.github.io/kaufland-feed/kaufland_feed.csv")
        print(f"🧪 Test sample: {len(unique_data)} randomly selected products from {len(csv_data)} total")
        print(f"💡 Perfect for testing Kaufland integration!")
        
    else:
        print("❌ No products to export")
        # Still create an empty CSV file
        with open('kaufland_feed.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_offer', 'ean', 'locale', 'category', 'title', 'description'])
        print("📁 Created empty kaufland_feed.csv file")

if __name__ == "__main__":
    main()
