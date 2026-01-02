#!/usr/bin/env python3
"""
MLB Qualifying Offer Calculator
Computes the average of top 125 salaries from the latest season.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Dict

import requests
from bs4 import BeautifulSoup

SALARY_DATA_ENDPOINT = "https://questionnaire-148920.appspot.com/swe/data.html"
THRESHOLD_COUNT = 125


@dataclass
class PlayerSalaryRecord:
    player: str
    amount: Decimal
    season: int
    league: str


@dataclass
class ParseMetrics:
    rows_total: int = 0
    rows_parsed: int = 0
    rows_dropped: int = 0
    bad_amounts: int = 0
    bad_seasons: int = 0
    missing_league: int = 0
    non_major_league: int = 0
    seasons_detected: set = None
    
    def __post_init__(self):
        if self.seasons_detected is None:
            self.seasons_detected = set()


def fetch_html_content(endpoint: str = SALARY_DATA_ENDPOINT) -> str:
    try:
        resp = requests.get(endpoint, timeout=15)
        resp.raise_for_status()
    except requests.Timeout:
        sys.exit(f"Connection timed out fetching {endpoint}")
    except requests.ConnectionError:
        sys.exit(f"Unable to reach {endpoint}. Check network.")
    except requests.RequestException as err:
        sys.exit(f"Request failed: {err}")
    return resp.text


def extract_decimal_amount(raw_text: str) -> Decimal | None:
    if not raw_text or not raw_text.strip():
        return None
    
    sanitized = re.sub(r"[^\d.]", "", raw_text)
    
    if not sanitized:
        return None
    
    if sanitized.count('.') > 1:
        fragments = sanitized.split('.')
        sanitized = fragments[0] + '.' + ''.join(fragments[1:])
    
    try:
        val = Decimal(sanitized)
        if val <= 0 or val > Decimal('100000000'):
            return None
        return val
    except (InvalidOperation, ValueError):
        return None


def extract_season_year(raw_text: str) -> int | None:
    if not raw_text or not raw_text.strip():
        return None
    
    digits = re.sub(r"[^\d]", "", raw_text)
    
    if not digits:
        return None
    
    try:
        yr = int(digits)
        if 1900 <= yr <= 2100:
            return yr
        return None
    except ValueError:
        return None


def extract_records_from_html(html_content: str) -> Tuple[List[PlayerSalaryRecord], ParseMetrics]:
    parser = BeautifulSoup(html_content, "html.parser")
    table_rows = parser.select("table#salaries-table tbody tr")
    
    records: List[PlayerSalaryRecord] = []
    metrics = ParseMetrics(rows_total=len(table_rows))
    
    for row in table_rows:
        name_elem = row.select_one(".player-name")
        amount_elem = row.select_one(".player-salary")
        season_elem = row.select_one(".player-year")
        league_elem = row.select_one(".player-level")
        
        player_name = name_elem.get_text(strip=True) if name_elem else ""
        
        raw_amount = amount_elem.get_text(strip=True) if amount_elem else ""
        parsed_amount = extract_decimal_amount(raw_amount)
        if not parsed_amount:
            metrics.bad_amounts += 1
        
        raw_season = season_elem.get_text(strip=True) if season_elem else ""
        parsed_season = extract_season_year(raw_season)
        if not parsed_season:
            metrics.bad_seasons += 1
        
        league_code = league_elem.get_text(strip=True) if league_elem else ""
        if not league_code:
            metrics.missing_league += 1
        
        if parsed_season:
            metrics.seasons_detected.add(parsed_season)
        
        if not (parsed_amount and parsed_season and league_code):
            metrics.rows_dropped += 1
            continue
        
        if league_code.upper() != "MLB":
            metrics.non_major_league += 1
        
        records.append(PlayerSalaryRecord(
            player=player_name,
            amount=parsed_amount,
            season=parsed_season,
            league=league_code
        ))
        metrics.rows_parsed += 1
    
    return records, metrics


def compute_offer_value(
    records: List[PlayerSalaryRecord], 
    threshold: int = THRESHOLD_COUNT
) -> Tuple[Decimal, List[PlayerSalaryRecord], int, Dict[str, int]]:
    
    mlb_only = [r for r in records if r.league.upper() == "MLB"]
    if not mlb_only:
        raise ValueError("No MLB records found")
    
    most_recent = max(r.season for r in mlb_only)
    
    current_season = [r for r in mlb_only if r.season == most_recent]
    
    if not current_season:
        raise ValueError(f"No MLB records for season {most_recent}")
    
    ranked = sorted(current_season, key=lambda r: r.amount, reverse=True)[:threshold]
    
    if not ranked:
        raise ValueError("Cannot compute offer - no valid records")
    
    aggregate = sum(r.amount for r in ranked)
    final_offer = (aggregate / Decimal(len(ranked))).quantize(Decimal("0.01"))
    
    analysis = {
        'mlb_total': len(mlb_only),
        'season_total': len(current_season),
        'used_count': len(ranked),
        'threshold': threshold,
        'floor_amount': min(r.amount for r in ranked),
        'ceiling_amount': max(r.amount for r in ranked),
    }
    
    return final_offer, ranked, most_recent, analysis


def format_money(amt: Decimal) -> str:
    normalized = amt.quantize(Decimal("0.01"))
    return f"${normalized:,.2f}"


def display_parse_metrics(metrics: ParseMetrics) -> None:
    print("\n" + "="*70)
    print("PARSING SUMMARY")
    print("="*70)
    print(f"Rows scanned:                 {metrics.rows_total:>6}")
    print(f"Rows successfully parsed:     {metrics.rows_parsed:>6}")
    print(f"Rows dropped:                 {metrics.rows_dropped:>6}")
    print(f"\nIssues encountered:")
    print(f"  Invalid amounts:            {metrics.bad_amounts:>6}")
    print(f"  Invalid seasons:            {metrics.bad_seasons:>6}")
    print(f"  Missing league info:        {metrics.missing_league:>6}")
    print(f"  Non-MLB records:            {metrics.non_major_league:>6}")
    print(f"\nSeasons in dataset: {sorted(metrics.seasons_detected)}")
    print("="*70)


def display_results(
    final_offer: Decimal, 
    ranked: List[PlayerSalaryRecord], 
    season: int,
    analysis: Dict[str, int]
) -> None:
    print("\n" + "="*70)
    print("QUALIFYING OFFER RESULT")
    print("="*70)
    print(f"\nSeason analyzed:              {season}")
    print(f"MLB players in season:        {analysis['season_total']:>6}")
    print(f"Top earners included:         {analysis['used_count']:>6} (threshold: {analysis['threshold']})")
    print(f"\nSalary bounds:")
    print(f"  Top earner:  {format_money(analysis['ceiling_amount'])}")
    print(f"  125th place: {format_money(analysis['floor_amount'])}")
    
    print(f"\n{'='*70}")
    print(f"QUALIFYING OFFER: {format_money(final_offer)}")
    print(f"{'='*70}")
    
    preview = min(10, len(ranked))
    print(f"\nTop {preview} Earners:")
    print("-" * 70)
    print(f"{'#':<6} {'Player':<30} {'Salary':>15}")
    print("-" * 70)
    
    for idx, rec in enumerate(ranked[:preview], start=1):
        print(f"{idx:<6} {rec.player:<30} {format_money(rec.amount):>15}")
    
    if len(ranked) > preview:
        print(f"... plus {len(ranked) - preview} more")
    print("="*70 + "\n")


def main() -> None:
    print("Retrieving salary data...")
    
    try:
        html_content = fetch_html_content()
    except SystemExit:
        raise
    
    print("Processing records...")
    records, metrics = extract_records_from_html(html_content)
    
    display_parse_metrics(metrics)
    
    if not records:
        sys.exit("\nError: No valid records parsed")
    
    try:
        final_offer, ranked, season, analysis = compute_offer_value(records)
    except ValueError as err:
        sys.exit(f"\nError: {err}")
    
    display_results(final_offer, ranked, season, analysis)


if __name__ == "__main__":
    main()