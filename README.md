# Kaufland Separated Feeds - Complete Setup Guide

## 🎯 Overview

You now have **TWO separate feed types** that solve your stock issues and translation challenges:

### 📦 Product Feed (Manual Upload)
- **Contains:** EAN, locale, title, description, images, category, dimensions
- **Needs translation:** YES - title & description in target language
- **Format:** Semicolon-separated (`;`) CSV, UTF-8
- **Upload frequency:** Manual or weekly (when products change)
- **Purpose:** Creates the product catalog on Kaufland

### 💰 Offer Feed (Automatic Upload)
- **Contains:** EAN, SKU, price, quantity, currency, condition
- **Needs translation:** NO - just numbers!
- **Format:** Semicolon-separated (`;`) CSV, UTF-8
- **Upload frequency:** Automatic 3x daily (02:00, 10:00, 18:00 Italy time)
- **Purpose:** Updates your prices and stock

---

## 📁 Generated Files

For each country (e.g., Germany = `_de`):

```
kaufland_products_de.csv    ← Product catalog (manual upload)
kaufland_offers_de.csv      ← Price/stock (auto upload)
index_de.html               ← Visual dashboard
feed_info_de.json           ← Metadata
```

---

## 🚀 How It Works

### Step 1: GitHub Action Runs Every 8 Hours
```
00:00 UTC → 01:00/02:00 Italy time
08:00 UTC → 09:00/10:00 Italy time
16:00 UTC → 17:00/18:00 Italy time
```

Generates both feeds with:
- ✅ Stock validation (min 2 units)
- ✅ Price calculation with FX rates
- ✅ Quality filters (EAN, weight, volume, price range)

### Step 2: Feeds Are Published to GitHub Pages
```
https://poppulseemporium.github.io/kaufland-feed/kaufland_products_de.csv
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_de.csv
```

### Step 3: Kaufland Imports Automatically
- **Product Feed:** You upload manually (rare)
- **Offer Feed:** Kaufland auto-imports 3x daily

---

## ⚙️ Kaufland Configuration

### In Kaufland Seller Portal:

#### 1. Disable "Automatic Product Data Upload"
You'll upload products manually when needed.

#### 2. Configure "Automatic Offer Upload"
```
URL: https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_de.csv
Days: Daily (all 7 days checked)
Times: 2:00-3:00, 10:00-11:00, 18:00-19:00 (Italy time)
```

This ensures Kaufland imports your offers ~30-60 minutes after generation.

---

## 🌍 Multi-Country Setup

### Germany (DE)
- **Product Feed:** German language ✅
- **Offer Feed:** EUR currency ✅
- **Setup:** Auto-update offers 3x daily

### Austria (AT)
- **Product Feed:** Use German feed (same language) ✅
- **Offer Feed:** EUR currency ✅
- **Setup:** Auto-update offers 3x daily

### Slovakia (SK)
- **Product Feed:** Need Slovak translation ⚠️
- **Offer Feed:** EUR currency ✅
- **Setup:** Auto-update offers 3x daily

### Poland (PL)
- **Product Feed:** Need Polish translation ⚠️
- **Offer Feed:** PLN currency (rate: 4.5) ✅
- **Setup:** Auto-update offers 3x daily

### Czech Republic (CZ)
- **Product Feed:** Need Czech translation ⚠️
- **Offer Feed:** CZK currency (rate: 24.0) ✅
- **Setup:** Auto-update offers 3x daily

---

## 🔄 Upload Workflow

### Initial Setup (One Time)
1. Generate all country feeds
2. **Manually upload product feeds** to each Kaufland country
3. Configure automatic offer upload URLs in Kaufland

### Daily Operations (Automated)
1. GitHub Action runs every 8 hours
2. Generates fresh offer feeds with current stock/prices
3. Kaufland auto-imports offers 3x daily
4. **You do nothing!** ✅

### When Products Change (Rare)
1. GitHub Action generates new product feed
2. **Manually re-upload product feed** to Kaufland
3. Offers continue auto-updating

---

## 🛠️ Key Features

### Stock Safety
```python
BigBuy Stock → Feed Quantity
1-2 units    → 0 (rejected)
3-5 units    → 2
6-10 units   → 5
11-20 units  → 10
21-50 units  → 25
50+ units    → 50 max (90% of stock)
```

### Price Calculation
```python
Wholesale Price EUR
+ 22% VAT
+ 35% Margin
+ €0.25 Base Price
× FX Rate (for PL/CZ)
= Final Price
```

### Quality Filters
- ✅ Valid EAN13 (13 digits)
- ✅ NEW condition only
- ✅ Weight ≤ 35kg
- ✅ Volume ≤ 180,000 cm³
- ✅ Price: €15-€400
- ✅ Stock ≥ 3 units (to list 2)

---

## 📊 File Format Examples

### Product Feed (kaufland_products_de.csv)
```csv
ean;locale;title;description;category;manufacturer;picture;condition;weight
4019111448324;de-DE;Gartenbank Kadina;Schöne Gartenbank...;Gardening & DIY;Pop Pulse Emporium;http://...;new;15.5
```

### Offer Feed (kaufland_offers_de.csv)
```csv
ean;id_offer;condition;price;currency;quantity;handling_time;delivery_time_min;delivery_time_max
4019111448324;SKU123;100;49.99;EUR;5;2;3;8
```

**Note:** 
- Separator: semicolon (`;`)
- Condition: `100` = new (Kaufland code)
- All numeric fields as strings

---

## 🐛 Troubleshooting

### "No stock issues resolved?"
✅ **Yes!** Your issues were caused by:
1. Not updating product catalog for 1+ month (stale EANs)
2. Only updating once per day (24h window for stock changes)

**Now fixed:**
- Product feed keeps EANs fresh
- Offer feed updates 3x daily
- Minimum 2 units in feed (stock ≥3 required)

### "Do I need to translate offers?"
❌ **No!** Offers are just:
- Numbers (price, quantity, SKU)
- EAN (universal)
- Codes (condition = 100)

The product feed (which HAS translations) links via EAN.

### "Can I use same product feed for AT?"
✅ **Yes!** Austria speaks German, so use the DE product feed for AT offers.

### "What about PL and CZ?"
⚠️ **Need translations** for product feeds.

Options:
1. Use Kaufland's built-in translation feature
2. Generate feeds with Polish/Czech descriptions from BigBuy API
3. Use external translation service

The offer feeds work automatically with correct FX rates.

---

## 🎯 Next Steps

1. **Test Germany first:**
   - Let GitHub Action run once
   - Download `kaufland_products_de.csv`
   - Manually upload to Kaufland Germany
   - Configure auto-upload for `kaufland_offers_de.csv`
   - Wait for 3 import cycles

2. **Verify it works:**
   - Check Kaufland dashboard for new offers
   - Verify prices are correct
   - Confirm stock quantities match expectations

3. **Expand to other countries:**
   - Set up workflows for AT, SK, PL, CZ
   - Handle translations as needed
   - Configure auto-upload for each

---

## 📞 Support

If you see issues:
- Check `feed_info_de.json` for validation stats
- Review HTML dashboard for sample data
- Verify Kaufland import logs
- Ensure semicolon separator is correct

**Common fixes:**
- Stock issues → Already fixed with 3x daily updates
- Translation → Use product feed only when needed
- Currency → Automatically handled in offer feed
- EAN mismatches → Product feed keeps catalog fresh
