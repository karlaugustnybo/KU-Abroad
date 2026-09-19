#!/usr/bin/env python3
"""
Map Faculty / Study area / Study field filters to partner institutions.

For each value of the Faculty, Study area and Study field filters on the UCPH
Mobility-Online portal, execute a filtered search in a single Playwright
browser session, collect the partner names that appear in the result map
(`plane_list`), and record which names are associated with each filter label.

Outputs:
  data/filter_partner_mappings.json
  data/study_field_to_metadata.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, APIResponse

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR
OUT_DIR.mkdir(parents=True, exist_ok=True)
PORTAL_URL = "https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01"
PORTAL_POST = "https://www.service4mobility.com/europe/PortalServlet"
MAPPINGS_PATH = OUT_DIR / "filter_partner_mappings.json"
META_PATH = OUT_DIR / "study_field_to_metadata.json"
CHECKPOINT_PATH = OUT_DIR / "filter_partner_checkpoint.json"


def log(msg: str) -> None:
    print(msg, flush=True)


def normalize_name(name: str) -> str:
    return (
        unicodedata.normalize("NFD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )


def parse_field_label(form: BeautifulSoup, target_id: str) -> str | None:
    label = form.find("label", attrs={"for": target_id})
    if label:
        return " ".join(label.get_text().split()).strip()
    return None


def parse_filter_options(html: str) -> dict[str, list[dict[str, str]]]:
    """Parse live filter options directly from portal HTML."""
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", attrs={"name": "search_form"})
    if not form:
        return {}

    label_map = {
        "Faculty": "faculty",
        "Study area": "studyArea",
        "Study field": "studyField",
    }

    filters: dict[str, list[dict[str, str]]] = {}
    for select in form.find_all("select"):
        field_id = select.get("id") or select.get("name")
        field_name = select.get("name") or select.get("id")
        if not field_name:
            continue
        label = parse_field_label(form, field_id) if field_id else None
        if label not in label_map:
            continue
        key = label_map[label]
        seen: set[str] = set()
        uniq: list[dict[str, str]] = []
        for opt in select.find_all("option"):
            val = opt.get("value", "") or ""
            text = " ".join(opt.get_text().split()).strip()
            if not val or not text or text in seen:
                continue
            # Faculty dropdown can include departments as well; restrict to faculties.
            if label == "Faculty" and not text.startswith("Faculty of"):
                continue
            seen.add(text)
            uniq.append({"value": val, "text": text, "field_name": field_name})
        filters[key] = uniq
    return filters


def extract_form_params(html: str) -> dict[str, str]:
    params: dict[str, str] = {}
    m = re.search(r'<form[^>]*name="search_form"[^>]*>(.*?)</form>', html, re.S | re.I)
    if not m:
        return params
    form_html = m.group(1)

    def get_attrs(tag: str) -> dict[str, str]:
        return dict(re.findall(r'\s+([^\s=]+)="([^"]*)"', tag))

    for tag in re.findall(r'<input([^>]*)/?>', form_html, re.S | re.I):
        tag = tag.strip()
        attrs = get_attrs(tag)
        name = attrs.get("name")
        if not name:
            continue
        t = attrs.get("type", "").lower()
        if t in ("radio", "checkbox") and "checked" not in tag.lower():
            continue
        params[name] = attrs.get("value", "")

    for tag, opts in re.findall(r"<select([^>]*)>(.*?)</select>", form_html, re.S | re.I):
        attrs = get_attrs(tag)
        name = attrs.get("name")
        if not name:
            continue
        selected = re.findall(r'<option[^>]*selected[^>]*value="([^"]*)"', opts, re.S | re.I)
        params[name] = selected[0] if selected else ""
    return params


def ajax_post(page: Page, payload: dict[str, str]) -> APIResponse:
    body = urllib.parse.urlencode(payload, doseq=False)
    return page.request.post(
        PORTAL_POST,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        },
    )


def parse_plane_list(result: dict[str, Any]) -> list[str]:
    plane_list = result.get("plane_list") or []
    if not plane_list:
        return []
    entries = plane_list[0]
    names: list[str] = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) > 0 and entry[0]:
            names.append(str(entry[0]).strip())
    return names


def fetch_filtered_names(
    page: Page,
    base_params: dict[str, str],
    field_name: str,
    option_value: str,
) -> list[str]:
    """Run a single filtered search via the portal's reloadFields endpoint."""
    payload = {
        **base_params,
        "identifier": "KOBENHA01",
        "is_reload_on_change": "1",
        field_name: option_value,
        "keyword_field": "",
        "search_button": "Start search",
    }
    response = ajax_post(page, payload)
    text = response.text()
    # If the portal rotated the response to an error page, raise so the caller
    # can refresh the session.
    if "validation" in text.lower() or "only valid for the current session" in text.lower():
        raise RuntimeError("Portal returned validation/session error")
    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse JSON response: {e}") from e
    return parse_plane_list(result)


