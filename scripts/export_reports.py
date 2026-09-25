"""Export the verified public questionnaire run as small, lazy-loaded JSON files."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import duckdb


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
APP = ROOT / "src"
EXPLORER_INDEX = APP / "src/assets/data/explorer-index.json"
COUNT_INDEX = APP / "src/assets/data/report-counts.json"
PUBLIC_REPORTS = APP / "public/reports"
REPORT_ID = re.compile(r"report-[a-f0-9]{24}\Z")


def normalized(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def identity(item: dict) -> tuple[str, str, str]:
    return tuple(normalized(item.get(key)) for key in ("name", "country", "city"))


def safe_links(raw: str | None) -> list[str]:
    links = json.loads(raw or "[]")
    if not isinstance(links, list):
        raise ValueError("Report links are not an array")
    result = []
    for link in links:
        if not isinstance(link, str):
            raise ValueError("Report link is not a string")
        parsed = urlsplit(link)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            result.append(link)
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def match_institutions(report_institutions: list[dict], explorer_institutions: list[dict]) -> dict[str, str]:
    by_id = {item["id"]: item for item in explorer_institutions}
    by_identity: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for item in explorer_institutions:
        by_identity[identity(item)].append(item["id"])
    mapping = {}
    used = set()
    for item in report_institutions:
        source_id = item["institution_id"]
        exact = by_id.get(source_id)
        if exact and identity(exact) == identity(item):
            target_id = source_id
        else:
            candidates = by_identity[identity(item)]
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous or missing explorer institution: {item['name']}")
            target_id = candidates[0]
        if target_id in used:
            raise ValueError(f"Two report institutions map to {target_id}")
        mapping[source_id] = target_id
        used.add(target_id)
    return mapping


def export_reports() -> dict:
    pointer = json.loads((DATA / "current_report_run.json").read_text())
    run_id = pointer["runId"]
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", run_id):
        raise ValueError("Invalid report run ID")
    quality = json.loads((DATA / "report-runs" / run_id / "quality-report.json").read_text())
    if quality.get("status") != "complete" or quality.get("discrepancies"):
        raise ValueError("Report run is not complete")
    explorer = json.loads(EXPLORER_INDEX.read_text())
    connection = duckdb.connect(str(DATA / "reports.duckdb"), read_only=True)
    try:
        runs = connection.execute("SELECT report_run_id, report_count FROM metadata.report_runs").fetchall()
        if runs != [(run_id, quality["collectedReports"])]:
            raise ValueError("Report database and validated run differ")
        rows = connection.execute("""
            SELECT institution_id, name, country, city, reported_count
            FROM catalog.report_institutions WHERE report_run_id = ?
        """, [run_id]).fetchall()
        institutions = [dict(zip(("institution_id", "name", "country", "city", "reported_count"), row)) for row in rows]
        if len(institutions) != quality["observedInstitutions"]:
            raise ValueError("Report institution count differs from validated run")
        mapping = match_institutions(institutions, explorer["institutions"])
        counts = {mapping[item["institution_id"]]: item["reported_count"] for item in institutions}

        report_rows = connection.execute("""
            SELECT report_id, institution_id, academic_year, study_field, questionnaire_type
            FROM catalog.reports WHERE report_run_id = ? ORDER BY report_id
        """, [run_id]).fetchall()
        if len(report_rows) != quality["collectedReports"] or len({row[0] for row in report_rows}) != len(report_rows):
            raise ValueError("Report total or identities differ from validated run")
        reports = {}
        listings: dict[str, list[dict]] = defaultdict(list)
        names = {mapping[item["institution_id"]]: item["name"] for item in institutions}
        for report_id, source_id, academic_year, study_field, questionnaire_type in report_rows:
            if not REPORT_ID.fullmatch(report_id) or source_id not in mapping:
                raise ValueError(f"Invalid report identity or association: {report_id}")
            institution_id = mapping[source_id]
            summary = dict(id=report_id, institutionId=institution_id,
                           academicYear=academic_year, studyField=study_field,
                           questionnaireType=questionnaire_type)
            reports[report_id] = dict(**summary, institutionName=names[institution_id], sections=[])
            listings[institution_id].append(summary)
        if any(len(listings.get(institution_id, [])) != count for institution_id, count in counts.items()):
            raise ValueError("Report lists do not match institution counts")

        PUBLIC_REPORTS.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".reports-", dir=PUBLIC_REPORTS))
        try:
            cursor = connection.execute("""
                SELECT report_id, section, question, answer, links
                FROM catalog.report_answers WHERE report_run_id = ?
                ORDER BY report_id, question_ordinal
            """, [run_id])
            answer_count = 0
            for report_id, section, question, answer, links in iter(lambda: cursor.fetchone(), None):
                report = reports.get(report_id)
                if report is None:
                    raise ValueError(f"Answer belongs to unknown report: {report_id}")
                sections = report["sections"]
                title = section or "Other"
                if not sections or sections[-1]["title"] != title:
                    sections.append(dict(title=title, questions=[]))
                sections[-1]["questions"].append(dict(question=question, answer=answer,
                                                      links=safe_links(links)))
                answer_count += 1
            if answer_count != connection.execute("SELECT count(*) FROM catalog.report_answers WHERE report_run_id = ?", [run_id]).fetchone()[0]:
                raise ValueError("Incomplete report answer export")
            for report_id, report in reports.items():
                if not report["sections"]:
                    raise ValueError(f"Report has no questions: {report_id}")
                write_json(staging / "items" / f"{report_id}.json", report)
            for institution_id, listing in listings.items():
                listing.sort(key=lambda item: (item["academicYear"] or "", item["studyField"] or "", item["id"]), reverse=True)
                write_json(staging / "institutions" / f"{institution_id}.json", listing)

            destination = PUBLIC_REPORTS / run_id
            backup = PUBLIC_REPORTS / f".{run_id}.previous"
            if backup.exists():
                shutil.rmtree(backup)
            if destination.exists():
                destination.rename(backup)
            try:
                staging.rename(destination)
            except Exception:
                if backup.exists():
                    backup.rename(destination)
                raise
            if backup.exists():
                shutil.rmtree(backup)
            count_index = dict(runId=run_id, counts=counts)
            temporary_index = COUNT_INDEX.with_suffix(".json.tmp")
            write_json(temporary_index, count_index)
            temporary_index.replace(COUNT_INDEX)
            return dict(runId=run_id, institutions=len(counts), reports=len(reports), answers=answer_count)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    finally:
        connection.close()


if __name__ == "__main__":
    print(json.dumps(export_reports()))
