# Multi-Language Kaufland Feed - Complete Setup Guide

## 🎯 The Perfect Solution

You now have the **optimal setup** for selling across multiple Kaufland countries:

### 📦 ONE Product Feed (All Languages)
- **File:** `kaufland_products_all.csv`
- **Contains:** Same products with translations in DE, AT, SK, PL, CZ
- **Format:** Multiple rows per EAN (one row per locale)
- **Upload:** Manual, rare (when products change)

### 💰 FIVE Offer Feeds (Per Country)
- **Files:** `kaufland_offers_de.csv`, `kaufland_offers_at.csv`, etc.
- **Contains:** EAN, SKU, price (with FX), quantity, condition
- **NO translation needed** - just numbers!
- **Upload:** Automatic 3x daily

---

## 📁 Generated Files

```
kaufland_products_all.csv      ← ONE product feed (all languages)
kaufland_offers_de.csv         ← Germany offers (EUR)
kaufland_offers_at.csv         ← Austria offers (EUR)
kaufland_offers_sk.csv         ← Slovakia offers (EUR)
kaufland_offers_pl.csv         ← Poland offers (PLN)
kaufland_offers_cz.csv         ← Czech Republic offers (CZK)
feed_info.json                 ← Metadata
```

---

## 🔄 How Multi-Language Product Feed Works

### Example: Product with EAN 4019111448324

The product feed contains **multiple rows for the same EAN**:

```csv
ean;locale;title;description;picture;...
4019111448324;de-DE;Gartenbank Kadina;Deutsche Beschreibung...;http://...;...
4019111448324;de-AT;Gartenbank Kadina;Deutsche Beschreibung...;http://...;...
4019111448324;sk-SK;Záhradná lavica Kadina;Slovenský popis...;http://...;...
4019111448324;pl-PL;Ławka ogrodowa Kadina;Polski opis...;http://...;...
4019111448324;cs-CZ;Zahradní lavice Kadina;Český popis...;http://...;...
```

**Kaufland automatically:**
1. Recognizes the EAN
2. Uses the correct locale for each country
3. Creates/updates product with proper translation

---

## 💰 How Offer Feeds Work Per Country

Each country gets its own offer feed with correct currency:

### Germany (`kaufland_offers_de.csv`)
```csv
ean;id_offer;condition;price;currency;quantity;...
4019111448324;SKU123;100;49.99;EUR;5;...
```

### Poland (`kaufland_offers_pl.csv`)
```csv
ean;id_offer;condition;price;currency;quantity;...
4019111448324;SKU123;100;224.96;PLN;5;...
```
*Same product, different currency (49.99 EUR × 4.5 = 224.96 PLN)*

---

## 🚀 GitHub Action Workflow

### Runs Every 8 Hours
```
00:00 UTC → 01:00/02:00 Italy
08:00 UTC → 09:00/10:00 Italy
16:00 UTC → 17:00/18:00 Italy
```

### What It Does
1. ✅ Fetches products from BigBuy API
2. ✅ Collects descriptions in ALL languages (de, sk, pl, cs)
3. ✅ Validates products (stock, EAN, price, weight, volume)
4. ✅ Generates ONE product feed with all translations
5. ✅ Generates FIVE offer feeds (one per country with FX)
6. ✅ Commits to GitHub
7. ✅ Publishes to GitHub Pages

---

## ⚙️ Kaufland Configuration (Per Country)

### For EACH Country (DE, AT, SK, PL, CZ):

#### Step 1: Upload Product Feed (One-Time)
1. Go to Kaufland Seller Portal for that country
2. Go to: **Product Data** → **Import Product Data**
3. **Manual Upload** → Choose `kaufland_products_all.csv`
4. Click Upload

**This creates the product catalog with translations for ALL countries!**

#### Step 2: Configure Automatic Offer Upload
1. Go to: **Offer Data** → **Automatic Offer Upload**
2. Enter URL: 
   - DE: `https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_de.csv`
   - AT: `https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_at.csv`
   - SK: `https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_sk.csv`
   - PL: `https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_pl.csv`
   - CZ: `https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_cz.csv`
3. Days: **Daily** (all 7 days)
4. Times: **2:00-3:00, 10:00-11:00, 18:00-19:00** (local time)
5. Save

---

## 📊 Feed Format Details

### Product Feed Structure
```csv
ean;locale;title;description;short_description;category;manufacturer;picture;picture_2;picture_3;picture_4;condition;weight;length;width;height
```

**Separator:** Semicolon (`;`)
**Encoding:** UTF-8
**Multiple locales:** YES - same EAN with different locale values

### Offer Feed Structure
```csv
ean;id_offer;condition;price;currency;quantity;handling_time;delivery_time_min;delivery_time_max
```

**Separator:** Semicolon (`;`)
**Encoding:** UTF-8
**Condition:** `100` = new (Kaufland code)

---

## 🌍 Countries & Currencies

