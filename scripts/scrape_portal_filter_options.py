#!/usr/bin/env python3
"""
Scrape static filter vocabularies from the UCPH Mobility-Online portal.

Fetches the search form HTML, parses every <select> and <input type="radio">
inside <form name="search_form">, captures human-readable labels, the hashed
field names, and each option's value/text.

Outputs:
  data/portal_filter_options.json  - structured vocabularies
  data/portal_form_params.json     - default form parameters (same shape as
                                     .firecrawl/portal_form_params.json)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PORTAL_URL = "https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01"


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch_html_with_requests() -> str | None:
    try:
        import requests
    except ImportError:
        return None
    try:
        r = requests.get(PORTAL_URL, timeout=60)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log(f"requests fetch failed: {e}")
        return None


def fetch_html_with_playwright() -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        log("Opening portal via Playwright...")
        page.goto(PORTAL_URL, wait_until="networkidle", timeout=120000)
        time.sleep(2)
        html = page.content()
        browser.close()
        return html


def strip_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\n", " ").replace("\r", " ")).strip()


def parse_field_label(form: BeautifulSoup, target_id: str) -> str | None:
    # Prefer explicit <label for="id">
    label = form.find("label", attrs={"for": target_id})
    if label:
        return strip_text(label.get_text())
    # Fallback: sibling label text before the control
    return None


def parse_options(select: BeautifulSoup) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for opt in select.find_all("option"):
        val = opt.get("value", "") or ""
        txt = strip_text(opt.get_text())
        if val and txt:
            options.append({"value": val, "text": txt})
    return options


def extract_fields(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", attrs={"name": "search_form"})
    if not form:
        log("WARN: <form name='search_form'> not found")
        return []

    fields: list[dict[str, Any]] = []

    for select in form.find_all("select"):
        field_id = select.get("id") or select.get("name")
        field_name = select.get("name") or select.get("id")
        if not field_name:
            continue
        label = parse_field_label(form, field_id) if field_id else None
        multiple = bool(select.get("multiple"))
        options = parse_options(select)
        fields.append(
            {
                "name": field_name,
                "id": field_id,
                "label": label,
                "type": "select-multiple" if multiple else "select",
                "options": options,
            }
        )

    # Group radio inputs by name
    radios_by_name: dict[str, dict[str, Any]] = {}
    for radio in form.find_all("input", attrs={"type": "radio"}):
        name = radio.get("name")
        value = radio.get("value", "")
        if not name:
            continue
        if name not in radios_by_name:
            radios_by_name[name] = {"name": name, "label": None, "type": "radio", "options": []}
        radios_by_name[name]["options"].append(
            {"value": value, "text": value, "checked": bool(radio.get("checked"))}
        )
    fields.extend(radios_by_name.values())

    return fields


def build_default_params(fields: list[dict[str, Any]]) -> dict[str, str]:
    params: dict[str, str] = {}
    for field in fields:
        name = field["name"]
        if field["type"] == "radio":
            selected = next((o for o in field["options"] if o.get("checked")), None)
            params[name] = selected["value"] if selected else ""
        elif field["type"] == "select-multiple":
            # Default selection is empty unless a selected option exists
            selected = [o["value"] for o in field["options"] if o.get("selected")]
            params[name] = selected[0] if selected else ""
        else:
            selected = next((o for o in field["options"] if o.get("selected")), None)
            params[name] = selected["value"] if selected else ""
    return params


def find_cpif_agree_name(html: str) -> str | None:
    for m in re.finditer(r"(cpif_[a-f0-9_]+_sep_[a-f0-9]+)=", html):
        snippet_after = html[m.end() : m.end() + 60]
        if re.search(r"['\"]?\s*\+\s*['\"]?cause", snippet_after):
            return m.group(1)
    return None


def main() -> None:
    log("Fetching portal search form...")
    html = fetch_html_with_requests()
    if html is None:
        log("Falling back to Playwright...")
        html = fetch_html_with_playwright()

    log("Parsing filter fields...")
    fields = extract_fields(html)

    options_path = OUT_DIR / "portal_filter_options.json"
    options_path.write_text(json.dumps(fields, indent=2), encoding="utf-8")
    log(f"Wrote {len(fields)} fields to {options_path}")

    params = build_default_params(fields)
    cpif_agree_name = find_cpif_agree_name(html)
    params_payload = {
        "params": params,
    }
    if cpif_agree_name:
        params_payload["cpif_agree_name"] = cpif_agree_name

    params_path = OUT_DIR / "portal_form_params.json"
    params_path.write_text(json.dumps(params_payload, indent=2), encoding="utf-8")
    log(f"Wrote default form params to {params_path}")


if __name__ == "__main__":
    main()
