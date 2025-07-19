# 🛍️ Feed Prodotti Multi-Marketplace

Sistema automatico per sincronizzare prodotti BigBuy con Kaufland (5 paesi) e ManoMano (Italia).

## 🌍 Marketplace Supportati

### 🏪 **Kaufland** (5 Paesi)
| Paese | Codice | Feed URL | Lingua | Valuta | Aggiornamento |
|-------|--------|----------|--------|--------|---------------|
| 🇦🇹 Austria | AT | `kaufland_feed_at.csv` | Tedesco | EUR | Ogni 6 ore (:15) |
| 🇩🇪 Germania | DE | `kaufland_feed_de.csv` | Tedesco | EUR | Ogni 6 ore (:25) |
| 🇸🇰 Slovacchia | SK | `kaufland_feed_sk.csv` | Slovacco | EUR | Ogni 6 ore (:45) |
| 🇨🇿 Rep. Ceca | CZ | `kaufland_feed_cz.csv` | Ceco | CZK | Ogni 6 ore (:55) |
| 🇵🇱 Polonia | PL | `kaufland_feed_pl.csv` | Polacco | PLN | Ogni 6 ore (:05) |

### 🔨 **ManoMano** (Italia)
| Marketplace | Codice | Feed URL | Lingua | Valuta | Focus | Aggiornamento |
|-------------|--------|----------|--------|--------|-------|---------------|
| 🇮🇹 ManoMano | IT | `manomano_feed.csv` | Italiano | EUR | DIY/Casa/Giardino | Ogni 6 ore (:10) |

## 📡 URL Feed Diretti

### 🏪 **Kaufland** (da inserire nel portale Kaufland)
```
Austria:      https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_at.csv
Germania:     https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_de.csv
Slovacchia:   https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_sk.csv
Rep. Ceca:    https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_cz.csv
Polonia:      https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_pl.csv
```

### 🔨 **ManoMano** (da inserire nel portale ManoMano)
```
Italia:       https://poppulseemporium.github.io/kaufland-feed/manomano_feed.csv
```

### 🌐 **Anteprima HTML**
```
Kaufland Austria:    https://poppulseemporium.github.io/kaufland-feed/index_at.html
Kaufland Germania:   https://poppulseemporium.github.io/kaufland-feed/index_de.html
Kaufland Slovacchia: https://poppulseemporium.github.io/kaufland-feed/index_sk.html
Kaufland Rep. Ceca:  https://poppulseemporium.github.io/kaufland-feed/index_cz.html
Kaufland Polonia:    https://poppulseemporium.github.io/kaufland-feed/index_pl.html
ManoMano Italia:     https://poppulseemporium.github.io/kaufland-feed/manomano_index.html
```

## ✅ **Validazione Stock e Qualità**

### 🔒 **Garanzie Anti-Overselling**
- **✅ Stock verificato**: Ogni prodotto ha stock confermato da BigBuy API
- **✅ Margini di sicurezza**: Quantità ridotte per evitare overselling
- **✅ Aggiornamento continuo**: Stock controllato ogni 6 ore
- **✅ Solo prodotti NUOVI**: Condizione verificata
- **✅ EAN13 validi**: Codici a barre verificati (13 cifre)

### 📊 **Filtri Qualità Applicati**

#### **🏪 Kaufland** (Marketplace Generalista)
| Filtro | Valore | Motivo |
|--------|--------|--------|
| **Stock minimo** | ≥ 2 unità | Evita overselling |
| **Prezzo minimo** | ≥ €6 | Margini migliori |
| **Prezzo massimo** | ≤ €200 | Limite Kaufland |
| **Peso massimo** | ≤ 25kg | Limiti spedizione |
| **Volume massimo** | ≤ 70.000 cm³ | Limiti logistici |
| **Condizione** | Solo NUOVO | Policy marketplace |
| **Margine** | 30% | Competitività |

#### **🔨 ManoMano** (DIY/Casa/Giardino)
| Filtro | Valore | Motivo |
|--------|--------|--------|
| **Stock minimo** | ≥ 2 unità | Evita overselling |
| **Prezzo minimo** | ≥ €6 | Margini migliori |
| **Prezzo massimo** | ≤ €500 | Attrezzi/Equipaggiamento |
| **Peso massimo** | ≤ 50kg | Attrezzi pesanti |
| **Volume massimo** | ≤ 100.000 cm³ | Equipaggiamento grande |
| **Categorie focus** | Bricolage, Giardino, Casa | Specializzazione ManoMano |
| **Margine** | 30% | Competitività |

## 🎲 **Randomizzazione e Varietà**

