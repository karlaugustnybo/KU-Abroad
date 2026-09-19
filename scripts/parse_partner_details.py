#!/usr/bin/env python3
"""Parse the partner detail HTML files into a JSON file for the webapp."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
IN_DIR = ROOT / "data" / "partner_details"
META_PATH = ROOT / "data" / "partners_metadata.json"
OUT_PATH = ROOT / "src" / "assets" / "data" / "partner_details.json"
BASE_URL = "https://www.service4mobility.com"


def load_metadata() -> list[dict]:
    if not META_PATH.exists():
        return []
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def strip_text(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def html_to_text(node) -> str:
    if not node:
        return ""
    text = node.get_text("\n")
    lines = [strip_text(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def find_field(soup: BeautifulSoup, label_text: str):
    for row in soup.select("div.form-group.row"):
        label = row.select_one("label")
        if not label:
            continue
        if strip_text(label.get_text()) == label_text:
            value = row.select_one("div.form-control-plaintext")
            if value:
                return value
    return None


def parse_documents(value_node) -> list[dict[str, str]]:
    docs: dict[str, str] = {}
    for a in value_node.find_all("a", href=True):
        href = a["href"]
        if not isinstance(href, str):
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        label = strip_text(a.get_text())
        # Prefer the first non-empty label for each URL.
        existing = docs.get(href, "")
        if not existing or (label and existing == ""):
            docs[href] = label or existing
    return [{"label": label, "url": url} for url, label in docs.items() if label]


def parse_file(path: Path) -> dict[str, Any] | None:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    name_field = find_field(soup, "Name of institution")
    name = html_to_text(name_field) if name_field else None
    if not name:
        return None

    code_field = find_field(soup, "Institution code")
    additional_field = find_field(soup, "Additional description")
    country_field = find_field(soup, "Country")
    description_field = find_field(soup, "Description")
    comment_field = find_field(soup, "Comment")

    ects_field = find_field(soup, "ECTS converter")
    semester_field = find_field(soup, "Semester dates")
    academic_field = find_field(soup, "Academic calendar")
    faculty_field = find_field(soup, "Faculty information (e-mail contact)")
    housing_field = find_field(soup, "Housing (e-mail contact)")

    documents_field = find_field(soup, "Documents")

    return {
        "name": name,
        "code": strip_text(code_field.get_text()) if code_field else None,
        "additionalDescription": html_to_text(additional_field) if additional_field else None,
        "country": strip_text(country_field.get_text()) if country_field else None,
        "description": html_to_text(description_field) if description_field else None,
        "ectsConverter": html_to_text(ects_field) if ects_field else None,
        "semesterDates": html_to_text(semester_field) if semester_field else None,
        "academicCalendar": html_to_text(academic_field) if academic_field else None,
        "facultyContact": html_to_text(faculty_field) if faculty_field else None,
        "housingContact": html_to_text(housing_field) if housing_field else None,
        "comment": html_to_text(comment_field) if comment_field else None,
        "documents": parse_documents(documents_field) if documents_field else [],
    }


def normalize_name(s: str) -> str:
    return (
        s.casefold()
        .replace("'", "")
        .replace("’", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("  ", " ")
        .strip()
    )


def main() -> None:
    metadata = load_metadata()
    parsed: list[dict[str, Any]] = []
    meta_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(IN_DIR.iterdir()):
        if not path.is_file() or path.suffix != ".html":
            continue
        try:
            html_id = int(path.stem)
            partner_id = html_id - 1
        except Exception:
            html_id = -1
            partner_id = -1
        record = parse_file(path)
        if not record:
            continue
        # The portal lists partners under an English-ish name while the detail
        # body sometimes uses the local-language name. Use the metadata order
        # (same as the file IDs) so the actual list name is preserved.
        canonical = metadata[partner_id]["name"] if 0 <= partner_id < len(metadata) else record["name"]
        key = normalize_name(canonical)
        if key in seen:
            continue
        seen.add(key)
        parsed.append({
            **record,
            "name": canonical,
            "parsedOriginalName": record["name"] if record["name"] != canonical else None,
        })
        meta_records.append({
            "partner_id": html_id,
            "partner_name": canonical,
            "filename": path.name,
            "status": "success",
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")

    META_OUT = ROOT / "data" / "partner_details_metadata.json"
    META_OUT.write_text(json.dumps({
        "total": len(meta_records),
        "success": len(meta_records),
        "validation_errors": 0,
        "errors": 0,
        "records": meta_records,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {len(parsed)} partner details to {OUT_PATH}")
    print(f"Wrote metadata for {len(meta_records)} files to {META_OUT}")


if __name__ == "__main__":
    main()
