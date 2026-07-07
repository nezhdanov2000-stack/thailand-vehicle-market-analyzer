"""
deal_finder.py
--------------
Statistical rule-based algorithm that identifies undervalued vehicle listings.

Algorithm:
  1. Compute peer-group median price for each (make, model, age_bucket)
  2. Calculate discount_pct = (median - price) / median × 100
  3. Flag listings with discount_pct ≥ 15% as deals
  4. Score each deal using a composite formula:
       score = 0.55 × discount_pct_norm
             + 0.25 × (1 - mileage_percentile_norm)
             + 0.20 × province_desirability_norm
  5. Rank deals and return the top N
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Province desirability scores (demand-side proxy)
# Scores are 0–1; Bangkok / Chiang Mai have highest buyer demand
# ---------------------------------------------------------------------------

PROVINCE_DESIRABILITY = {
    "Bangkok":              1.00,
    "Chiang Mai":           0.90,
    "Phuket":               0.85,
    "Chonburi":             0.80,
    "Nonthaburi":           0.75,
    "Pathum Thani":         0.72,
    "Samut Prakan":         0.70,
    "Rayong":               0.65,
    "Hat Yai (Songkhla)":  0.60,
    "Khon Kaen":            0.55,
    "Udon Thani":           0.52,
    "Nakhon Ratchasima":    0.50,
    "Surat Thani":          0.48,
    "Chiang Rai":           0.45,
    "Ubon Ratchathani":     0.40,
    "Nakhon Sawan":         0.38,
    "Saraburi":             0.35,
    "Lampang":              0.32,
    "Prachuap Khiri Khan":  0.30,
    "Krabi":                0.28,
}

DEAL_THRESHOLD_PCT = 15.0    # minimum discount to qualify as a deal
SCORE_WEIGHTS = {
    "discount":    0.55,
    "mileage":     0.25,
    "desirability": 0.20,
}


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _compute_peer_medians(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute median price per peer group (make × model × age_bucket).
    Falls back to (make × age_bucket) for models with < 3 listings.
    """
    df = df.copy()

    # Primary grouping: make + model + age_bucket
    peer_median = (
        df.groupby(["make", "model", "age_bucket"])["price"]
        .transform("median")
    )
    peer_count = (
        df.groupby(["make", "model", "age_bucket"])["price"]
        .transform("count")
    )

    # Fallback grouping for sparse models: make + age_bucket
    fallback_median = (
        df.groupby(["make", "age_bucket"])["price"]
        .transform("median")
    )

    df["peer_median"] = np.where(peer_count >= 3, peer_median, fallback_median)
    df["peer_count"]  = peer_count
    return df


def _score_deal(row: pd.Series, mileage_p75: float) -> float:
    """
    Composite deal score in range [0, 1].
    Higher = better deal.
    """
    # Discount component (0–1, capped at 40% discount)
    discount_norm = min(row["discount_pct"] / 40.0, 1.0)

    # Mileage component: lower mileage → higher score
    mileage_norm = 1.0 - min(row["mileage"] / (mileage_p75 * 2), 1.0)

    # Province desirability
    desirability = PROVINCE_DESIRABILITY.get(row["province"], 0.3)

    score = (
        SCORE_WEIGHTS["discount"]     * discount_norm
        + SCORE_WEIGHTS["mileage"]    * mileage_norm
        + SCORE_WEIGHTS["desirability"] * desirability
    )
    return round(score, 4)