### **Come Funziona la Selezione**
1. **⏰ Seed temporale**: Ogni paese ha orari diversi → seed diversi
2. **🔀 Categorie randomizzate**: Ordine categorie cambia per paese
3. **🎯 Prodotti randomizzati**: Selezione casuale in ogni categoria
4. **📊 Post-filtri**: Solo prodotti che passano tutti i controlli qualità

### **Perché Prodotti Simili tra Paesi**
- **Pool limitato**: Dopo filtri severi rimangono ~8-12k prodotti "top quality"
- **Stessi standard**: Tutti i paesi usano gli stessi filtri di qualità
- **Migliori prodotti**: Prodotti con stock affidabile appaiono più spesso

### **Risultati Attesi per Paese**
- **🏪 Kaufland**: ~4.000-6.000 prodotti per paese
- **🔨 ManoMano**: ~8.000-12.000 prodotti (focus DIY)

## 💱 **Gestione Valute**

| Paese | Valuta | Tasso | Range Prezzi | Esempio |
|-------|--------|-------|--------------|---------|
| 🇦🇹 Austria | EUR | 1.0 | €6 - €200 | €50 → €50 |
| 🇩🇪 Germania | EUR | 1.0 | €6 - €200 | €50 → €50 |
| 🇸🇰 Slovacchia | EUR | 1.0 | €6 - €200 | €50 → €50 |
| 🇨🇿 Rep. Ceca | CZK | 24.0 | 144 - 4.800 CZK | €50 → 1.200 CZK |
| 🇵🇱 Polonia | PLN | 4.5 | 27 - 900 PLN | €50 → 225 PLN |
| 🇮🇹 ManoMano | EUR | 1.0 | €6 - €500 | €50 → €50 |

## ⚙️ **Configurazione Marketplace**

### 🏪 **Setup Kaufland**
1. **Portale Venditori** → **Gestione Prodotti** → **Feed automatico**
2. **URL Feed**: Inserisci l'URL del paese specifico
3. **Frequenza**: Ogni 6 ore (o giornaliera)
4. **Formato**: CSV UTF-8
5. **Verifica**: Controllo automatico formato

### 🔨 **Setup ManoMano**
1. **Seller Center** → **Catalogo** → **Importazione prodotti**
2. **URL Feed**: `https://poppulseemporium.github.io/kaufland-feed/manomano_feed.csv`
3. **Frequenza**: Ogni 6 ore
4. **Categorie**: Mappatura automatica a categorie ManoMano
5. **Validazione**: Controllo qualità prodotti

## 🔄 **Schedule Aggiornamenti**

### ⏰ **Orari Ottimizzati**
```
:05 min → 🇵🇱 Polonia (PLN)
:10 min → 🔨 ManoMano Italia (EUR)
:15 min → 🇦🇹 Austria (EUR)
:25 min → 🇩🇪 Germania (EUR)
:45 min → 🇸🇰 Slovacchia (EUR)
:55 min → 🇨🇿 Rep. Ceca (CZK)
```

### 📈 **Processo Automatico**
1. **🔍 Estrazione**: 20 categorie BigBuy randomizzate
2. **📊 Validazione**: Stock, prezzo, qualità, EAN13
3. **🌐 Localizzazione**: Traduzione descrizioni
4. **💱 Conversione**: Prezzi in valuta locale
5. **📁 Generazione**: CSV + HTML per marketplace
6. **🚀 Pubblicazione**: GitHub Pages automatica

## 📊 **Formato Feed**

### 🏪 **Kaufland CSV**
```csv
id_offer,ean,locale,category,title,short_description,description,
manufacturer,picture_1,picture_2,picture_3,picture_4,price_cs,
quantity,condition,length,width,height,weight,content_volume,
currency,handling_time,delivery_time_max,delivery_time_min
```

### 🔨 **ManoMano CSV**
```csv
sku,ean,title,description,brand,category,price,quantity,condition,
weight,length,width,height,image_url,image_url_2,image_url_3,
image_url_4,shipping_cost,delivery_time,warranty,origin_country,
material,color,size
```

## 🛠️ **Setup Tecnico**

### 1. **GitHub Repository**
```bash
# Secrets necessari
BIGBUY_API_KEY=your_api_key_here

# Files richiesti
bigbuy_kaufland.py      # Script Kaufland
bigbuy_manomano.py      # Script ManoMano
requirements.txt        # Dipendenze Python
.github/workflows/      # Workflow automatici
```

### 2. **GitHub Pages**
- **Settings** → **Pages** → **Source**: main branch
- **Custom domain** (opzionale): `feeds.poppulseemporium.com`

