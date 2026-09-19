#!/usr/bin/env python3
"""Parse scraped agreement detail HTML into a structured JSON dataset."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

BASE_URL = "https://www.service4mobility.com"


# Display names diverge from the portal's raw "Host country" value.
COUNTRY_DISPLAY_NAMES = {
    "China (Hong Kong)": "Hong Kong (China)",
    "China (Taiwan)": "Taiwan",
}


def display_country(value: str) -> str:
    stripped = (value or "").strip()
    return COUNTRY_DISPLAY_NAMES.get(stripped, value)


def clean_value(soup: BeautifulSoup, node: Any) -> str:
    if node is None:
        return ""

    # Work on a clone so we don't mutate the parsed document
    clone = BeautifulSoup(str(node), "html.parser").find()

    yes_no_map = {
        "/europe/images/haken3.gif": "Yes",
        "/europe/images/haken2.gif": "Yes",
        "/europe/images/haken.gif": "Yes",
        "/europe/images/cancel.gif": "No",
    }

    for img in clone.find_all("img"):
        src = img.get("src", "")
        replacement = yes_no_map.get(src)
        if replacement is None:
            replacement = ""
        img.replace_with(replacement)

    for a in clone.find_all("a"):
        href = a.get("href", "").strip()
        text = a.get_text(" ", strip=True)
        if href.startswith("/"):
            href = BASE_URL + href
        if href and text:
            a.replace_with(f"{text} ({href})")
        elif text:
            a.replace_with(text)
        elif href:
            a.replace_with(href)
        else:
            a.replace_with("")

    # Add line breaks for common block/separator tags
    for tag in clone.find_all(["br", "p", "div", "li"]):
        if tag.name in ("br",):
            tag.replace_with("\n")
        else:
            tag.insert_after("\n")

    text = clone.get_text(" ", strip=True)
    # Collapse multiple newlines/whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def parse_detail_html(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    fields: dict[str, str] = {}

    for row in soup.find_all("div", class_=lambda c: c and "form-group" in c and "row" in c):
        label_tag = row.find("label", class_=lambda c: c and "col-form-label" in c)
        if not label_tag:
            continue
        label = label_tag.get_text(" ", strip=True)
        if not label or label.lower() == "null":
            continue

        value_tag = row.find("div", class_=lambda c: c and "form-control-plaintext" in c)
        if not value_tag:
            continue

        value = clean_value(soup, value_tag)
        fields[label] = value

    partner = fields.get("Partner institution", "")
    host_country = display_country(fields.get("Host country", ""))
    if "Host country" in fields:
        fields["Host country"] = host_country
    return {
        "partner": partner,
        "partnerName": "",
        "hostCountry": host_country,
        "fields": fields,
    }


def main() -> None:
    root = Path(__file__).parent.parent
    html_dir = root / "data" / "agreement_details"
    meta_path = root / "data" / "agreement_details_metadata.json"
    out_path = root / "src" / "assets" / "data" / "agreement_details.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    details: dict[str, Any] = {}
    seen: set[tuple[str, str, tuple[tuple[str, str], ...]]] = set()

    for rec in meta.get("records", []):
        filename = rec.get("filename")
        token = rec.get("agreement_match")
        if not filename or not token:
            continue
        html_path = html_dir / filename
        if not html_path.exists():
            continue
        parsed = parse_detail_html(html_path.read_text(encoding="utf-8"))
        parsed["portalUrl"] = rec.get("detail_url", "")
        parsed["partnerName"] = rec.get("partner_name", "")

        # Deduplicate exact field-for-field repeats caused by duplicate fetches.
        key = (
            parsed["partner"],
            parsed["hostCountry"],
            tuple(sorted(parsed["fields"].items())),
        )
        if key in seen:
            continue
        seen.add(key)
        details[token] = parsed

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "total": len(details),
        "details": details,
    }
    out_path.write_text(json.dumps(output), encoding="utf-8")
    print(f"Wrote {len(details)} parsed agreement details to {out_path}")


if __name__ == "__main__":
    main()