def find_deals(
    df: pd.DataFrame,
    output_path: Path,
    stats_path: Path,
    top_n: int = 20,
    threshold_pct: float = DEAL_THRESHOLD_PCT,
) -> pd.DataFrame:
    """
    Identify undervalued vehicle listings and output the top deals.

    Parameters
    ----------
    df:           Cleaned DataFrame from the pipeline.
    output_path:  Path to save the top_deals CSV.
    stats_path:   Path to save market stats JSON (for the dashboard).
    top_n:        Number of top deals to return.
    threshold_pct: Minimum % below median to flag as a deal.

    Returns
    -------
    DataFrame of top N deals with scoring columns.
    """
    console.rule("[bold cyan]Deal Finder Engine[/bold cyan]")

    if df.empty:
        console.print("[red]✗  Empty DataFrame — cannot find deals.[/red]")
        return pd.DataFrame()

    # Step 1: Compute peer-group medians
    df = _compute_peer_medians(df)

    # Step 2: Compute discount percentage
    df["discount_pct"] = (
        (df["peer_median"] - df["price"]) / df["peer_median"] * 100
    ).round(2)

    # Step 3: Filter deals
    deals = df[df["discount_pct"] >= threshold_pct].copy()
    console.print(
        f"  Found [bold green]{len(deals):,}[/bold green] listings priced ≥{threshold_pct}% "
        f"below peer median out of {len(df):,} total"
    )

    if deals.empty:
        console.print("[yellow]⚠  No deals found at current threshold.[/yellow]")
        return deals

    # Step 4: Score each deal
    mileage_p75 = df["mileage"].quantile(0.75)
    deals["deal_score"] = deals.apply(
        lambda row: _score_deal(row, mileage_p75), axis=1
    )

    # Saving price (estimated flip value)
    deals["saving_thb"] = (deals["peer_median"] - deals["price"]).round(0)

    # Step 5: Rank and select top N
    top_deals = (
        deals
        .sort_values("deal_score", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    # Select relevant output columns
    out_cols = [
        "listing_id", "title", "make", "model", "year", "vehicle_type",
        "price", "peer_median", "discount_pct", "saving_thb", "deal_score",
        "mileage", "province", "age_bucket", "vehicle_age", "source",
    ]
    out_cols = [c for c in out_cols if c in top_deals.columns]
    top_deals = top_deals[out_cols]

    # Step 6: Save CSVs
    output_path.parent.mkdir(parents=True, exist_ok=True)
    top_deals.to_csv(output_path, index=False)
    console.print(f"[green]✓  Top {len(top_deals)} deals saved → {output_path}[/green]")

    # Save all deals (for dashboard scatter)
    all_deals_path = output_path.parent / "all_flagged_deals.csv"
    deals[out_cols].sort_values("deal_score", ascending=False).to_csv(
        all_deals_path, index=False
    )

    # Step 7: Save market stats JSON for the dashboard
    market_stats = {
        "total_listings": int(len(df)),
        "deal_count": int(len(deals)),
        "top_deal_count": int(len(top_deals)),
        "deal_rate_pct": round(len(deals) / len(df) * 100, 1),
        "avg_discount_pct": round(deals["discount_pct"].mean(), 1),
        "max_discount_pct": round(deals["discount_pct"].max(), 1),
        "avg_saving_thb": int(deals["saving_thb"].mean()),
        "max_saving_thb": int(deals["saving_thb"].max()),
        "overall_median_price": int(df["price"].median()),
        "car_median_price": int(df[df["vehicle_type"] == "Car"]["price"].median()) if (df["vehicle_type"] == "Car").any() else 0,
        "moto_median_price": int(df[df["vehicle_type"] == "Motorcycle"]["price"].median()) if (df["vehicle_type"] == "Motorcycle").any() else 0,
        "threshold_pct": threshold_pct,
        # Serialise processed listings for dashboard scatter chart (sample 500)
        "scatter_data": df[["vehicle_age", "price", "vehicle_type", "make", "model", "discount_pct"]]
            .sample(min(500, len(df)), random_state=42)
            .round(0)
            .to_dict(orient="records"),
        # Province chart data
        "province_data": (
            df.groupby("province")["price"]
            .agg(count="count", median="median")
            .reset_index()
            .sort_values("count", ascending=False)
            .head(15)
            .to_dict(orient="records")
        ),
        # Depreciation data (make + median by age)
        "depreciation_data": (
            df.groupby(["make", "vehicle_age"])["price"]
            .median()
            .reset_index()
            .rename(columns={"price": "median_price"})
            .to_dict(orient="records")
        ),
    }

    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(market_stats, f, indent=2, default=str)
    console.print(f"[green]✓  Market stats JSON saved → {stats_path}[/green]")

    # Step 8: Console summary
    table = Table(title=f"🏆 Top {min(10, len(top_deals))} Deals",
                  show_header=True, header_style="bold yellow")
    table.add_column("#",            width=3,  justify="right")
    table.add_column("Title",        width=28)
    table.add_column("Price (฿)",    width=12, justify="right")
    table.add_column("Market (฿)",   width=12, justify="right")
    table.add_column("Discount",     width=9,  justify="right")
    table.add_column("Saving (฿)",   width=11, justify="right")
    table.add_column("Score",        width=7,  justify="right")
    table.add_column("Province",     width=18)

    for i, (_, row) in enumerate(top_deals.head(10).iterrows(), 1):
        table.add_row(
            str(i),
            row["title"][:27],
            f"{int(row['price']):,}",
            f"{int(row['peer_median']):,}",
            f"[green]{row['discount_pct']:.1f}%[/green]",
            f"{int(row['saving_thb']):,}",
            f"{row['deal_score']:.3f}",
            str(row["province"]),
        )
    console.print(table)

    return top_deals
