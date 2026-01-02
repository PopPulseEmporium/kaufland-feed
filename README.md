# Pop Pulse Emporium - Marketplace Feed Generator

Automated feed generation for Kaufland (7 countries) and ManoMano (Italy) marketplaces using BigBuy API.

## Feed URLs

### Kaufland Feeds
| Country | CSV Feed | Dashboard |
|---------|----------|-----------|
| Italy | [kaufland_feed_it.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_it.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_it.html) |
| Germany | [kaufland_feed_de.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_de.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_de.html) |
| France | [kaufland_feed_fr.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_fr.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_fr.html) |
| Austria | [kaufland_feed_at.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_at.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_at.html) |
| Slovakia | [kaufland_feed_sk.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_sk.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_sk.html) |
| Poland | [kaufland_feed_pl.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_pl.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_pl.html) |
| Czech Republic | [kaufland_feed_cz.csv](https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_cz.csv) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/index_cz.html) |

### ManoMano Feeds
| Country | CSV Feed | XLSX Feed | Dashboard |
|---------|----------|-----------|-----------|
| Italy | [manomano_feed_it.csv](https://poppulseemporium.github.io/kaufland-feed/manomano_feed_it.csv) | [manomano_feed_it.xlsx](https://poppulseemporium.github.io/kaufland-feed/manomano_feed_it.xlsx) | [Dashboard](https://poppulseemporium.github.io/kaufland-feed/manomano_index_it.html) |

---

## Update Schedule

Feeds are automatically updated every 8 hours:
- **01:00 CET** (00:00 UTC)
- **09:00 CET** (08:00 UTC)
- **17:00 CET** (16:00 UTC)

---

## Configuration

Each marketplace/country has its own YAML config file in `V2/config/`:

### Kaufland Configs
- `V2/config/kaufland_it.yaml`
- `V2/config/kaufland_de.yaml`
- `V2/config/kaufland_fr.yaml`
- `V2/config/kaufland_at.yaml`
- `V2/config/kaufland_sk.yaml`
- `V2/config/kaufland_pl.yaml`
- `V2/config/kaufland_cz.yaml`

### ManoMano Configs
- `V2/config/manomano_it.yaml`

### Config Parameters

```yaml
# Pricing settings
pricing:
  margin: 0.43              # 43% markup
  vat: 0.22                 # 22% VAT
  base_price: 2.0           # Fixed fee added to price
  min_price_eur: 15.0       # Minimum selling price
  max_price_eur: 1000.0     # Maximum selling price

# Product filters
filters:
  max_weight_kg: 28.0       # Max product weight
  max_volume_cm3: 150000    # Max product volume
  max_handling_days: 2      # Only include immediate stock
  sample_size: 10000        # Max products per feed

# Promotions
promotions:
  enable_black_friday: false
  black_friday_prefix: "Black Friday OFFER - "

# Shipping settings
shipping:
  handling_time: 2
  delivery_time_min: 3
  delivery_time_max: 8
```

---

## Directory Structure

```
├── V2/                         # Current version (active)
│   ├── bigbuy_kaufland.py      # Kaufland feed generator
│   ├── manomano_feed_generator.py  # ManoMano feed generator
│   ├── generate_all_kaufland_feeds.py  # Multi-country orchestrator
│   └── config/                 # YAML configuration files
│       ├── kaufland_*.yaml     # Per-country Kaufland configs
│       └── manomano_*.yaml     # Per-country ManoMano configs
│
├── V1-deprecated/              # Old version (archived)
│   ├── bigbuy_kaufland.py
│   ├── bigbuy_manomano.py
│   └── ...
│
├── .github/workflows/
│   └── generate-feeds-v2.yml   # Automated workflow
│
└── [Generated Files]           # Output CSVs, HTMLs, JSONs
```

---

## Countries & Currencies

| Country | Code | Currency | FX Rate |
|---------|------|----------|---------|
| Italy | IT | EUR | 1.0 |
| Germany | DE | EUR | 1.0 |
| France | FR | EUR | 1.0 |
| Austria | AT | EUR | 1.0 |
| Slovakia | SK | EUR | 1.0 |
| Poland | PL | PLN | 4.5 |
| Czech Republic | CZ | CZK | 24.0 |

---

## Validation Rules

Products are validated against these criteria:
- Valid EAN13 (13 digits)
- NEW condition only
- Weight ≤ 28kg
- Volume ≤ 150,000 cm³
- Price: €15-€1000 (before currency conversion)
- Stock ≥ 2 units with ≤2 day handling time

### Stock Safety Margins

```
BigBuy Stock → Listed Quantity
1-2 units    → 1
3-5 units    → 2
6-10 units   → 5
11-20 units  → 10
21-50 units  → 25
50+ units    → 50 max (90% of stock)
```

---

## Running Locally

```bash
# Set API key
export BIGBUY_API_KEY="your_api_key"

# Generate single country feed
export COUNTRY_CODE="IT"
python V2/bigbuy_kaufland.py

# Generate all Kaufland countries
python V2/generate_all_kaufland_feeds.py

# Generate ManoMano Italy
export COUNTRY_CODE="IT"
python V2/manomano_feed_generator.py
```

---

## GitHub Actions

The workflow `.github/workflows/generate-feeds-v2.yml`:
1. Runs every 8 hours automatically
2. Generates feeds for all 7 Kaufland countries in parallel
3. Generates ManoMano Italy feed
4. Deploys all files to GitHub Pages

### Manual Trigger
Go to Actions → "Generate Kaufland & ManoMano Feeds (V2)" → Run workflow

---

## Requirements

```
requests==2.31.0
pandas==1.5.3
numpy==1.24.3
PyYAML==6.0.1
openpyxl==3.1.2
```

---

## Secrets Required

In GitHub repository settings → Secrets → Actions:
- `BIGBUY_API_KEY` - Your BigBuy API key