| Country | Code | Locale | Language | Currency | FX Rate |
|---------|------|--------|----------|----------|---------|
| Germany | DE | de-DE | German | EUR | 1.0 |
| Austria | AT | de-AT | German | EUR | 1.0 |
| Slovakia | SK | sk-SK | Slovak | EUR | 1.0 |
| Poland | PL | pl-PL | Polish | PLN | 4.5 |
| Czech Rep | CZ | cs-CZ | Czech | CZK | 24.0 |

---

## ✅ Quality & Safety Features

### Stock Safety Margins
```
BigBuy Stock → Your Listing
1-2 units    → Rejected (not listed)
3-5 units    → List 2
6-10 units   → List 5
11-20 units  → List 10
21-50 units  → List 25
50+ units    → List 50 max
```

### Validation Rules
- ✅ Valid EAN13 (13 digits)
- ✅ NEW condition only
- ✅ Weight ≤ 35kg
- ✅ Volume ≤ 180,000 cm³
- ✅ Price: €15-€400 (in EUR, before FX)
- ✅ Stock ≥ 3 units in BigBuy

### Price Calculation
```
Base Formula:
Wholesale Price (EUR)
× 1.22 (VAT)
× 1.35 (Margin)
+ €0.25 (Base fee)
= Price in EUR

Then for non-EUR countries:
EUR Price × FX Rate = Local Price
```

---

## 🔧 Troubleshooting

### "Products not showing in all countries?"
**Solution:** Make sure you uploaded `kaufland_products_all.csv` to EACH country's Kaufland portal. The file is the same, but each country needs it uploaded.

### "Prices wrong in Poland/Czech?"
**Check:** 
- PLN should be ~4.5× EUR price
- CZK should be ~24× EUR price
If not, verify the FX rates in the script.

### "Stock still running out?"
**Check:**
1. Are offer feeds auto-importing 3x daily?
2. Look at Kaufland import logs
3. Verify times are correct for your timezone

### "Some products missing translations?"
**Cause:** BigBuy might not have descriptions in all languages.
**Solution:** Script will use available languages. Products without translations in a language won't have rows for that locale.

---

## 📋 Daily Operations Checklist

### Automated (No Action Needed)
- ✅ GitHub Action runs every 8 hours
- ✅ Generates fresh product feed (all languages)
- ✅ Generates fresh offer feeds (all countries)
- ✅ Publishes to GitHub Pages
- ✅ Kaufland imports offers 3x daily automatically

### Manual (Only When Needed)
- 📦 **Re-upload product feed** when:
  - Adding new product categories
  - BigBuy updates descriptions
  - You want to refresh translations
  - Frequency: Weekly or monthly

---

## 🎯 Why This Setup Solves Your Problems

### Problem 1: Stock Issues ✅ SOLVED
**Before:** Updated once daily, stale product catalog
**Now:** Offers update 3x daily, fresh product data, min 2 units listed

### Problem 2: Translation Complexity ✅ SOLVED
**Before:** Needed separate product feeds per country
**Now:** ONE product feed with all languages, auto-matched by Kaufland

### Problem 3: Currency Handling ✅ SOLVED
**Before:** Manual price conversions
**Now:** Automatic FX calculation per country in offer feeds

### Problem 4: Manual Work ✅ SOLVED
**Before:** Manual uploads for everything
**Now:** Only product feed manual (rare), offers auto-update

---

## 🚀 Getting Started (First Time)

### Step 1: Deploy Script & Workflow
1. Save `bigbuy_kaufland.py` (the new multi-language version)
2. Save `.github/workflows/update-all-feeds.yml`
3. Commit and push to GitHub
4. Verify GitHub Action runs successfully

### Step 2: Download Generated Files
After first run, download:
- `kaufland_products_all.csv`
- `kaufland_offers_de.csv`, `kaufland_offers_at.csv`, etc.

### Step 3: Upload to Kaufland (Per Country)
For **each country** (DE, AT, SK, PL, CZ):

1. **Upload product feed** (manual, one-time):
   - Login to that country's Kaufland Seller Portal
   - Upload `kaufland_products_all.csv`
   - This creates products with translations

2. **Configure offer auto-upload**:
   - Set URL for that country's offer feed
   - Set times: 02:00, 10:00, 18:00
   - Enable daily upload

### Step 4: Monitor & Verify
- Wait 24 hours
- Check Kaufland dashboards for each country
- Verify products appear with correct translations
- Verify offers update with correct prices/stock
- Check import logs for any errors

### Step 5: You're Done! 🎉
Everything now runs automatically. Only re-upload product feed when products significantly change.

---

## 📞 Quick Reference

### Feed URLs
```
Product (all languages):
https://poppulseemporium.github.io/kaufland-feed/kaufland_products_all.csv

Offers per country:
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_de.csv
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_at.csv
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_sk.csv
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_pl.csv
https://poppulseemporium.github.io/kaufland-feed/kaufland_offers_cz.csv
```

### Update Schedule
- **GitHub Action:** Every 8 hours (01:00, 09:00, 17:00 Italy time)
- **Kaufland Import:** 3x daily (02:00, 10:00, 18:00 local time per country)

### Key Files
- `bigbuy_kaufland.py` - Multi-language feed generator
- `.github/workflows/update-all-feeds.yml` - GitHub Action
- `feed_info.json` - Metadata and stats
