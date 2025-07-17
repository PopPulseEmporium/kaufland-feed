# 🛍️ Feed Prodotti Kaufland Multi-Paese

Sistema automatico per sincronizzare prodotti BigBuy con Kaufland in 5 paesi europei.

## 🌍 Paesi Supportati

| Paese | Codice | Feed URL | Lingua | Aggiornamento |
|-------|--------|----------|--------|---------------|
| 🇮🇹 Italia | IT | `kaufland_feed.csv` | Italiano | Ogni 6 ore |
| 🇩🇪 Germania | DE | `kaufland_feed_de.csv` | Tedesco | Ogni 6 ore |
| 🇦🇹 Austria | AT | `kaufland_feed_at.csv` | Tedesco | Ogni 6 ore (+15min) |
| 🇵🇱 Polonia | PL | `kaufland_feed_pl.csv` | Polacco | Ogni 6 ore (+30min) |
| 🇸🇰 Slovacchia | SK | `kaufland_feed_sk.csv` | Slovacco | Ogni 6 ore (+45min) |
| 🇨🇿 Rep. Ceca | CZ | `kaufland_feed_cz.csv` | Ceco | 4 volte al giorno |

## 📡 URL Feed per Kaufland

### URL Diretti CSV (da inserire in Kaufland)
```
Italia:       https://poppulseemporium.github.io/kaufland-feed/kaufland_feed.csv
Germania:     https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_de.csv
Austria:      https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_at.csv  
Polonia:      https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_pl.csv
Slovacchia:   https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_sk.csv
Rep. Ceca:    https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_cz.csv
```

### Anteprima HTML per Paese
```
Italia:       https://poppulseemporium.github.io/kaufland-feed/index.html
Germania:     https://poppulseemporium.github.io/kaufland-feed/index_de.html
Austria:      https://poppulseemporium.github.io/kaufland-feed/index_at.html
Polonia:      https://poppulseemporium.github.io/kaufland-feed/index_pl.html
Slovacchia:   https://poppulseemporium.github.io/kaufland-feed/index_sk.html
Rep. Ceca:    https://poppulseemporium.github.io/kaufland-feed/index_cz.html
```

## ⚙️ Configurazione Kaufland

### 1. Accesso al Portale Venditori Kaufland
1. Accedi al tuo account Kaufland Marketplace
2. Vai su **"Gestione Prodotti"** → **"Caricamento automatico dei dati dei prodotti"**

### 2. Inserimento Feed URL
1. Nel campo **"Percorso del file"** inserisci l'URL del paese desiderato:
   ```
   Esempio per Germania:
   https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_de.csv
   ```

2. Seleziona **"Giorno feriale"**: Tutti i giorni
3. Seleziona **"Ora"**: 06:00 (o orario preferito)
4. Clicca **"Salva le modifiche"**

### 3. Verifica Feed
- Kaufland verificherà automaticamente il formato del feed
- I prodotti appariranno nel tuo catalogo entro 24-48 ore
- Controlla lo stato in **"Gestione Prodotti"** → **"I miei prodotti"**

## 📊 Dettagli Tecnici

### Caratteristiche Prodotti
- **Quantità per paese**: 25.000 prodotti selezionati casualmente
- **Prezzo massimo**: €300 per prodotto
- **Condizione**: Solo prodotti NUOVI
- **Stock minimo**: ≥ 2 unità disponibili in BigBuy
- **Quantità reali**: Stock effettivo da BigBuy (massimo 100)
- **Margine applicato**: 20%
- **IVA**: 22%
- **Categoria principale**: Gardening & DIY
- **Tempi di consegna**: 3-5 giorni lavorativi

### Formato CSV Kaufland
Il feed include tutti i campi richiesti da Kaufland:
```csv
id_offer,ean,locale,category,title,short_description,description,
manufacturer,picture_1,picture_2,picture_3,picture_4,price_cs,
quantity,condition,length,width,height,weight,content_volume,
currency,handling_time,delivery_time_max,delivery_time_min
```

### Localizzazione per Paese
- **Italia**: Descrizioni in italiano (`it-IT`)
- **Germania/Austria**: Descrizioni in tedesco (`de-DE`, `de-AT`)
- **Polonia**: Descrizioni in polacco (`pl-PL`)
- **Slovacchia**: Descrizioni in slovacco (`sk-SK`)
- **Rep. Ceca**: Descrizioni in ceco (`cs-CZ`)

## 🔄 Aggiornamenti Automatici

### Schedule GitHub Actions
- **Italia**: Ogni 6 ore (00:00, 06:00, 12:00, 18:00)
- **Germania**: Ogni 6 ore (00:00, 06:00, 12:00, 18:00)
- **Austria**: Ogni 6 ore (+15 min offset)
- **Polonia**: Ogni 6 ore (+30 min offset)  
- **Slovacchia**: Ogni 6 ore (+45 min offset)
- **Rep. Ceca**: 4 volte al giorno (01:00, 07:00, 13:00, 19:00)

