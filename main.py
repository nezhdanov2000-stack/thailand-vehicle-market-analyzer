"""
main.py
-------
CLI entry point for the Automated Local Vehicle Market Analyzer.

Usage:
    python main.py               # Live scrape BahtSold + full pipeline
    python main.py --mock        # Use mock data (no network required)
    python main.py --skip-scrape # Re-use existing raw CSV, re-run pipeline
    python main.py --top 30      # Change number of top deals (default 20)
    python main.py --pages 5     # Max pages to scrape (default 10)
    python main.py --threshold 12 # Deal threshold % (default 15)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows so Rich emoji/special chars work correctly
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass  # Python < 3.7 fallback

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Project root
ROOT = Path(__file__).parent

# Create console with safe encoding for Windows
console = Console(highlight=False)

# Paths
RAW_CSV      = ROOT / "data" / "raw"  / "raw_listings.csv"
CLEAN_CSV    = ROOT / "data" / "processed" / "cleaned_listings.csv"
DEALS_CSV    = ROOT / "outputs" / "top_deals.csv"
STATS_JSON   = ROOT / "outputs" / "market_stats.json"
NOTEBOOKS    = ROOT / "notebooks"
DASH_PUBLIC  = ROOT / "dashboard" / "public" / "data"


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automated Local Vehicle Market Analyzer & Deal Finder (Thailand)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use synthetic mock data instead of live scraping",
    )
    parser.add_argument(
        "--skip-scrape", action="store_true",
        help="Skip scraping; reuse existing raw CSV",
    )
    parser.add_argument(
        "--top", type=int, default=20,
        help="Number of top deals to output (default: 20)",
    )
    parser.add_argument(
        "--pages", type=int, default=10,
        help="Max pages to scrape from BahtSold (default: 10)",
    )
    parser.add_argument(
        "--threshold", type=float, default=15.0,
        help="Minimum discount %% below median to flag as a deal (default: 15.0)",
    )
    parser.add_argument(
        "--mock-size", type=int, default=600,
        help="Number of mock listings to generate (default: 600)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def print_banner() -> None:
    banner = Text()
    banner.append("[CAR]  AUTOMATED LOCAL VEHICLE MARKET ANALYZER\n", style="bold cyan")
    banner.append("       Deal Finder -- Thailand (BahtSold)\n",       style="cyan")
    banner.append(f"       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(1, 4)))


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_scrape(args: argparse.Namespace) -> None:
    """Stage 1: Scrape or generate listings → raw CSV."""
    from scraper.scraper import BahtSoldScraper, generate_mock_data, save_raw_csv

    console.rule("[bold]Stage 1 · Data Collection[/bold]")

    if args.mock:
        console.print("[yellow]>> Mock mode -- generating synthetic data[/yellow]")
        listings = generate_mock_data(n=args.mock_size)
        save_raw_csv(listings, RAW_CSV)
        return

    # Live scrape with mock fallback
    console.print("[cyan]>> Attempting live scrape of BahtSold...[/cyan]")
    scraper = BahtSoldScraper(max_pages=args.pages)
    live_listings = list(scraper.scrape())

    if len(live_listings) < 20:
        console.print(
            f"[yellow]!! Only {len(live_listings)} live listings collected. "
            "Falling back to mock data to supplement.[/yellow]"
        )
        from scraper.scraper import generate_mock_data
        mock_listings = generate_mock_data(n=args.mock_size)
        listings = live_listings + mock_listings
    else:
        listings = live_listings

    console.print(f"[green]OK  Total listings collected: {len(listings):,}[/green]")
    save_raw_csv(listings, RAW_CSV)


def stage_clean() -> "pd.DataFrame":
    """Stage 2: Clean and engineer features → processed CSV."""
    from pipeline.cleaner import clean_listings
    console.rule("[bold]Stage 2 · Data Cleaning & Pipeline[/bold]")
    return clean_listings(RAW_CSV, CLEAN_CSV)


def stage_eda(df: "pd.DataFrame") -> dict:
    """Stage 3: Exploratory data analysis → notebook + markdown."""
    from analysis.eda import run_eda
    console.rule("[bold]Stage 3 · Exploratory Data Analysis[/bold]")
    return run_eda(df, CLEAN_CSV, NOTEBOOKS)


def stage_find_deals(df: "pd.DataFrame", args: argparse.Namespace) -> "pd.DataFrame":
    """Stage 4: Run deal-finding algorithm → top_deals CSV + JSON."""
    from engine.deal_finder import find_deals
    console.rule("[bold]Stage 4 · Deal Finder Engine[/bold]")
    return find_deals(
        df,
        output_path=DEALS_CSV,
        stats_path=STATS_JSON,
        top_n=args.top,
        threshold_pct=args.threshold,
    )


def stage_sync_dashboard() -> None:
    """Stage 5: Copy output files to dashboard/public/data/ for Vite dev server."""
    console.rule("[bold]Stage 5 · Sync Dashboard Data[/bold]")
    DASH_PUBLIC.mkdir(parents=True, exist_ok=True)

    files_to_copy = [
        (CLEAN_CSV,   DASH_PUBLIC / "cleaned_listings.csv"),
        (DEALS_CSV,   DASH_PUBLIC / "top_deals.csv"),
        (STATS_JSON,  DASH_PUBLIC / "market_stats.json"),
    ]

    # Also copy all_flagged_deals if it exists
    all_deals = ROOT / "outputs" / "all_flagged_deals.csv"
    if all_deals.exists():
        files_to_copy.append((all_deals, DASH_PUBLIC / "all_flagged_deals.csv"))

    for src, dst in files_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            console.print(f"[green]✓  Copied {src.name} → {dst}[/green]")
        else:
            console.print(f"[yellow]⚠  {src.name} not found — skipping[/yellow]")

    console.print(
        "\n[bold cyan]Dashboard is ready![/bold cyan]  "
        "Run [bold]cd dashboard && npm run dev[/bold] to open it."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    print_banner()

    try:
        # Stage 1: Collect data
        if not args.skip_scrape:
            stage_scrape(args)
        else:
            if not RAW_CSV.exists():
                console.print(
                    "[red]✗  --skip-scrape requested but no raw CSV found at "
                    f"{RAW_CSV}. Run without --skip-scrape first.[/red]"
                )
                sys.exit(1)
            console.print(f"[yellow]⏭  Skipping scrape — using {RAW_CSV}[/yellow]")

        # Stage 2: Clean
        df = stage_clean()

        # Stage 3: EDA
        stage_eda(df)

        # Stage 4: Deal finder
        top_deals = stage_find_deals(df, args)

        # Stage 5: Sync dashboard data
        stage_sync_dashboard()

        # Final summary
        console.rule()
        console.print(
            f"\n[bold green]DONE  Pipeline complete![/bold green]\n"
            f"   - Processed listings : {len(df):,}\n"
            f"   - Deals found        : {len(top_deals):,}\n"
            f"   - Top deals CSV      : [cyan]{DEALS_CSV}[/cyan]\n"
            f"   - Market stats JSON  : [cyan]{STATS_JSON}[/cyan]\n"
            f"   - EDA notebook       : [cyan]{NOTEBOOKS / 'eda_report.ipynb'}[/cyan]\n"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]!! Interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as exc:
        console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
