import requests
import json
import pandas as pd
from typing import Dict, List, Optional
import time
import os
from datetime import datetime

class BigBuyAPI:
    def __init__(self, api_key: str, base_url: str = "https://api.bigbuy.eu"):
        """Initialize BigBuy API client"""
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            
            print(f"Request: {endpoint} - Status: {response.status_code}")
            
            if response.status_code == 401:
                print("❌ Authentication Error: Please check your API key")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            return None

    def _filter_erotic_categories(self, taxonomies: List[Dict]) -> List[Dict]:
        """Filter out erotic/adult content categories"""
        erotic_keywords = [
            'erotic', 'erotico', 'adult', 'adulto', 'sex', 'sesso', 'sexy', 
            'intimate', 'intimo', 'lingerie', 'pleasure', 'piacere',
            'sensual', 'sensuale', 'mature', 'maturo', 'xxx'
        ]
        
        filtered_taxonomies = []
        for taxonomy in taxonomies:
            taxonomy_name = taxonomy.get('name', '').lower()
            taxonomy_url = taxonomy.get('url', '').lower()
            
            is_erotic = any(keyword in taxonomy_name or keyword in taxonomy_url 
                          for keyword in erotic_keywords)
            
            if not is_erotic:
                filtered_taxonomies.append(taxonomy)
            else:
                print(f"🚫 Filtered out: {taxonomy['name']}")
        
        return filtered_taxonomies

    def get_taxonomies(self, first_level_only: bool = True) -> List[Dict]:
        """Get product taxonomies (categories)"""
        endpoint = "/rest/catalog/taxonomies.json"
        if first_level_only:
            endpoint += "?firstLevel"
        
        result = self._make_request(endpoint)
        if result:
            result = self._filter_erotic_categories(result)
        return result

    def get_products_by_taxonomy(self, taxonomy_id: int) -> List[Dict]:
        """Get products for a specific taxonomy"""
        endpoint = f"/rest/catalog/products.json?parentTaxonomy={taxonomy_id}"
        return self._make_request(endpoint)

    def get_product_information(self, taxonomy_id: int, iso_code: str = "it") -> List[Dict]:
        """Get product information (names, descriptions) for a taxonomy"""
        endpoint = f"/rest/catalog/productsinformation.json?isoCode={iso_code}&parentTaxonomy={taxonomy_id}"
        return self._make_request(endpoint)

    def get_product_images(self, taxonomy_id: int) -> List[Dict]:
        """Get product images for a taxonomy"""
        endpoint = f"/rest/catalog/productsimages.json?parentTaxonomy={taxonomy_id}"
        return self._make_request(endpoint)

    def retrieve_catalog_data(self, language: str = "it", max_categories: int = 10) -> Dict:
        """Retrieve BigBuy catalog data (optimized for GitHub Actions)"""
        print("🔄 Starting catalog retrieval...")
        
        catalog = {
            'products': [],
            'product_information': [],
            'images': []
        }
        
        # Get taxonomies
        taxonomies = self.get_taxonomies(first_level_only=True)
        if not taxonomies:
            print("❌ Failed to retrieve taxonomies")
            return catalog
        
        # Limit categories for GitHub Actions (to avoid timeout)
        taxonomies = taxonomies[:max_categories]
        print(f"📊 Processing {len(taxonomies)} categories...")
        
        for i, taxonomy in enumerate(taxonomies):
            taxonomy_id = taxonomy['id']
            taxonomy_name = taxonomy['name']
            
            print(f"📦 Processing {i+1}/{len(taxonomies)}: {taxonomy_name}")
            
            # Get products
            products = self.get_products_by_taxonomy(taxonomy_id)
            if products:
                catalog['products'].extend(products)
                print(f"   ✅ {len(products)} products")
            
            # Get product information
            product_info = self.get_product_information(taxonomy_id, language)
            if product_info:
                catalog['product_information'].extend(product_info)
                print(f"   ✅ {len(product_info)} descriptions")
            
            # Get images
            images = self.get_product_images(taxonomy_id)
            if images:
                catalog['images'].extend(images)
                print(f"   ✅ {len(images)} image sets")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        print(f"✅ Catalog retrieval complete!")
        print(f"📊 Total: {len(catalog['products'])} products, {len(catalog['product_information'])} descriptions")
        
        return catalog

    def process_for_kaufland(self, catalog: Dict, margin: float = 0.20) -> pd.DataFrame:
        """Process catalog data for Kaufland marketplace"""
        print("🔄 Processing data for Kaufland...")
        
        try:
            # Convert to DataFrames
            products_df = pd.DataFrame(catalog['products'])
            product_info_df = pd.DataFrame(catalog['product_information'])
            images_df = pd.DataFrame(catalog['images'])
            
            if products_df.empty:
                print("❌ No products to process")
                return pd.DataFrame()
            
            # Filter NEW condition only
            products_new = products_df[products_df['condition'].str.upper() == 'NEW']
            print(f"📦 {len(products_new)} NEW products found")
            
            # Merge with product information
            merged_df = products_new.merge(product_info_df, on='sku', how='left')
            
            # Process images
            if not images_df.empty:
                # Flatten images
                images_flat = []
                for _, row in images_df.iterrows():
                    product_id = row['id']
                    if isinstance(row.get('images'), list):
                        for i, img in enumerate(row['images'][:4]):  # Max 4 images
                            images_flat.append({
                                'product_id': product_id,
                                f'IMAGE{i+1}': img.get('url', '') if isinstance(img, dict) else ''
                            })
                
                if images_flat:
                    images_pivot = pd.DataFrame(images_flat).groupby('product_id').first().reset_index()
                    merged_df = merged_df.merge(images_pivot, left_on='id', right_on='product_id', how='left')
            
            # Create Kaufland format
            output_df = pd.DataFrame()
            output_df['id_offer'] = merged_df['id']
            output_df['ean'] = merged_df['ean13']
            output_df['locale'] = 'it-IT'
            output_df['category'] = "Gardening & DIY"
            output_df['title'] = merged_df['name']
            output_df['short_description'] = merged_df['description'].astype(str).str[:200] + "..."
            output_df['description'] = merged_df['description']
            output_df['manufacturer'] = "Pop Pulse Emporium"
            
            # Images
            output_df['picture_1'] = merged_df.get('IMAGE1', '')
            output_df['picture_2'] = merged_df.get('IMAGE2', '')
            output_df['picture_3'] = merged_df.get('IMAGE3', '')
            output_df['picture_4'] = merged_df.get('IMAGE4', '')
            
            # Pricing (wholesale * (1 + VAT) * (1 + margin) + base_price)
            VAT = 0.22
            base_price = 0.75
            output_df['price_cs'] = (merged_df['wholesalePrice'].astype(float) * 
                                   (1 + VAT) * (1 + margin) + base_price).round(2)
            
            # Product details
            output_df['quantity'] = 100  # Default stock
            output_df['condition'] = 'NEW'
            output_df['length'] = merged_df['depth'].fillna(0)
            output_df['width'] = merged_df['width'].fillna(0)
            output_df['height'] = merged_df['height'].fillna(0)
            output_df['weight'] = merged_df['weight'].fillna(0)
            output_df['content_volume'] = (output_df['length'] * output_df['width'] * output_df['height']).fillna(0)
            output_df['currency'] = 'EUR'
            output_df['handling_time'] = 2
            output_df['delivery_time_max'] = 5
            output_df['delivery_time_min'] = 3
            
            # Clean up
            output_df = output_df.fillna('')
            output_df = output_df.drop_duplicates(subset=['ean'], keep='first')
            
            print(f"✅ Processed {len(output_df)} products for Kaufland")
            print(f"💰 Price range: €{output_df['price_cs'].min():.2f} - €{output_df['price_cs'].max():.2f}")
            
            return output_df
            
        except Exception as e:
            print(f"❌ Error processing for Kaufland: {e}")
            return pd.DataFrame()

