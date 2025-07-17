import requests
import json
import csv
import os
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

    def get_product_info(self, taxonomy_id):
        """Get product descriptions"""
        return self._make_request(f"/rest/catalog/productsinformation.json?isoCode=it&parentTaxonomy={taxonomy_id}")

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

def create_html_page(unique_data, margin):
    """Create HTML page with product data"""
    
    print(f"🔄 Creating HTML for {len(unique_data)} products...")
    
    # Safety check
    if not unique_data:
        print("❌ No data to create HTML page")
        return "<html><body><h1>No products available</h1></body></html>"
    
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
<html>
<head>
    <title>Kaufland Feed - Pop Pulse Emporium</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: #2c5aa0; }}
        .stat-label {{ font-size: 14px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .price {{ color: #2c5aa0; font-weight: bold; }}
        .ean {{ font-family: monospace; font-size: 12px; }}
        .image {{ max-width: 50px; max-height: 50px; }}
        .feed-url {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .feed-url code {{ background: #fff; padding: 5px; border-radius: 3px; font-size: 14px; }}
        .description {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛍️ Kaufland Product Feed</h1>
        <p><strong>Pop Pulse Emporium</strong> - Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
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
    
    <div class="feed-url">
        <h3>📡 Feed URL for Kaufland:</h3>
        <code>https://your-username.github.io/kaufland-feed/kaufland_feed.csv</code>
        <p><small>Use this URL in Kaufland's automatic feed import</small></p>
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
    
    api = BigBuyAPI(api_key)
    
    # Configuration
    margin = 0.20
    vat = 0.22
    base_price = 0.75
    
    # Get data
    taxonomies = api.get_taxonomies()
    if not taxonomies:
        print("❌ No taxonomies found")
        return
    
    print(f"📊 Processing {len(taxonomies)} categories...")
    
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
            
        # Get descriptions
        info = api.get_product_info(tax_id)
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
    
    print(f"✅ Collected {len(all_products)} products")
    
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
    
    # Create CSV
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
        
        # Create row
        row = {
            'id_offer': product_id,
            'ean': safe_str(product.get('ean13')),
            'locale': 'it-IT',
            'category': 'Gardening & DIY',
            'title': safe_str(info.get('name', 'Product')),
            'short_description': safe_str(info.get('description', ''))[:200] + '...',
            'description': safe_str(info.get('description', '')),
            'manufacturer': 'Pop Pulse Emporium',
            'picture_1': images.get('image1', ''),
            'picture_2': images.get('image2', ''),
            'picture_3': images.get('image3', ''),
            'picture_4': images.get('image4', ''),
            'price_cs': price,
            'quantity': 100,
            'condition': 'NEW',
            'length': safe_float(product.get('depth')),
            'width': safe_float(product.get('width')),
            'height': safe_float(product.get('height')),
            'weight': safe_float(product.get('weight')),
            'content_volume': safe_float(product.get('width')) * safe_float(product.get('height')) * safe_float(product.get('depth')),
            'currency': 'EUR',
            'handling_time': 2,
            'delivery_time_max': 5,
            'delivery_time_min': 3
        }
        
        csv_data.append(row)
    
    # Remove duplicates by EAN
    seen_eans = set()
    unique_data = []
    for row in csv_data:
        ean = row['ean']
        if ean and ean not in seen_eans:
            seen_eans.add(ean)
            unique_data.append(row)
    
    print(f"✅ Created {len(unique_data)} unique products")
    
    # Write files
    if unique_data:
        print(f"✅ Ready to create files with {len(unique_data)} products")
        
        # Write CSV
        with open('kaufland_feed.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=unique_data[0].keys())
            writer.writeheader()
            writer.writerows(unique_data)
        print("✅ CSV file created")
        
        # Create info file
        info_data = {
            "last_updated": datetime.now().isoformat(),
            "product_count": len(unique_data),
            "margin_applied": f"{margin*100}%",
            "categories_processed": len(taxonomies)
        }
        
        with open('feed_info.json', 'w') as f:
            json.dump(info_data, f, indent=2)
        print("✅ JSON info file created")
        
        # Create HTML page - this is where the error might occur
        print("🔄 Creating HTML page...")
        try:
            html_content = create_html_page(unique_data, margin)
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
<p>Feed URL: https://your-username.github.io/kaufland-feed/kaufland_feed.csv</p>
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
        
        print(f"✅ Files created: {', '.join(files_created)}")
        print(f"🌐 Preview will be available at: https://your-username.github.io/kaufland-feed/")
        print(f"📡 Feed URL: https://your-username.github.io/kaufland-feed/kaufland_feed.csv")
        
    else:
        print("❌ No products to export")
        # Still create an empty CSV file
        with open('kaufland_feed.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id_offer', 'ean', 'locale', 'category', 'title', 'description'])
        print("📁 Created empty kaufland_feed.csv file")

if __name__ == "__main__":
    main()
