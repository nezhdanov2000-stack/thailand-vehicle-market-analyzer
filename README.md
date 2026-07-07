# 🚗 Automated Local Vehicle Market Analyzer & Deal Finder (Thailand)

> **Portfolio Project** · Data Analyst / Automation Developer  
> _Automated end-to-end pipeline: web scraping → data cleaning → EDA → statistical deal detection → interactive dashboard_

---

## 📌 Overview

This tool automatically scrapes vehicle listings from **BahtSold** (Thailand's leading classifieds platform), cleans and processes the data with **pandas**, performs **Exploratory Data Analysis**, and runs a **statistical rule-based algorithm** to surface vehicles priced **≥15% below their peer-group market median** — a curated list of undervalued deals.

---

## 🏗 Project Structure

```
portfolio/
├── scraper/
│   └── scraper.py        # BeautifulSoup + requests · live BahtSold scraper + mock generator
├── pipeline/
│   └── cleaner.py        # pandas cleaning · dedup · anomaly removal · feature engineering
├── analysis/
│   └── eda.py            # Depreciation analysis · median pricing · Jupyter notebook generator
├── engine/
│   └── deal_finder.py    # Statistical deal-flagging algorithm · composite scoring
├── dashboard/            # Vite + Chart.js interactive dashboard
│   ├── src/
│   │   ├── charts/       # Scatter · Depreciation · Province · Median Age charts
│   │   └── components/   # KPI cards · Deals table
│   └── public/data/      # ← pipeline outputs are copied here automatically
├── data/
│   ├── raw/              # Raw scraped CSVs
│   └── processed/        # Cleaned + feature-engineered CSVs
├── outputs/
│   ├── top_deals.csv     # Curated top N deals
│   └── market_stats.json # Aggregated statistics (consumed by dashboard)
├── notebooks/
│   ├── eda_report.ipynb  # Auto-generated Jupyter notebook
│   └── eda_report.md     # Exported markdown summary
└── main.py               # CLI entry point
```

---

## ⚡ Quick Start

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the full pipeline

```bash
# Live scrape BahtSold + pipeline (may fall back to mock if site is blocked)
python main.py

# Use synthetic mock data (always works, great for demos)
python main.py --mock

# Re-run analysis on existing data (skip scraping)
python main.py --skip-scrape --top 30
```

### 3. Launch the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

---

## 🔧 CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--mock` | off | Use synthetic data (no network required) |
| `--skip-scrape` | off | Reuse existing raw CSV |
| `--top N` | 20 | Number of top deals to output |
| `--pages N` | 10 | Max BahtSold pages to scrape |
| `--threshold N` | 15.0 | Min % below median to flag as deal |
| `--mock-size N` | 600 | Number of mock listings to generate |

---

## 🧠 How It Works

### Stage 1 · Data Collection (scraper/scraper.py)
- Requests BahtSold vehicle listings with rotating User-Agents and jitter delays
- Parses title, price, year, mileage, and province using BeautifulSoup
- Falls back to a realistic **600-listing mock generator** if the site is unreachable
- Outputs: `data/raw/raw_listings.csv`

### Stage 2 · Data Cleaning (pipeline/cleaner.py)
- Coerces types, removes exact and key-column duplicates
- Filters price anomalies (cars: ฿30k–฿8M, motorcycles: ฿5k–฿1M)
- Fills missing mileage with per-model medians
- Standardises province names (e.g. "BKK" → "Bangkok")
- Engineers `vehicle_age` and `age_bucket` features
- Outputs: `data/processed/cleaned_listings.csv`

### Stage 3 · EDA (analysis/eda.py)
- Computes annual depreciation rates per make (log-linear regression)
- Calculates median prices by (vehicle_type × age_bucket)
- Generates province-level listing density + pricing stats
- Auto-generates `notebooks/eda_report.ipynb` (runnable Jupyter notebook)
- Exports `notebooks/eda_report.md` (markdown summary)

### Stage 4 · Deal Finder (engine/deal_finder.py)
- Computes peer-group median for each (make × model × age_bucket)
- Calculates `discount_pct = (median − price) / median × 100`
- Flags listings with `discount_pct ≥ 15%`
- Scores deals via composite formula:
  ```
  score = 0.55 × discount_pct_norm
        + 0.25 × (1 − mileage_percentile)
        + 0.20 × province_desirability
  ```
- Outputs: `outputs/top_deals.csv`, `outputs/market_stats.json`

### Stage 5 · Dashboard Sync
- Copies all outputs to `dashboard/public/data/` for the Vite dev server

---

## 📊 Dashboard Features

| Widget | Description |
|--------|-------------|
| KPI Cards | Total listings · Market median · Deals found · Avg discount · Avg saving |
| Price vs Age Scatter | All listings; deals highlighted as amber stars |
| Depreciation Curves | Median price by age for top 6 makes |
| Province Density | Horizontal bar chart of listing counts by region |
| Median by Age Bucket | Grouped bars: Cars vs Motorcycles |
| Top Deals Table | Sortable · Searchable · Filterable by type · Discount badges · Score bars |

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Scraping | Python · requests · BeautifulSoup4 · lxml |
| Data Processing | pandas · NumPy |
| EDA & Notebooks | nbformat (programmatic `.ipynb` generation) |
| CLI | argparse · Rich (console UI) |
| Dashboard | Vite · Vanilla JS · Chart.js · PapaParse |

---

## 📈 Impact

- **End-to-end automation**: zero manual steps from data collection to deal surfacing
- **Bot-detection resistance**: jitter delays, User-Agent rotation, session keep-alive
- **Statistical rigour**: peer-group medians, log-linear depreciation modelling
- **Portfolio-ready dashboard**: dark glassmorphism UI with 4 chart types and interactive table

---

## 📄 License

MIT — free to use and adapt for personal or commercial projects.
