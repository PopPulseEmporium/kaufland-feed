"""
BigBuy Order API Client
Allows programmatic order submission to BigBuy

Based on BigBuy API documentation:
POST /rest/order/order/create

Usage:
    from bigbuy_order_api import BigBuyOrderClient

    client = BigBuyOrderClient(api_key)
    order = client.create_order(
        products=[{'sku': 'S0469229', 'quantity': 2}],
        shipping_address={...},
        reference="MANOMANO-ORDER-123"
    )
"""

import requests
import json
import os
import time
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


@dataclass
class ShippingAddress:
    """Shipping address for order"""
    firstName: str
    lastName: str
    country: str  # ISO code (e.g., 'IT', 'DE')
    postcode: str
    town: str
    address: str
    phone: str
    email: str
    company: Optional[str] = None
    state: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class OrderProduct:
    """Product for order"""
    sku: str
    quantity: int
    reference: Optional[str] = None  # Your internal reference


class BigBuyOrderClient:
    """BigBuy API client for order management"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bigbuy.eu"
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def create_order(
        self,
        products: List[OrderProduct],
        shipping_address: ShippingAddress,
        reference: str,
        language: str = "it",
        shipping_method: Optional[str] = None,
        payment_method: Optional[str] = None,
        incoterm: str = "DDU"  # Delivered Duty Unpaid
    ) -> dict:
        """
        Create an order on BigBuy

        Args:
            products: List of products to order
            shipping_address: Shipping address details
            reference: Your order reference/ID
            language: Language code (default: 'it')
            shipping_method: Specific shipping method (optional)
            payment_method: Payment method (optional)
            incoterm: Incoterm (default: DDU)

        Returns:
            BigBuy order response with order ID
        """

        # Build order payload
        order_data = {
            "reference": reference,
            "language": language,
            "incoterm": incoterm,
            "shippingAddress": {
                "firstName": shipping_address.firstName,
                "lastName": shipping_address.lastName,
                "country": shipping_address.country,
                "postcode": shipping_address.postcode,
                "town": shipping_address.town,
                "address": shipping_address.address,
                "phone": shipping_address.phone,
                "email": shipping_address.email,
            },
            "products": [
                {
                    "sku": p.sku if isinstance(p, OrderProduct) else p['sku'],
                    "quantity": p.quantity if isinstance(p, OrderProduct) else p['quantity'],
                    "reference": p.reference if isinstance(p, OrderProduct) and p.reference else ""
                }
                for p in products
            ]
        }

        # Add optional fields
        if shipping_address.company:
            order_data["shippingAddress"]["company"] = shipping_address.company
        if shipping_address.state:
            order_data["shippingAddress"]["state"] = shipping_address.state
        if shipping_address.comment:
            order_data["shippingAddress"]["comment"] = shipping_address.comment

        if shipping_method:
            order_data["shippingMethod"] = shipping_method
        if payment_method:
            order_data["paymentMethod"] = payment_method

        print(f"\n📦 Creating order: {reference}")
        print(f"   Products: {len(products)}")
        print(f"   Destination: {shipping_address.country}")

        # Submit order
        response = self._request('POST', '/rest/order/order/create.json', order_data)

        print(f"✅ Order created successfully!")
        if 'id' in response:
            print(f"   BigBuy Order ID: {response['id']}")

        return response

    def get_order_status(self, order_id: int) -> dict:
        """Get order status by BigBuy order ID"""
        return self._request('GET', f'/rest/order/{order_id}.json')

    def get_orders(self, since_date: Optional[str] = None) -> List[dict]:
        """
        Get all orders

        Args:
            since_date: Filter orders since date (format: YYYY-MM-DD)

        Returns:
            List of orders
        """
        endpoint = '/rest/order/orders.json'
        if since_date:
            endpoint += f'?isoDateFrom={since_date}'

        return self._request('GET', endpoint)


# Example usage and testing
def example_test_order():
    """Example: Create a test order"""

    api_key = os.getenv('BIGBUY_API_KEY')
    if not api_key:
        print("❌ BIGBUY_API_KEY not set")
        return

    client = BigBuyOrderClient(api_key)

    # Example shipping address (Italy)
    shipping = ShippingAddress(
        firstName="Mario",
        lastName="Rossi",
        country="IT",
        postcode="20121",
        town="Milano",
        address="Via Roma 123",
        phone="+39 02 1234567",
        email="mario.rossi@example.com",
        company="Test Company SRL"
    )

    # Example products
    products = [
        OrderProduct(sku="S0469229", quantity=1, reference="TEST-001")
    ]

    # Create order
    try:
        order = client.create_order(
            products=products,
            shipping_address=shipping,
            reference=f"MANOMANO-TEST-{int(time.time())}"
        )

        print("\n" + "="*70)
        print("ORDER RESPONSE:")
        print("="*70)
        print(json.dumps(order, indent=2))

    except Exception as e:
        print(f"\n❌ Order failed: {e}")


def check_order_capability():
    """Check if we can create orders via API"""

    print("="*70)
    print("BIGBUY ORDER API CAPABILITY CHECK")
    print("="*70)

    api_key = os.getenv('BIGBUY_API_KEY', 'YjEzYWU2YTRkNmQyZTY1MjU5M2IzYjlmN2Q2OTQyMTljMjIxZjE0MTdkZGE1NTRjY2YzMTg3OWExYjllNTUzZQ')
    if not api_key:
        print("❌ BIGBUY_API_KEY not set")
        return

    client = BigBuyOrderClient(api_key)

    # Try to get existing orders (read-only test)
    print("\n1. Testing order list endpoint (GET /rest/order/orders.json)...")
    try:
        orders = client.get_orders()
        print(f"   ✅ Success! Found {len(orders)} existing orders")

        if orders:
            print("\n   Recent order example:")
            print(f"   ID: {orders[0].get('id')}")
            print(f"   Reference: {orders[0].get('reference')}")
            print(f"   Status: {orders[0].get('status')}")

    except Exception as e:
        print(f"   ❌ Failed: {e}")

    print("\n" + "="*70)
    print("RECOMMENDATION:")
    print("="*70)

    print("""
If order API works, you can:

1. Update Config in manomano_feed_generator.py:

   max_handling_days: int = 2  # Include 0-2 day stock

   or even:

   max_handling_days: int = 999  # All stock

2. When ManoMano order comes in:
   - Extract product SKU from your feed
   - Use this script to programmatically order from BigBuy
   - Track order with BigBuy order ID

3. Benefits:
   - More products available (not limited to website stock)
   - Automated order flow
   - Access to all warehouses
""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("⚠️  WARNING: This will create a REAL order on BigBuy!")
        print("Are you sure? (yes/no): ")
        # For safety, don't actually run test
        print("\nFor safety, test mode is disabled.")
        print("To test, modify this script and uncomment the test call.")
        # Uncomment below ONLY when ready to test:
        # example_test_order()
    else:
        check_order_capability()
