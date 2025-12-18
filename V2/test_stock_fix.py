"""
Test the stock filtering fix
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Simulated stock data from API (like what we saw for EAN 4711387067246)
test_stock_data = [
    {
        "id": 1248195,
        "sku": "S0469229",
        "stocks": [
            {"quantity": 0, "minHandlingDays": 0, "maxHandlingDays": 1, "warehouse": 1},
            {"quantity": 20, "minHandlingDays": 1, "maxHandlingDays": 2, "warehouse": 1}
        ]
    },
    {
        "sku": "TEST001",
        "stocks": [
            {"quantity": 10, "minHandlingDays": 0, "maxHandlingDays": 1, "warehouse": 1},
            {"quantity": 50, "minHandlingDays": 2, "maxHandlingDays": 3, "warehouse": 1}
        ]
    },
    {
        "sku": "TEST002",
        "stocks": [
            {"quantity": 5, "minHandlingDays": 0, "maxHandlingDays": 0, "warehouse": 1},
        ]
    }
]

def build_stock_map_OLD(stock_data):
    """Old method - sums ALL stock"""
    product_stock = {}
    for item in stock_data:
        sku = item.get('sku')
        if sku:
            total = sum(s.get('quantity', 0) for s in item.get('stocks', []))
            product_stock[sku] = total
    return product_stock

def build_stock_map_NEW(stock_data, max_handling_days=1):
    """New method - only counts stock within handling days"""
    product_stock = {}
    for item in stock_data:
        sku = item.get('sku')
        if sku:
            total = sum(
                s.get('quantity', 0)
                for s in item.get('stocks', [])
                if s.get('maxHandlingDays', 999) <= max_handling_days
            )
            product_stock[sku] = total
    return product_stock

def calculate_safe_quantity(bigbuy_stock: int) -> int:
    """Safety buffer calculation"""
    if bigbuy_stock <= 0:
        return 0
    elif bigbuy_stock <= 2:
        return 1
    elif bigbuy_stock <= 5:
        return min(2, bigbuy_stock - 1)
    elif bigbuy_stock <= 10:
        return min(5, bigbuy_stock - 2)
    elif bigbuy_stock <= 20:
        return min(10, bigbuy_stock - 3)
    elif bigbuy_stock <= 50:
        return min(25, bigbuy_stock - 5)
    else:
        return min(50, int(bigbuy_stock * 0.9))

print("="*80)
print("STOCK FILTERING TEST - OLD vs NEW")
print("="*80)

# Test with OLD method
print("\n📊 OLD METHOD (sum all stock regardless of handling days):")
print("-"*80)
old_stock = build_stock_map_OLD(test_stock_data)

for sku, raw_stock in old_stock.items():
    safe_stock = calculate_safe_quantity(raw_stock)
    print(f"SKU {sku}: Raw={raw_stock}, Safe={safe_stock}")

# Test with NEW method (0-1 day handling)
print("\n📊 NEW METHOD (max_handling_days=1, immediate stock only):")
print("-"*80)
new_stock_1day = build_stock_map_NEW(test_stock_data, max_handling_days=1)

for sku, raw_stock in new_stock_1day.items():
    safe_stock = calculate_safe_quantity(raw_stock)
    old_raw = old_stock.get(sku, 0)
    old_safe = calculate_safe_quantity(old_raw)
    change = "✓ FIXED" if raw_stock != old_raw else "unchanged"
    print(f"SKU {sku}: Raw={raw_stock} (was {old_raw}), Safe={safe_stock} (was {old_safe}) - {change}")

# Test with 2 days
print("\n📊 NEW METHOD (max_handling_days=2, fast stock):")
print("-"*80)
new_stock_2day = build_stock_map_NEW(test_stock_data, max_handling_days=2)

for sku, raw_stock in new_stock_2day.items():
    safe_stock = calculate_safe_quantity(raw_stock)
    print(f"SKU {sku}: Raw={raw_stock}, Safe={safe_stock}")

print("\n" + "="*80)
print("SPECIFIC CASE: EAN 4711387067246 (SKU S0469229)")
print("="*80)

target_sku = "S0469229"
old_raw = old_stock.get(target_sku, 0)
new_raw = new_stock_1day.get(target_sku, 0)
old_safe = calculate_safe_quantity(old_raw)
new_safe = calculate_safe_quantity(new_raw)

print(f"\nBigBuy Website Shows: 0 (immediate stock only)")
print(f"Old Method Raw Stock: {old_raw} (0-1 day: 0 + 1-2 day: 20)")
print(f"Old Method Safe Stock: {old_safe}")
print(f"New Method Raw Stock: {new_raw} (0-1 day only)")
print(f"New Method Safe Stock: {new_safe}")
print(f"\n{'✅ MATCHES BigBuy website!' if new_raw == 0 else '❌ Still does not match'}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
