#!/usr/bin/env python3
"""
Fetch *partner* detail pages (contact / general info) via Playwright in one
browser session.

The Mobility-Online portal binds all detail `match` tokens to the current
session.  This script:

  1. Opens the portal once.
  2. Pulls the partner DataTable to get live partner-detail `match` tokens.
  3. For each partner, calls openFancy('partnerDetails', ...) and captures the
     modal body HTML to data/partner_details/.
  4. Writes metadata.json.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "data" / "partner_details"
OUT_DIR.mkdir(parents=True, exist_ok=True)
META_PATH = ROOT / "data" / "partner_details_metadata.json"
CHECKPOINT_PATH = ROOT / "data" / "partner_details_checkpoint.json"
PORTAL_URL = "https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01"
PORTAL_POST = "https://www.service4mobility.com/europe/PortalServlet"
DETAIL_BASE = "https://www.service4mobility.com/europe/DispSearchDetailServlet?match={}"


def log(msg: str) -> None:
    print(msg, flush=True)


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def normalize_name(s: str) -> str:
    return (
        s.normalize("NFD")
        .replace("\u0300", "")
        .replace("\u0301", "")
        .replace("\u0302", "")
        .replace("\u0303", "")
        .replace("\u0308", "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )


def short_hash(s: str, length: int = 16) -> str:
    return f"{s[:24]}_{s[-length:]}"


# Matches the DataTable row returned by the portal search form.
_ROW_RE = re.compile(
    r"openFancy\('partnerDetails',\s*'[^']*match=([^'\" ;]+)"
)


def parse_detail_col(detail_col: str) -> str | None:
    m = _ROW_RE.search(detail_col)
    return m.group(1) if m else None


def parse_partner_row(row: list[str]) -> dict[str, Any] | None:
    if len(row) < 11:
        return None
    detail_col = row[-1]
    partner_match = parse_detail_col(detail_col)
    if not partner_match:
        return None

    def to_int(c: str) -> int:
        c = strip_html(c).replace("N/A", "").strip()
        try:
            return int(c)
        except Exception:
            return 0

    return {
        "partner_match": partner_match,
        "name": strip_html(row[1]),
        "continent": strip_html(row[2]),
        "country": strip_html(row[3]),
        "city": strip_html(row[4]),
        "agreement_count": to_int(row[5]),
        "cooperation_count": to_int(row[7]),
        "multilat_count": to_int(row[8]),
        "reports_count": to_int(row[9]),
        "events_count": to_int(row[10]),
    }


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


def ajax_post(page: Page, payload: dict[str, str]) -> str:
    body = urllib.parse.urlencode(payload, doseq=False)
    response = page.request.post(
        PORTAL_POST,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    return response.text()


def fetch_partner_table(page: Page) -> list[dict[str, Any]]:
    form_params = extract_form_params(page.content())
    payload = {**form_params, "identifier": "KOBENHA01", "is_reload_table": "1", "is_show_counter": "1", "row_start": "0", "row_length": "600"}
    body = ajax_post(page, payload)
    table_json = json.loads(body)
    rows = table_json.get("aaData", [])
    parsed: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        info = parse_partner_row(r)
        if info:
            info["partner_id"] = idx
            parsed.append(info)
    log(f"Parsed {len(parsed)} partners from DataTable")
    return parsed


def open_partner_detail(page: Page, partner_match: str, partner_name: str) -> str:
    detail_path = f"/europe/DispSearchDetailServlet?match={partner_match}"
    page.evaluate(
        f"""
        () => {{
            if (typeof openFancy === 'function') {{
                openFancy('partnerDetails', '{detail_path}');
            }} else {{
                throw new Error('openFancy not found');
            }}
        }}
        """
    )
    page.wait_for_selector("#modal_dialog .modal-body", state="attached", timeout=15000)
    try:
        page.wait_for_function(
            """({ name }) => {
                const body = document.querySelector('#modal_dialog .modal-body');
                if (!body) return false;
                const text = body.textContent.toLowerCase();
                return body.innerHTML.trim().length > 20 &&
                    text.includes('name of institution') &&
                    text.includes(name.toLowerCase());
            }""",
            arg={"name": partner_name},
            timeout=30000,
        )
    except Exception:
        # Some institutions use a local-language name in the detail body, which
        # doesn't match the English name in the list. Return what we have.
        log(f"  fallback capture for {partner_name}")
    return page.locator("#modal_dialog .modal-body").inner_html()


def close_modal(page: Page) -> None:
    try:
        page.evaluate(
            """() => {
                const closeBtn = document.querySelector('#modal_dialog .modal-header .close, #modal_dialog button[data-dismiss="modal"]');
                if (closeBtn) closeBtn.click();
                const modal = document.getElementById('modal_dialog');
                if (modal && modal.classList) modal.classList.remove('in');
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) backdrop.remove();
            }"""
        )
        page.wait_for_timeout(300)
    except Exception:
        pass


def load_checkpoint() -> set[str]:
    if CHECKPOINT_PATH.exists():
        try:
            data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
            return set(data.get("done", []))
        except Exception:
            pass
    return set()


def save_checkpoint(done: set[str]) -> None:
    CHECKPOINT_PATH.write_text(json.dumps({"done": sorted(done)}, indent=2), encoding="utf-8")


def has_validation_error(html: str) -> bool:
    return bool("validation" in html.lower() or "only valid for the current session" in html.lower())


def run(mode: str) -> None:
    records: list[dict[str, Any]] = []
    if META_PATH.exists():
        try:
            existing = json.loads(META_PATH.read_text(encoding="utf-8"))
            records = list(existing.get("records", []))
        except Exception:
            records = []
    done: set[str] = load_checkpoint()
    existing_record_ids: list[int] = []
    for r in records:
        pid = r.get("partner_id")
        if pid is not None:
            pid = int(pid)
            existing_record_ids.append(pid)
            # Only mark successful fetches as done so errors get retried.
            if r.get("status") == "success" or (
                r.get("filename") and (OUT_DIR / r["filename"]).exists()
            ):
                done.add(f"{pid:04d}")

    # Rebuild metadata without duplicates (new run uses partner_id keys).
    if existing_record_ids:
        seen_pids = set()
        deduped: list[dict[str, Any]] = []
        for r in records:
            pid = int(r["partner_id"])
            if pid not in seen_pids:
                seen_pids.add(pid)
                deduped.append(r)
        records = deduped

    total = 0
    success = 0
    validation_errors = 0
    errors: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        log("Opening portal...")
        page.goto(PORTAL_URL, wait_until="networkidle", timeout=120000)
        time.sleep(2)

        partners = fetch_partner_table(page)
        if mode != "all":
            partners = partners[:12 if mode == "twelve" else 1]

        for i, partner in enumerate(partners, start=1):
            partner_id = partner["partner_id"]
            name = partner["name"]
            match = partner["partner_match"]
            file_key = f"{partner_id:04d}"

            if file_key in done or (OUT_DIR / f"{file_key}.html").exists():
                log(f"[{i}/{len(partners)}] SKIP {name} already done")
                continue

            log(f"[{i}/{len(partners)}] {name}")
            try:
                html = open_partner_detail(page, match, name)
                err = has_validation_error(html)
                size = len(html)
                out_path = OUT_DIR / f"{file_key}.html"
                out_path.write_text(html, encoding="utf-8")
                total += 1
                if err or size < 500:
                    validation_errors += 1
                    status = "validation_error"
                    log(f"  VALIDATION ERROR ({size} bytes)")
                else:
                    success += 1
                    status = "success"
                    log(f"  OK ({size} bytes)")
                records.append({
                    "partner_id": partner_id,
                    "partner_name": name,
                    "partner_match": match,
                    "detail_url": DETAIL_BASE.format(match),
                    "filename": out_path.name,
                    "status": status,
                    "size": size,
                })
                done.add(file_key)
                save_checkpoint(done)
            except Exception as e:
                log(f"  ERROR: {e}")
                errors.append({"partner_id": partner_id, "name": name, "error": str(e)})
            finally:
                close_modal(page)
                time.sleep(0.5)

        browser.close()

    meta = {
        "total": len(records),
        "success": success,
        "validation_errors": validation_errors,
        "errors": len(errors),
        "records": records,
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()

    log("\n--- Summary ---")
    log(f"Total attempts: {total}")
    log(f"Success: {success}")
    log(f"Validation errors: {validation_errors}")
    log(f"Other errors: {len(errors)}")
    log(f"Metadata: {META_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch partner detail pages via Playwright.")
    parser.add_argument("mode", choices=["one", "twelve", "all"], help="How many partner details to fetch")
    args = parser.parse_args()
    run(args.mode)
