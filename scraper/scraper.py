"""
scraper.py
----------
Live web scraper targeting BahtSold vehicle listings (bahtsold.com).
Falls back gracefully to a realistic mock data generator if the site
is unreachable, returns errors, or bot-detection triggers.

Techniques to avoid detection:
  - Random User-Agent rotation (fake_useragent)
  - Randomised request delays (jitter sleep)
  - Session reuse with keep-alive
  - Accept-Language / Accept headers mimicking a browser
"""

from __future__ import annotations

import csv
import os
import random
import time
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Iterator

import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.bahtsold.com"
LISTINGS_URL = f"{BASE_URL}/en/vehicles-for-sale"

REQUEST_TIMEOUT = 15          # seconds
MIN_DELAY = 1.5               # seconds between requests (jitter base)
MAX_DELAY = 4.0               # seconds between requests (jitter cap)
MAX_PAGES = 10                # hard cap on pages to scrape

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Listing:
    listing_id: str
    title: str
    make: str
    model: str
    year: int
    price: float          # Thai Baht
    mileage: float        # kilometres
    province: str
    vehicle_type: str     # "car" | "motorcycle"
    source: str           # "live" | "mock"
    scraped_at: str

    @classmethod
    def csv_headers(cls) -> list[str]:
        return [f.name for f in fields(cls)]

    def to_row(self) -> list:
        return [getattr(self, f.name) for f in fields(self)]


# ---------------------------------------------------------------------------
# HTTP session factory
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
    })
    return session


# ---------------------------------------------------------------------------
# BahtSold live scraper
# ---------------------------------------------------------------------------

