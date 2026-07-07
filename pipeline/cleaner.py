"""
cleaner.py
----------
pandas-based data cleaning and feature engineering pipeline.

Steps:
  1. Load raw CSV
  2. Coerce and validate data types
  3. Drop exact duplicates
  4. Remove price anomalies (too low or too high)
  5. Fill missing mileage with per-model median
  6. Standardise province names
  7. Derive vehicle_age and age_bucket features
  8. Save cleaned CSV to data/processed/
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Province name standardisation map
# ---------------------------------------------------------------------------

PROVINCE_MAP = {
    "bkk": "Bangkok",
    "bangkok": "Bangkok",
    "กรุงเทพ": "Bangkok",
    "กรุงเทพมหานคร": "Bangkok",
    "chiangmai": "Chiang Mai",
    "chiang mai": "Chiang Mai",
    "เชียงใหม่": "Chiang Mai",
    "phuket": "Phuket",
    "ภูเก็ต": "Phuket",
    "chonburi": "Chonburi",
    "ชลบุรี": "Chonburi",
    "pattaya": "Chonburi",
    "khonkaen": "Khon Kaen",
    "khon kaen": "Khon Kaen",
    "nonthaburi": "Nonthaburi",
    "pathumthani": "Pathum Thani",
    "pathum thani": "Pathum Thani",
    "samutprakan": "Samut Prakan",
    "samut prakan": "Samut Prakan",
    "udonthani": "Udon Thani",
    "udon thani": "Udon Thani",
    "surathani": "Surat Thani",
    "surat thani": "Surat Thani",
    "nakornratchasima": "Nakhon Ratchasima",
    "nakhon ratchasima": "Nakhon Ratchasima",
    "korat": "Nakhon Ratchasima",
    "chiangrai": "Chiang Rai",
    "chiang rai": "Chiang Rai",
    "rayong": "Rayong",
    "hat yai": "Hat Yai (Songkhla)",
    "hatyai": "Hat Yai (Songkhla)",
    "songkhla": "Hat Yai (Songkhla)",
}

CURRENT_YEAR = datetime.now().year
AGE_BINS = [0, 2, 5, 10, float("inf")]
AGE_LABELS = ["0-2 yrs", "3-5 yrs", "6-10 yrs", "10+ yrs"]

# Price sanity bounds (Thai Baht)
MIN_PRICE_CAR = 30_000
MAX_PRICE_CAR = 8_000_000
MIN_PRICE_MOTO = 5_000
MAX_PRICE_MOTO = 1_000_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _standardise_province(name: str) -> str:
    if not isinstance(name, str):
        return "Unknown"
    key = name.strip().lower()
    return PROVINCE_MAP.get(key, name.strip().title())


def _fill_mileage(df: pd.DataFrame) -> pd.DataFrame:
    """Fill zero/NaN mileage with the per-model median derived from age."""
    mask = df["mileage"].isna() | (df["mileage"] == 0)
    if mask.sum() == 0:
        return df

    # Estimate: 15,000 km/year × vehicle_age as fallback
    df.loc[mask, "mileage"] = df.loc[mask, "vehicle_age"] * 15_000

    # Per-model median fill (second pass)
    medians = df.groupby(["make", "model"])["mileage"].transform("median")
    still_zero = df["mileage"].isna() | (df["mileage"] == 0)
    df.loc[still_zero, "mileage"] = medians[still_zero]

    return df


# ---------------------------------------------------------------------------
# Main cleaning pipeline
# ---------------------------------------------------------------------------

def clean_listings(raw_path: Path, output_path: Path) -> pd.DataFrame:
    """
    Load the raw CSV, apply all cleaning steps, and save the processed CSV.

    Parameters
    ----------
    raw_path:   Path to raw CSV written by the scraper.
    output_path: Path where the cleaned CSV will be saved.

    Returns
    -------
    Cleaned pandas DataFrame.
    """
    console.rule("[bold cyan]Data Cleaning Pipeline[/bold cyan]")

    # 1. Load
    df = pd.read_csv(raw_path, dtype=str)
    console.print(f"  Loaded {len(df):,} raw rows from [bold]{raw_path.name}[/bold]")

    initial_count = len(df)

    # 2. Coerce types
    df["year"]    = pd.to_numeric(df["year"],    errors="coerce").astype("Int64")
    df["price"]   = pd.to_numeric(df["price"],   errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")

    # Clamp year to plausible range
    df = df[df["year"].between(1990, CURRENT_YEAR + 1)]

    # 3. Drop exact duplicates (all columns)
    before_dedup = len(df)
    df.drop_duplicates(inplace=True)
    dup_dropped = before_dedup - len(df)

    # Also deduplicate on (make, model, year, price, mileage, province)
    key_cols = ["make", "model", "year", "price", "mileage", "province"]
    before_key_dedup = len(df)
    df.drop_duplicates(subset=key_cols, inplace=True)
    key_dup_dropped = before_key_dedup - len(df)

    console.print(f"  Removed {dup_dropped + key_dup_dropped:,} duplicate rows")

    # 4. Remove price anomalies
    cars  = df["vehicle_type"] == "car"
    motos = df["vehicle_type"] == "motorcycle"

    price_mask = (
        (cars  & df["price"].between(MIN_PRICE_CAR,  MAX_PRICE_CAR))  |
        (motos & df["price"].between(MIN_PRICE_MOTO, MAX_PRICE_MOTO)) |
        (~cars & ~motos & df["price"].between(MIN_PRICE_CAR, MAX_PRICE_CAR))
    )
    anomaly_count = (~price_mask).sum()
    df = df[price_mask].copy()
    console.print(f"  Removed {anomaly_count:,} price anomalies")

    # 5. Drop rows with missing critical fields
    before_dropna = len(df)
    df.dropna(subset=["make", "model", "price"], inplace=True)
    console.print(f"  Dropped {before_dropna - len(df):,} rows with missing make/model/price")

    # 6. Standardise province names
    df["province"] = df["province"].apply(_standardise_province)

    # 7. Feature engineering
    df["vehicle_age"] = (CURRENT_YEAR - df["year"].astype(int)).clip(lower=0)

    # Fill missing / zero mileage
    df = _fill_mileage(df)

    # Age bucket
    df["age_bucket"] = pd.cut(
        df["vehicle_age"],
        bins=AGE_BINS,
        labels=AGE_LABELS,
        right=True,
    ).astype(str)

    # Normalise string columns
    for col in ["make", "model", "province", "vehicle_type", "source"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title()

    # 8. Reset index
    df.reset_index(drop=True, inplace=True)

    # 9. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    # 10. Summary report
    final_count = len(df)
    removed_total = initial_count - final_count

    table = Table(title="Cleaning Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Raw rows",              f"{initial_count:,}")
    table.add_row("Cleaned rows",          f"{final_count:,}")
    table.add_row("Rows removed",          f"{removed_total:,}")
    table.add_row("Retention rate",        f"{final_count / initial_count * 100:.1f}%")
    table.add_row("Cars",                  f"{(df['vehicle_type'] == 'Car').sum():,}")
    table.add_row("Motorcycles",           f"{(df['vehicle_type'] == 'Motorcycle').sum():,}")
    table.add_row("Provinces covered",     f"{df['province'].nunique()}")
    table.add_row("Unique makes",          f"{df['make'].nunique()}")
    console.print(table)
    console.print(f"[green]✓  Processed CSV saved → {output_path}[/green]")

    return df