### 3. **Workflow Files**
```
.github/workflows/update-feed-at.yml      # Austria
.github/workflows/update-feed-de.yml      # Germania  
.github/workflows/update-feed-sk.yml      # Slovacchia
.github/workflows/update-feed-cz.yml      # Rep. Ceca
.github/workflows/update-feed-pl.yml      # Polonia
.github/workflows/update-feed-manomano.yml # ManoMano
```

## 📈 **Monitoraggio**

### 🎯 **Metriche Chiave**
- **Success Rate**: % prodotti che passano filtri (~55-60%)
- **Stock Validation**: 100% prodotti con stock confermato
- **Update Frequency**: Ogni 6 ore per tutti i feed
- **Quality Score**: EAN13 + Stock + Prezzo + Descrizione

### 📊 **Dashboard HTML**
Ogni feed include pagina di monitoraggio con:
- **📈 Statistiche**: Prodotti validati, filtri applicati
- **💰 Range prezzi**: Min/max per marketplace
- **🎲 Randomization**: Seed temporale utilizzato
- **✅ Validazione**: Controlli qualità superati

## 🚀 **Avvio Rapido**

### **Test Manuale**
```bash
# 1. Vai su GitHub Actions
# 2. Seleziona workflow (es. "Aggiorna Feed Kaufland Austria")  
# 3. Click "Run workflow"
# 4. Verifica risultati in ~5 minuti
```

### **Verifica Feed**
```bash
# Kontrolla che i feed siano accessibili
curl -I https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_at.csv
curl -I https://poppulseemporium.github.io/kaufland-feed/manomano_feed.csv
```

## 🔧 **Personalizzazione**

### **Modifica Filtri** (`bigbuy_kaufland.py` / `bigbuy_manomano.py`)
```python
# Prezzi
min_price_eur = 6.0        # Prezzo minimo
max_price_eur = 200.0      # Kaufland max (500 per ManoMano)
margin = 0.30              # Margine 30%

# Stock
stock_minimum = 2          # Stock minimo richiesto

# Fisici  
max_weight = 25.0          # Peso max kg (50 per ManoMano)
max_volume = 70000         # Volume max cm³ (100000 per ManoMano)
```

### **Aggiunta Nuovi Paesi**
1. **Config**: Aggiungi in `country_config` dictionary
2. **Workflow**: Crea `.github/workflows/update-feed-{paese}.yml`
3. **Language**: Configura lingua locale appropriata
4. **Currency**: Aggiungi tasso di cambio se necessario

## ❗ **Risoluzione Problemi**

### **Feed Non Si Aggiorna**
- ✅ Controlla **GitHub Actions** per errori
- ✅ Verifica validità **BIGBUY_API_KEY**
- ✅ Controlla logs workflow specifico
- ✅ Verifica limite rate BigBuy API

### **Marketplace Non Accetta Feed**
- ✅ URL deve essere pubblico (GitHub Pages attivo)
- ✅ Formato CSV UTF-8 corretto
- ✅ Tutti i campi obbligatori presenti
- ✅ EAN13 validi (13 cifre esatte)

### **Pochi Prodotti nel Feed**
- ✅ **Normal**: Filtri qualità sono severi per evitare problemi
- ✅ **Stock limitato**: BigBuy potrebbe avere meno prodotti disponibili
- ✅ **Prezzi alti**: Molti prodotti sopra soglie prezzo
- ✅ **Categorie**: Alcune categorie hanno pochi prodotti

## 📞 **Supporto**

- **🐛 Issues**: [GitHub Issues](https://github.com/poppulseemporium/kaufland-feed/issues)
- **📚 BigBuy API**: [Documentazione](https://api.bigbuy.eu/rest)
- **🏪 Kaufland**: [Centro Assistenza](https://www.kaufland.de/service/hilfe/)
- **🔨 ManoMano**: [Seller Center](https://vendeurs.manomano.fr/)

---

## ✨ **Versione 3.0 - Multi-Marketplace**

### 🆕 **Novità**
- ✅ **Stock validation completa**: API BigBuy per stock reali
- ✅ **ManoMano support**: Feed specializzato DIY/Casa
- ✅ **Filtri avanzati**: Prezzo minimo €6, stock ≥2 unità
- ✅ **6 marketplace**: 5 Kaufland + 1 ManoMano  
- ✅ **Localizzazione completa**: 5 lingue + valute locali
- ✅ **Zero overselling**: Margini sicurezza su tutte le quantità
- ✅ **Categorizzazione smart**: Mapping automatico categorie marketplace

### 🎯 **Obiettivo**
**Vendere su 6 marketplace europei con aggiornamenti automatici e zero rischi di overselling!**

## 📄 **Licenza**
MIT License - Vedi `LICENSE` per dettagli completi.