class BahtSoldScraper:
    """
    Scrapes vehicle listings from bahtsold.com.

    Usage:
        scraper = BahtSoldScraper(max_pages=5)
        listings = list(scraper.scrape())
    """

    def __init__(self, max_pages: int = MAX_PAGES) -> None:
        self.max_pages = max_pages
        self.session = _make_session()
        self._scraped_ids: set[str] = set()

    def _get_page(self, url: str) -> BeautifulSoup | None:
        """Fetch a URL and return a BeautifulSoup object, or None on failure."""
        try:
            # Rotate User-Agent per request
            self.session.headers["User-Agent"] = random.choice(USER_AGENTS)
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as exc:
            console.print(f"[yellow]⚠  HTTP error on {url}: {exc}[/yellow]")
            return None

    @staticmethod
    def _parse_price(text: str) -> float:
        """Extract a numeric price from a Thai Baht string like '฿250,000'."""
        cleaned = text.replace("฿", "").replace(",", "").replace("THB", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_mileage(text: str) -> float:
        """Extract numeric km from strings like '45,000 km'."""
        cleaned = text.lower().replace("km", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _classify_type(title: str) -> str:
        motorcycles = [
            "motorcycle", "motorbike", "scooter", "bike", "moto",
            "cbr", "r15", "r3", "ninja", "pcx", "click", "wave",
            "cbf", "crf", "xsr", "mt-", "yzf", "z300", "z400",
        ]
        title_lower = title.lower()
        for kw in motorcycles:
            if kw in title_lower:
                return "motorcycle"
        return "car"

    def _parse_listing_card(self, card, page_index: int, card_index: int) -> Listing | None:
        """
        Parse a single listing card HTML element into a Listing object.
        BahtSold listing cards follow different layouts; we try multiple
        CSS selectors to be resilient against minor template changes.
        """
        now = datetime.utcnow().isoformat()

        # --- Title ---
        title_el = (
            card.select_one("h2.listing-title")
            or card.select_one("h3.listing-title")
            or card.select_one(".title")
            or card.select_one("[class*='title']")
            or card.select_one("a[href*='/listing/']")
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown"

        # --- Price ---
        price_el = (
            card.select_one(".listing-price")
            or card.select_one("[class*='price']")
            or card.select_one("span.price")
        )
        price_text = price_el.get_text(strip=True) if price_el else "0"
        price = self._parse_price(price_text)
        if price <= 0:
            return None  # skip invalid

        # --- Year ---
        year_el = card.select_one("[class*='year']") or card.select_one(".year")
        year = 0
        if year_el:
            txt = year_el.get_text(strip=True)
            digits = "".join(filter(str.isdigit, txt))
            year = int(digits[:4]) if len(digits) >= 4 else 0

        # fallback: extract year from title (e.g. "Toyota Camry 2020")
        if year == 0:
            words = title.split()
            for w in words:
                if w.isdigit() and 1990 <= int(w) <= datetime.now().year:
                    year = int(w)
                    break

        # --- Mileage ---
        mileage_el = (
            card.select_one("[class*='mileage']")
            or card.select_one("[class*='odometer']")
            or card.select_one(".km")
        )
        mileage = self._parse_mileage(mileage_el.get_text(strip=True)) if mileage_el else 0.0

        # --- Province / Location ---
        loc_el = (
            card.select_one("[class*='location']")
            or card.select_one("[class*='province']")
            or card.select_one(".location")
        )
        province = loc_el.get_text(strip=True) if loc_el else "Unknown"

        # --- Make / Model (derive from title) ---
        parts = title.split()
        make = parts[0] if parts else "Unknown"
        model = " ".join(parts[1:3]) if len(parts) >= 3 else (parts[1] if len(parts) == 2 else "Unknown")

        listing_id = f"live_{page_index}_{card_index}"
        if listing_id in self._scraped_ids:
            return None
        self._scraped_ids.add(listing_id)

        return Listing(
            listing_id=listing_id,
            title=title,
            make=make.title(),
            model=model.title(),
            year=year if year else 2018,
            price=price,
            mileage=mileage,
            province=province,
            vehicle_type=self._classify_type(title),
            source="live",
            scraped_at=now,
        )

    def _get_next_page_url(self, soup: BeautifulSoup, current_page: int) -> str | None:
        """Find the URL of the next page, or None if we're on the last page."""
        next_el = (
            soup.select_one("a[rel='next']")
            or soup.select_one(".pagination .next a")
            or soup.select_one("[class*='pagination'] [class*='next']")
        )
        if next_el and next_el.get("href"):
            href = next_el["href"]
            return href if href.startswith("http") else BASE_URL + href
        # fallback: construct page URL from pattern
        return f"{LISTINGS_URL}?page={current_page + 1}"

    def scrape(self) -> Iterator[Listing]:
        """Main scraping generator — yields Listing objects page by page."""
        url = LISTINGS_URL
        for page_num in range(1, self.max_pages + 1):
            console.print(f"[cyan]🌐  Scraping page {page_num}: {url}[/cyan]")
            soup = self._get_page(url)
            if soup is None:
                console.print("[red]✗  Failed to fetch page — stopping live scrape.[/red]")
                break

            # Find all listing cards (try multiple selectors)
            cards = (
                soup.select(".listing-card")
                or soup.select("[class*='listing-card']")
                or soup.select("[class*='vehicle-card']")
                or soup.select("article.listing")
                or soup.select(".post-listing")
            )

            if not cards:
                console.print(f"[yellow]⚠  No listing cards found on page {page_num}. "
                              "Site structure may have changed.[/yellow]")
                break

            page_listings = 0
            for idx, card in enumerate(cards):
                listing = self._parse_listing_card(card, page_num, idx)
                if listing:
                    page_listings += 1
                    yield listing

            console.print(f"[green]✓  Page {page_num}: extracted {page_listings} listings[/green]")

            if page_num < self.max_pages:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)
                url = self._get_next_page_url(soup, page_num)
                if url is None:
                    break


# ---------------------------------------------------------------------------
# Mock data generator (realistic Thai vehicle market simulation)
# ---------------------------------------------------------------------------

THAI_PROVINCES = [
    "Bangkok", "Chiang Mai", "Phuket", "Chonburi", "Khon Kaen",
    "Nonthaburi", "Pathum Thani", "Samut Prakan", "Udon Thani",
    "Surat Thani", "Nakhon Ratchasima", "Chiang Rai", "Rayong",
    "Hat Yai (Songkhla)", "Ubon Ratchathani", "Nakhon Sawan",
    "Lampang", "Saraburi", "Prachuap Khiri Khan", "Krabi",
]

CARS = [
    ("Toyota", "Camry",       950_000, 550_000, 8, 14, "car"),
    ("Toyota", "Corolla",     650_000, 300_000, 7, 13, "car"),
    ("Toyota", "Hilux Revo",  850_000, 450_000, 8, 12, "car"),
    ("Toyota", "Fortuner",    1_200_000, 600_000, 6, 10, "car"),
    ("Toyota", "Yaris",       450_000, 220_000, 8, 14, "car"),
    ("Toyota", "CHR",         750_000, 400_000, 5, 8,  "car"),
    ("Honda",  "Civic",       700_000, 350_000, 8, 13, "car"),
    ("Honda",  "City",        500_000, 220_000, 8, 14, "car"),
    ("Honda",  "HR-V",        700_000, 320_000, 7, 12, "car"),
    ("Honda",  "Jazz",        400_000, 180_000, 9, 14, "car"),
    ("Honda",  "CR-V",        900_000, 450_000, 7, 12, "car"),
    ("Isuzu",  "D-Max",       750_000, 380_000, 8, 13, "car"),
    ("Ford",   "Ranger",      800_000, 400_000, 7, 12, "car"),
    ("Ford",   "EcoSport",    500_000, 240_000, 8, 13, "car"),
    ("Nissan", "Navara",      750_000, 350_000, 8, 13, "car"),
    ("Nissan", "Almera",      450_000, 200_000, 8, 14, "car"),
    ("Nissan", "Note",        400_000, 180_000, 8, 14, "car"),
    ("Mitsubishi", "Triton",  700_000, 350_000, 8, 13, "car"),
    ("Mitsubishi", "Pajero",  1_100_000, 550_000, 7, 12, "car"),
    ("Mazda",  "3",           650_000, 300_000, 8, 13, "car"),
    ("Mazda",  "CX-5",        900_000, 450_000, 6, 10, "car"),
    ("Suzuki", "Swift",       400_000, 180_000, 9, 14, "car"),
    ("BMW",    "Series 3",    1_800_000, 900_000, 7, 12, "car"),
    ("Mercedes-Benz", "C-Class", 2_200_000, 1_100_000, 6, 10, "car"),
]

MOTORCYCLES = [
    ("Honda",    "PCX 160",   90_000,  40_000, 5, 8,  "motorcycle"),
    ("Honda",    "Wave 110",  35_000,  15_000, 8, 14, "motorcycle"),
    ("Honda",    "CBR 150R",  90_000,  40_000, 6, 10, "motorcycle"),
    ("Honda",    "Click 150", 50_000,  20_000, 7, 12, "motorcycle"),
    ("Yamaha",   "NMAX 155",  85_000,  38_000, 5, 8,  "motorcycle"),
    ("Yamaha",   "Aerox 155", 78_000,  35_000, 5, 8,  "motorcycle"),
    ("Yamaha",   "R15",       100_000, 45_000, 5, 8,  "motorcycle"),
    ("Yamaha",   "MT-15",     95_000,  42_000, 5, 8,  "motorcycle"),
    ("Kawasaki", "Ninja 300", 130_000, 60_000, 6, 10, "motorcycle"),
    ("Kawasaki", "Z400",      180_000, 85_000, 5, 8,  "motorcycle"),
    ("Suzuki",   "GSX-S150",  70_000,  30_000, 6, 10, "motorcycle"),
]

ALL_VEHICLES = CARS + MOTORCYCLES


def generate_mock_data(n: int = 600, seed: int = 42) -> list[Listing]:
    """
    Generate `n` realistic synthetic Thai vehicle listings.
    Approximately 15% of listings are intentionally priced 15-35% below
    their model median to ensure the deal-finder engine has data to surface.
    """
    rng = random.Random(seed)
    listings: list[Listing] = []
    now = datetime.utcnow().isoformat()

    current_year = datetime.now().year

    for i in range(n):
        make, model, price_new, price_floor, age_min, age_max, vtype = rng.choice(ALL_VEHICLES)

        age = rng.randint(age_min - 2, age_max)
        age = max(0, age)
        year = current_year - age

        # Depreciation: simple exponential decay
        depreciation_factor = 0.88 ** age          # ~12% per year
        base_price = price_new * depreciation_factor
        base_price = max(base_price, price_floor)

        # Add realistic scatter ±10%
        scatter = rng.uniform(0.90, 1.10)
        price = base_price * scatter

        # ~15% of listings are undervalued deals
        is_deal = rng.random() < 0.15
        if is_deal:
            discount = rng.uniform(0.15, 0.35)
            price *= (1.0 - discount)

        price = round(price / 1000) * 1000  # round to nearest 1k THB

        # Mileage correlated with age + scatter
        avg_km_per_year = rng.randint(10_000, 20_000)
        mileage = age * avg_km_per_year * rng.uniform(0.7, 1.3)
        mileage = round(mileage / 100) * 100

        province = rng.choice(THAI_PROVINCES)

        listings.append(Listing(
            listing_id=f"mock_{i:04d}",
            title=f"{make} {model} {year}",
            make=make,
            model=model,
            year=year,
            price=float(price),
            mileage=float(mileage),
            province=province,
            vehicle_type=vtype,
            source="mock",
            scraped_at=now,
        ))

    console.print(f"[green]✓  Generated {len(listings)} mock listings "
                  f"(~{sum(1 for l in listings if l.source == 'mock')} total)[/green]")
    return listings


# ---------------------------------------------------------------------------
# CSV writer helper
# ---------------------------------------------------------------------------

def save_raw_csv(listings: list[Listing], output_path: Path) -> None:
    """Write a list of Listing objects to a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(Listing.csv_headers())
        for listing in listings:
            writer.writerow(listing.to_row())
    console.print(f"[green]✓  Raw CSV saved → {output_path}[/green]")