def main():
    """Main function for GitHub Actions"""
    print("🚀 Starting BigBuy to Kaufland sync...")
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get API key from environment
    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ BIGBUY_API_KEY environment variable not set")
        return
    
    # Initialize API
    api = BigBuyAPI(api_key)
    
    # Configuration
    margin = 0.20  # 20% margin
    max_categories = 15  # Limit for GitHub Actions
    
    try:
        # Step 1: Retrieve catalog
        catalog = api.retrieve_catalog_data(language="it", max_categories=max_categories)
        
        # Step 2: Process for Kaufland
        kaufland_df = api.process_for_kaufland(catalog, margin=margin)
        
        if not kaufland_df.empty:
            # Step 3: Save to CSV
            kaufland_df.to_csv('kaufland_feed.csv', index=False, encoding='utf-8')
            
            # Step 4: Create info file
            info = {
                "last_updated": datetime.now().isoformat(),
                "product_count": len(kaufland_df),
                "margin_applied": f"{margin*100}%",
                "categories_processed": max_categories,
                "price_range": {
                    "min": f"€{kaufland_df['price_cs'].min():.2f}",
                    "max": f"€{kaufland_df['price_cs'].max():.2f}"
                }
            }
            
            with open('feed_info.json', 'w') as f:
                json.dump(info, f, indent=2)
            
            print("✅ SUCCESS!")
            print(f"📁 Created kaufland_feed.csv with {len(kaufland_df)} products")
            print(f"💰 Applied {margin*100}% margin")
            print(f"🌐 Feed will be available at: https://[your-username].github.io/kaufland-feed/kaufland_feed.csv")
            
        else:
            print("❌ No products processed")
            
    except Exception as e:
        print(f"❌ Error in main process: {e}")
        raise

if __name__ == "__main__":
    main()