### Processo di Aggiornamento
1. **Estrazione dati** da BigBuy API
2. **Filtraggio** prodotti (max €300, solo NUOVI, stock ≥ 2)
3. **Selezione casuale** di 25k prodotti per paese
4. **Traduzione** descrizioni nella lingua locale
5. **Quantità reali** dal magazzino BigBuy (max 100)
6. **Generazione** file CSV e HTML separati per paese
7. **Pubblicazione** automatica su GitHub Pages

## 🛠️ Configurazione Tecnica

### Variabili d'Ambiente
```bash
BIGBUY_API_KEY=your_bigbuy_api_key_here
COUNTRY_CODE=DE  # IT, DE, AT, PL, SK, CZ
```

### File Generati per Paese
**Italia (paese principale):**
- `kaufland_feed.csv` - Feed principale
- `feed_info.json` - Metadati del feed
- `index.html` - Anteprima prodotti

**Altri paesi:**
- `kaufland_feed_{paese}.csv` - Feed principale
- `feed_info_{paese}.json` - Metadati del feed
- `index_{paese}.html` - Anteprima prodotti

### Dipendenze Python
```
requests==2.31.0
pandas==1.5.3
numpy==1.24.3
```

## 📈 Monitoraggio e Statistiche

### Dashboard HTML
Ogni feed include una pagina di anteprima con:
- **Statistiche**: Numero prodotti, margine, range prezzi
- **Anteprima**: Primi 50 prodotti con immagini
- **URL diretti**: Link CSV per Kaufland
- **Informazioni**: Ultimo aggiornamento, configurazione

### Logs GitHub Actions
Monitora gli aggiornamenti in **Actions** → **Workflow runs**

## 🚀 Avvio Rapido

### 1. Configurazione Repository
```bash
# Clona il repository
git clone https://github.com/poppulseemporium/kaufland-feed.git

# Configura API key nei Secrets
# Settings → Secrets → Actions → New repository secret
# Nome: BIGBUY_API_KEY
# Valore: your_bigbuy_api_key
```

### 2. Attivazione GitHub Pages
1. **Settings** → **Pages**
2. **Source**: Deploy from a branch
3. **Branch**: main
4. **Folder**: / (root)
5. **Save**

### 3. Test Manuale
1. **Actions** → **All workflows**
2. Seleziona workflow paese (es. "Aggiorna Feed Kaufland Germania")
3. **Run workflow** → **Run workflow**

### 4. Verifica Feed
```bash
# Controlla i file generati per ogni paese
curl https://poppulseemporium.github.io/kaufland-feed/kaufland_feed.csv      # Italia
curl https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_de.csv   # Germania
curl https://poppulseemporium.github.io/kaufland-feed/kaufland_feed_at.csv   # Austria
```

## 🔧 Personalizzazione

### Modifica Parametri
Nel file `bigbuy_kaufland.py`:
```python
# Configurazione prezzi
margin = 0.20              # Margine 20%
vat = 0.22                # IVA 22%
max_price_limit = 300.0   # Prezzo massimo €300
sample_size = 25000       # Prodotti per paese

# Filtro stock
stock_minimum = 5         # Stock minimo richiesto

# Tempi di consegna
handling_time = 2         # Giorni preparazione
delivery_time_min = 3     # Consegna minima
delivery_time_max = 5     # Consegna massima
```

### Aggiunta Nuovi Paesi
1. Aggiungi configurazione in `country_config`
2. Crea nuovo workflow `.github/workflows/update-feed-{paese}.yml`
3. Configura `COUNTRY_CODE` nel workflow

## ❓ Risoluzione Problemi

### Feed Non Si Aggiorna
- Controlla **Actions** per errori nei workflow
- Verifica la validità dell'API key BigBuy
- Controlla i logs del workflow specifico

### Kaufland Non Accetta Feed
- Verifica che l'URL sia accessibile pubblicamente
- Controlla il formato CSV (deve essere UTF-8)
- Assicurati che tutti i campi obbligatori siano presenti

### Prodotti Non Appaiono
- I prodotti impiegano 24-48 ore per apparire
- Controlla **"I miei prodotti"** in Kaufland
- Verifica che i prodotti rispettino le policy Kaufland

## 📞 Supporto

- **Repository**: [GitHub Issues](https://github.com/poppulseemporium/kaufland-feed/issues)
- **BigBuy API**: [Documentazione BigBuy](https://api.bigbuy.eu/rest)
- **Kaufland**: [Centro Assistenza Kaufland](https://www.kaufland.de/service/hilfe/)

## 📄 Licenza

Questo progetto è disponibile sotto licenza MIT. Vedi il file `LICENSE` per i dettagli.

---

🎯 **Obiettivo**: Vendere su Kaufland in 6 paesi europei con aggiornamenti automatici ogni 6 ore!

## ✨ **Novità Versione 2.0**

- ✅ **Stock reali**: Quantità effettive dal magazzino BigBuy
- ✅ **Filtro stock**: Solo prodotti con ≥ 5 unità disponibili
- ✅ **HTML separati**: Anteprima dedicata per ogni paese
- ✅ **Italia supportata**: Paese aggiunto con traduzioni italiane
- ✅ **Migliore qualità**: Prodotti sempre disponibili per la vendita
