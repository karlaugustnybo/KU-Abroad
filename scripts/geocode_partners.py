#!/usr/bin/env python3
"""Geocode partner institutions using Nominatim and (re)generate the address cache.

Usage:
    .venv/bin/python scripts/geocode_partners.py           # all partners
    .venv/bin/python scripts/geocode_partners.py --missing-only  # only missing partners

Outputs:
    .firecrawl/partner_addresses.json

Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
- Maximum 1 request per second.
- Provide a valid User-Agent with contact details.
- Do not use for bulk geocoding without permission; this is a one-off regeneration.
"""

from __future__ import annotations

import argparse
import html
import json
import time
import unicodedata
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARTNERS_PATH = PROJECT_ROOT / "data" / "partners_metadata.json"
OUTPUT_PATH = PROJECT_ROOT / ".firecrawl" / "partner_addresses.json"
OVERRIDES_PATH = PROJECT_ROOT / "scripts" / "geocode_overrides.json"

USER_AGENT = "KU-Abroad/0.1 (https://github.com/karlaugustnybo/KU-Abroad)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
REQUEST_DELAY = 1.1


def normalize(text: str) -> str:
    """ASCII-fold and lowercase a string for stable matching."""
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .strip()
    )


def build_queries(name: str, city: str, country: str) -> list[str]:
    """Return prioritized geocoding queries for a partner."""
    queries = []
    parts: list[str] = []
    if name:
        parts.append(name)
    if city:
        parts.append(city)
    if country:
        parts.append(country)
    if parts:
        queries.append(", ".join(parts))

    # Fallbacks
    if name and country:
        queries.append(f"{name}, {country}")
    if city and country:
        queries.append(f"{city}, {country}")
    if name:
        queries.append(name)
    # Country-only is too imprecise for a university map, so we avoid it.
    return queries


def geocode(session: requests.Session, query: str) -> tuple[float, float] | None:
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    try:
        response = session.get(NOMINATIM_URL, params=params, timeout=30)
        response.raise_for_status()
        results = response.json()
    except Exception as exc:
        print(f"    [ERROR] request failed for query '{query}': {exc}")
        return None

    if not results:
        return None

    try:
        lat = float(results[0]["lat"])
        lon = float(results[0]["lon"])
        return lat, lon
    except (KeyError, ValueError, TypeError) as exc:
        print(f"    [ERROR] unexpected response for query '{query}': {exc}")
        return None


def load_partners() -> list[dict]:
    with open(PARTNERS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_existing_addresses() -> list[dict]:
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            # Older versions of this file stored names with HTML entities
            # (e.g. &#39;). Normalize them back to real characters so the
            # same institution does not appear twice.
            for entry in data:
                entry["name"] = html.unescape(entry["name"])
            return data
    return []


def load_overrides() -> dict[str, dict[str, float]]:
    if OVERRIDES_PATH.exists():
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, dict):
                return data
    return {}


def main(missing_only: bool = False) -> None:
    partners = load_partners()
    existing = load_existing_addresses()
    overrides = load_overrides()

    # Seed the new result map with existing coordinates so we can keep stable
    # answers unless a fresh query resolves a previously missing institution.
    addresses: list[dict] = []
    seen_keys: set[str] = set()
    for entry in existing:
        key = normalize(entry["name"])
        if key and key not in seen_keys:
            addresses.append(
                {
                    "name": entry["name"],
                    "lat": entry.get("lat"),
                    "lon": entry.get("lon"),
                }
            )
            seen_keys.add(key)

    override_keys = {normalize(n) for n in overrides.keys()}

    targets = []
    for partner in partners:
        name = (partner.get("name") or "").strip()
        key = normalize(name)
        if not key:
            continue
        has_existing = any(
            a.get("lat") is not None and normalize(a["name"]) == key for a in addresses
        )
        has_override = key in override_keys
        if missing_only and (has_existing or has_override):
            continue
        targets.append(partner)

    failed: list[str] = []

    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        session.headers.update({"Accept-Language": "en"})

        for i, partner in enumerate(targets, start=1):
            name = (partner.get("name") or "").strip()
            key = normalize(name)

            city = (partner.get("city") or "").strip()
            country = (partner.get("country") or "").strip()
            queries = build_queries(name, city, country)
            coords: tuple[float, float] | None = None
            used_query = ""
            for query in queries:
                coords = geocode(session, query)
                if coords:
                    used_query = query
                    break
                # Respect rate limits even on failures.
                time.sleep(REQUEST_DELAY)

            if key not in seen_keys:
                if coords:
                    lat, lon = coords
                    print(
                        f"[{i:03d}/{len(targets)}] OK {name} "
                        f"({lat:.4f}, {lon:.4f}) [query: {used_query}]"
                    )
                    addresses.append({"name": name, "lat": lat, "lon": lon})
                    seen_keys.add(key)
                else:
                    print(f"[{i:03d}/{len(targets)}] FAIL {name}")
                    failed.append(name)
            elif coords:
                # Update an entry that previously existed but had no coordinates
                lat, lon = coords
                print(
                    f"[{i:03d}/{len(targets)}] UPDATE {name} "
                    f"({lat:.4f}, {lon:.4f}) [query: {used_query}]"
                )
                for a in addresses:
                    if normalize(a["name"]) == key:
                        a["lat"] = lat
                        a["lon"] = lon
                        break
            else:
                print(f"[{i:03d}/{len(targets)}] STILL_MISSING {name}")

            # Nominatim rate limit
            time.sleep(REQUEST_DELAY)

    # Apply manual overrides for institutions that Nominatim cannot resolve
    # directly (e.g. local-language names or very long official names).
    overrides = load_overrides()
    for raw_name, coords in overrides.items():
        key = normalize(raw_name)
        if not key:
            continue
        existing_entry = next(
            (a for a in addresses if normalize(a["name"]) == key), None
        )
        if existing_entry:
            if existing_entry.get("lat") is None:
                existing_entry["lat"] = coords["lat"]
                existing_entry["lon"] = coords["lon"]
                print(f"[OVERRIDE] {raw_name} ({coords['lat']}, {coords['lon']})")
                failed = [n for n in failed if normalize(n) != key]
        else:
            addresses.append({"name": raw_name, "lat": coords["lat"], "lon": coords["lon"]})
            seen_keys.add(key)
            print(f"[OVERRIDE] {raw_name} ({coords['lat']}, {coords['lon']})")

    # Remove any entries that still have no coordinates: they cannot be placed
    # on the map and are better represented without lat/lon than with a bogus
    # default location.
    addresses = [a for a in addresses if a.get("lat") is not None]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(addresses, fh, ensure_ascii=False, indent=2)

    print(f"\nWrote {len(addresses)} addresses to {OUTPUT_PATH}")
    if failed:
        print(f"Failed to geocode {len(failed)} institutions:")
        for name in failed:
            print(f"  - {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geocode partner institutions via Nominatim")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only query coordinates for institutions not already in the cache.",
    )
    args = parser.parse_args()
    main(missing_only=args.missing_only)