def load_checkpoint() -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {"faculty": set(), "studyArea": set(), "studyField": set()}
    if CHECKPOINT_PATH.exists():
        try:
            data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
            for key in mapping:
                mapping[key] = set(data.get(key, []))
        except Exception:
            pass
    return mapping


def save_checkpoint(done: dict[str, set[str]]) -> None:
    payload = {k: sorted(v) for k, v in done.items()}
    CHECKPOINT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def derive_metadata(
    mappings: dict[str, dict[str, list[str]]],
) -> dict[str, dict[str, str | None]]:
    sf_sets = {
        k: set(normalize_name(n) for n in v)
        for k, v in mappings.get("studyField", {}).items()
    }
    faculty_sets = {
        k: set(normalize_name(n) for n in v)
        for k, v in mappings.get("faculty", {}).items()
    }
    area_sets = {
        k: set(normalize_name(n) for n in v)
        for k, v in mappings.get("studyArea", {}).items()
    }

    meta: dict[str, dict[str, str | None]] = {}
    for sf_label, sf_set in sf_sets.items():
        if not sf_set:
            meta[sf_label] = {"faculty": None, "studyArea": None}
            continue
        best_faculty = max(
            faculty_sets.items(),
            key=lambda item: len(sf_set & item[1]),
        )
        best_area = max(
            area_sets.items(),
            key=lambda item: len(sf_set & item[1]),
        )
        faculty = best_faculty[0] if best_faculty[1] else None
        area = best_area[0] if best_area[1] else None
        meta[sf_label] = {
            "faculty": faculty if faculty and len(sf_set & faculty_sets[faculty]) > 0 else None,
            "studyArea": area if area and len(sf_set & area_sets[area]) > 0 else None,
        }
    return meta


def run(test: bool) -> None:
    # Load prior mappings if available so the script can resume.
    if MAPPINGS_PATH.exists():
        existing = json.loads(MAPPINGS_PATH.read_text(encoding="utf-8"))
        mappings: dict[str, dict[str, list[str]]] = {
            "faculty": existing.get("faculty", {}),
            "studyArea": existing.get("studyArea", {}),
            "studyField": existing.get("studyField", {}),
        }
    else:
        mappings = {"faculty": {}, "studyArea": {}, "studyField": {}}
    done = load_checkpoint()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        log("Opening portal...")
        page.goto(PORTAL_URL, wait_until="networkidle", timeout=120000)
        time.sleep(2)

        html = page.content()
        filter_options = parse_filter_options(html)
        base_params = extract_form_params(html)

        if not filter_options:
            log("ERROR: Could not parse filter options from portal HTML")
            sys.exit(1)
        for key, opts in filter_options.items():
            log(f"{key}: {len(opts)} values")
        log(f"Loaded base form with {len(base_params)} parameters")

        total = 0
        for category, options in filter_options.items():
            items = options[:2] if test else options
            for opt in items:
                label = opt["text"]
                if label in done[category]:
                    continue
                field_name = opt["field_name"]
                option_value = opt["value"]

                log(f"[{category}] {label}")
                names: list[str] = []
                attempts = 0
                while attempts < 3:
                    try:
                        names = fetch_filtered_names(page, base_params, field_name, option_value)
                        break
                    except Exception as e:
                        attempts += 1
                        log(f"  ERROR (attempt {attempts}): {e}")
                        time.sleep(3)
                        log("  Refreshing portal session...")
                        page.goto(PORTAL_URL, wait_until="networkidle", timeout=120000)
                        time.sleep(2)
                        html = page.content()
                        filter_options = parse_filter_options(html)
                        base_params = extract_form_params(html)
                        # Re-resolve the current field name/value from refreshed page.
                        refreshed = next(
                            (o for o in filter_options[category] if o["text"] == label),
                            None,
                        )
                        if refreshed:
                            field_name = refreshed["field_name"]
                            option_value = refreshed["value"]
                        if attempts >= 3:
                            log(f"  Giving up on {label}")
                            names = []
                            break

                # Filter the result down to partners that are in the current
                # portal result table for this filter.  This prevents assigning
                # countries to institutions that only appear on the map.
                mappings[category][label] = sorted(set(names))
                done[category].add(label)
                total += 1
                save_checkpoint(done)
                log(f"  -> {len(names)} institutions")
                time.sleep(0.75)

        browser.close()

    output = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "faculty": {k: sorted(set(v)) for k, v in mappings["faculty"].items()},
        "studyArea": {k: sorted(set(v)) for k, v in mappings["studyArea"].items()},
        "studyField": {k: sorted(set(v)) for k, v in mappings["studyField"].items()},
    }
    MAPPINGS_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    log(f"Wrote mappings to {MAPPINGS_PATH}")

    meta = derive_metadata(output)
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"Wrote study field metadata to {META_PATH}")

    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    log(f"Total searches executed: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Map portal filters to partner institutions.")
    parser.add_argument("--test", action="store_true", help="Run a small subset for testing")
    args = parser.parse_args()
    run(args.test)
