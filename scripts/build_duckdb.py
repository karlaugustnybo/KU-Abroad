#!/usr/bin/env python3
"""Build the analytical DuckDB database from a validated portal run.

The source JSON remains authoritative.  This database is a reproducible,
query-friendly projection with explicit grains and provenance.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import duckdb

from portal_data import parse_partner


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DEFAULT_OUTPUT = DATA / "ku_abroad.duckdb"
REPORT_OUTPUT = DATA / "reports.duckdb"
PUBLISHED_DATASET = ROOT / "src/src/assets/data/institutions.json"
EXCLUDED_INSTITUTION_CODES = {"DA-Overflytning"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def blank_to_none(value: Any) -> Any:
    return None if value == "" else value


def yes_no(value: Any) -> bool | None:
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def chunks(rows: Iterable[Sequence[Any]], size: int = 2_000) -> Iterator[list[Sequence[Any]]]:
    batch: list[Sequence[Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def insert_many(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    rows: Iterable[Sequence[Any]],
) -> None:
    for batch in chunks(rows):
        connection.executemany(sql, batch)


def academic_year_parts(label: str) -> tuple[int | None, int | None]:
    match = re.fullmatch(r"(\d{4})/(\d{4})", label.strip())
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_coordinates(run_id: str) -> dict[str, tuple[float, float]]:
    if not PUBLISHED_DATASET.exists():
        return {}
    published = read_json(PUBLISHED_DATASET)
    if published.get("exchange", {}).get("runId") != run_id:
        return {}
    return {
        item["id"]: (item["lat"], item["lon"])
        for item in published.get("institutions", [])
        if item.get("lat") is not None and item.get("lon") is not None
    }


SCHEMA_SQL = r"""
CREATE SCHEMA metadata;
CREATE SCHEMA raw;
CREATE SCHEMA catalog;
CREATE SCHEMA availability;
CREATE SCHEMA mart;

CREATE TABLE metadata.dataset_runs (
    run_id VARCHAR PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ NOT NULL,
    source_url VARCHAR,
    source_state_path VARCHAR NOT NULL,
    source_state_sha256 VARCHAR NOT NULL,
    verification_status VARCHAR NOT NULL,
    quality_status VARCHAR NOT NULL,
    is_current BOOLEAN NOT NULL,
    verification JSON NOT NULL,
    quality_report JSON NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
);

CREATE TABLE metadata.data_quality_issues (
    run_id VARCHAR NOT NULL,
    issue_type VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    message VARCHAR NOT NULL,
    PRIMARY KEY (run_id, issue_type, message)
);

CREATE TABLE metadata.table_grains (
    table_name VARCHAR PRIMARY KEY,
    grain VARCHAR NOT NULL,
    purpose VARCHAR NOT NULL
);

CREATE TABLE raw.http_events (
    run_id VARCHAR NOT NULL,
    event_number INTEGER NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    method VARCHAR NOT NULL,
    kind VARCHAR NOT NULL,
    status INTEGER,
    url VARCHAR NOT NULL,
    body_sha256 VARCHAR,
    body_ref VARCHAR,
    post_data_sha256 VARCHAR,
    post_data_bytes BIGINT NOT NULL,
    academic_year VARCHAR,
    study_field VARCHAR,
    institution VARCHAR,
    application_type VARCHAR,
    person_type VARCHAR,
    context JSON NOT NULL,
    PRIMARY KEY (run_id, event_number)
);

CREATE TABLE catalog.academic_years (
    run_id VARCHAR NOT NULL,
    academic_year VARCHAR NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    in_portal_catalog BOOLEAN NOT NULL,
    PRIMARY KEY (run_id, academic_year)
);

CREATE TABLE catalog.study_fields (
    run_id VARCHAR NOT NULL,
    study_field VARCHAR NOT NULL,
    PRIMARY KEY (run_id, study_field)
);

CREATE TABLE catalog.institutions (
    run_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    institution_code VARCHAR,
    country VARCHAR NOT NULL,
    city VARCHAR,
    continent VARCHAR,
    latitude DOUBLE,
    longitude DOUBLE,
    agreement_count INTEGER NOT NULL,
    cooperation_count INTEGER NOT NULL,
    multilateral_count INTEGER NOT NULL,
    report_count INTEGER NOT NULL,
    event_count INTEGER NOT NULL,
    additional_description VARCHAR,
    description VARCHAR,
    ects_converter VARCHAR,
    semester_dates VARCHAR,
    academic_calendar VARCHAR,
    faculty_contact VARCHAR,
    housing_contact VARCHAR,
    comment VARCHAR,
    source_ref VARCHAR,
    partner_details JSON,
    PRIMARY KEY (run_id, institution_id)
);

CREATE TABLE catalog.institution_attributes (
    run_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    attribute_name VARCHAR NOT NULL,
    value_ordinal INTEGER NOT NULL,
    attribute_value VARCHAR NOT NULL,
    PRIMARY KEY (run_id, institution_id, attribute_name, value_ordinal)
);

CREATE TABLE catalog.institution_documents (
    run_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    document_ordinal INTEGER NOT NULL,
    label VARCHAR,
    url VARCHAR NOT NULL,
    PRIMARY KEY (run_id, institution_id, document_ordinal)
);

CREATE TABLE catalog.agreements (
    run_id VARCHAR NOT NULL,
    agreement_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    partner_name VARCHAR NOT NULL,
    host_country VARCHAR NOT NULL,
    agreement_name VARCHAR,
    description VARCHAR,
    person_type VARCHAR,
    application_type VARCHAR,
    program_name VARCHAR,
    total_places INTEGER,
    bachelor BOOLEAN,
    master_postgraduate BOOLEAN,
    phd_doctoral BOOLEAN,
    comment VARCHAR,
    partner_information VARCHAR,
    academic_calendar VARCHAR,
    undergraduate_gpa VARCHAR,
    graduate_gpa VARCHAR,
    language_proficiency VARCHAR,
    undergraduate_study_load VARCHAR,
    graduate_study_load VARCHAR,
    restrictions VARCHAR,
    important_links VARCHAR,
    housing VARCHAR,
    scholarships VARCHAR,
    additional_information VARCHAR,
    portal_url VARCHAR,
    source_ref VARCHAR,
    details JSON NOT NULL,
    PRIMARY KEY (run_id, agreement_id)
);

CREATE TABLE catalog.agreement_attributes (
    run_id VARCHAR NOT NULL,
    agreement_id VARCHAR NOT NULL,
    attribute_name VARCHAR NOT NULL,
    attribute_value VARCHAR NOT NULL,
    PRIMARY KEY (run_id, agreement_id, attribute_name)
);

CREATE TABLE catalog.agreement_academic_years (
    run_id VARCHAR NOT NULL,
    agreement_id VARCHAR NOT NULL,
    academic_year VARCHAR NOT NULL,
    PRIMARY KEY (run_id, agreement_id, academic_year)
);

CREATE TABLE metadata.report_runs (
    report_run_id VARCHAR PRIMARY KEY,
    collected_at TIMESTAMPTZ NOT NULL,
    source_state_path VARCHAR NOT NULL,
    source_state_sha256 VARCHAR NOT NULL,
    report_count INTEGER NOT NULL,
    quality_report JSON NOT NULL
);

CREATE TABLE catalog.report_institutions (
    report_run_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    city VARCHAR,
    continent VARCHAR,
    reported_count INTEGER NOT NULL,
    source_ref VARCHAR NOT NULL,
    PRIMARY KEY (report_run_id, institution_id)
);

CREATE TABLE catalog.reports (
    report_run_id VARCHAR NOT NULL,
    report_id VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    source_ref VARCHAR NOT NULL,
    raw_sha256 VARCHAR NOT NULL,
    content_sha256 VARCHAR NOT NULL,
    questionnaire_type VARCHAR,
    academic_year VARCHAR,
    study_field VARCHAR,
    language VARCHAR,
    source_fields JSON NOT NULL,
    PRIMARY KEY (report_run_id, report_id)
);

CREATE TABLE catalog.report_answers (
    report_run_id VARCHAR NOT NULL,
    report_id VARCHAR NOT NULL,
    question_ordinal INTEGER NOT NULL,
    section VARCHAR,
    question VARCHAR NOT NULL,
    normalized_question VARCHAR NOT NULL,
    answer VARCHAR,
    source_field VARCHAR,
    links JSON NOT NULL,
    PRIMARY KEY (report_run_id, report_id, question_ordinal)
);

CREATE TABLE availability.portal_queries (
    run_id VARCHAR NOT NULL,
    query_key VARCHAR NOT NULL,
    academic_year VARCHAR NOT NULL,
    study_field VARCHAR,
    status VARCHAR NOT NULL,
    collected_at TIMESTAMPTZ,
    method VARCHAR,
    table_refs JSON NOT NULL,
    matched_institution_count INTEGER NOT NULL,
    matched_agreement_count INTEGER NOT NULL,
    PRIMARY KEY (run_id, query_key)
);

CREATE TABLE availability.query_institution_matches (
    run_id VARCHAR NOT NULL,
    query_key VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    agreement_count INTEGER NOT NULL,
    method VARCHAR,
    source_ref VARCHAR,
    PRIMARY KEY (run_id, query_key, institution_id)
);

CREATE TABLE availability.query_agreement_matches (
    run_id VARCHAR NOT NULL,
    query_key VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    agreement_id VARCHAR NOT NULL,
    PRIMARY KEY (run_id, query_key, institution_id, agreement_id)
);

CREATE TABLE availability.baseline_observations (
    run_id VARCHAR NOT NULL,
    academic_year VARCHAR NOT NULL,
    institution_id VARCHAR NOT NULL,
    reported_agreement_count INTEGER NOT NULL,
    observed_agreement_count INTEGER NOT NULL,
    source_discrepancy VARCHAR,
    source_ref VARCHAR,
    PRIMARY KEY (run_id, academic_year, institution_id)
);

CREATE INDEX institution_location_idx ON catalog.institutions(country, city);
CREATE INDEX agreement_institution_idx ON catalog.agreements(run_id, institution_id);
CREATE INDEX query_dimensions_idx ON availability.portal_queries(run_id, academic_year, study_field);
CREATE INDEX query_agreement_idx ON availability.query_agreement_matches(run_id, agreement_id);

CREATE VIEW mart.current_run AS
SELECT * EXCLUDE (verification, quality_report)
FROM metadata.dataset_runs
WHERE is_current;

CREATE VIEW mart.current_institutions AS
SELECT i.* EXCLUDE (run_id)
FROM catalog.institutions i
JOIN metadata.dataset_runs r USING (run_id)
WHERE r.is_current;

CREATE VIEW mart.current_agreements AS
SELECT a.* EXCLUDE (run_id, details)
FROM catalog.agreements a
JOIN metadata.dataset_runs r USING (run_id)
WHERE r.is_current;

CREATE VIEW mart.current_reports AS
SELECT r.* EXCLUDE (report_run_id, source_fields)
FROM catalog.reports r
JOIN metadata.report_runs run USING (report_run_id);

CREATE VIEW mart.current_exchange_options AS
SELECT
    q.academic_year,
    q.study_field,
    i.institution_id,
    i.name AS institution_name,
    i.country,
    i.city,
    i.continent,
    i.latitude,
    i.longitude,
    a.agreement_id,
    a.agreement_name,
    a.program_name,
    a.total_places,
    a.bachelor,
    a.master_postgraduate,
    a.phd_doctoral,
    a.application_type,
    a.person_type
FROM availability.portal_queries q
JOIN metadata.dataset_runs r USING (run_id)
JOIN availability.query_agreement_matches m USING (run_id, query_key)
JOIN catalog.institutions i USING (run_id, institution_id)
JOIN catalog.agreements a USING (run_id, agreement_id, institution_id)
WHERE r.is_current AND q.status = 'success' AND q.study_field IS NOT NULL;

CREATE VIEW mart.current_query_coverage AS
SELECT
    count(*) AS query_count,
    count(*) FILTER (WHERE status = 'success') AS successful_query_count,
    count(*) FILTER (WHERE study_field IS NULL) AS baseline_query_count,
    count(*) FILTER (WHERE study_field IS NOT NULL) AS study_field_query_count,
    min(collected_at) AS first_query_at,
    max(collected_at) AS last_query_at
FROM availability.portal_queries q
JOIN metadata.dataset_runs r USING (run_id)
WHERE r.is_current;
"""


TABLE_GRAINS = [
    ("metadata.dataset_runs", "one row per collection run", "Run lineage, validation, and current-run selection"),
    ("metadata.data_quality_issues", "one row per run and distinct issue", "Machine-queryable source and validation caveats"),
    ("raw.http_events", "one row per manifest line", "HTTP provenance without duplicating large volatile POST bodies"),
    ("catalog.institutions", "one row per run and institution", "Typed institution snapshot"),
    ("catalog.institution_attributes", "one row per institution field value", "Lossless long-form partner fields"),
    ("catalog.institution_documents", "one row per institution document", "Partner document links"),
    ("catalog.agreements", "one row per run and agreement", "Typed agreement snapshot plus source JSON"),
    ("catalog.agreement_attributes", "one row per agreement detail field", "Lossless long-form agreement details"),
    ("catalog.agreement_academic_years", "one row per agreement and declared academic year", "Years declared on the agreement itself"),
    ("metadata.report_runs", "one row per validated questionnaire run", "Separate questionnaire collection lineage"),
    ("catalog.report_institutions", "one row per institution in a questionnaire run", "Institution identity and location from the questionnaire snapshot"),
    ("catalog.reports", "one row per questionnaire in the report run", "Institution-linked questionnaire metadata"),
    ("catalog.report_answers", "one row per asked question in a questionnaire", "Ordered original wording and nullable answer"),
    ("availability.portal_queries", "one row per year/study-field portal query", "Complete query coverage, including empty results"),
    ("availability.query_institution_matches", "one row per query and matched institution", "Institution-level query evidence and provenance"),
    ("availability.query_agreement_matches", "one row per query, institution, and agreement", "Authoritative availability fact"),
    ("availability.baseline_observations", "one row per year and baseline institution", "Reported-versus-observed agreement counts"),
    ("mart.current_exchange_options", "one row per current year/study-field/agreement match", "Convenient analysis-ready options"),
]


def load_report_run(connection: duckdb.DuckDBPyConnection, report_run_id: str) -> None:
    """Load only a fully validated report run into the reports projection."""
    run = DATA / "report-runs" / report_run_id
    state_path = run / "state.json"
    quality_path = run / "quality-report.json"
    if not state_path.exists() or not quality_path.exists():
        raise FileNotFoundError(f"Missing report run files for {report_run_id}")
    state, quality = read_json(state_path), read_json(quality_path)
    if state.get("runId") != report_run_id or not state.get("completedAt"):
        raise ValueError("Report run identity or completion marker is invalid")
    if quality.get("status") != "complete" or quality.get("discrepancies"):
        raise ValueError("Only quality-complete report runs can be loaded")
    reports = state.get("reports", {})
    def archive_matches(ref: str | None, expected: str | None = None) -> bool:
        if not ref or not re.fullmatch(r"bodies/[0-9a-f]{64}\.gz", ref):
            return False
        path = run / ref
        if not path.is_file():
            return False
        try:
            sha = hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()
        except (OSError, EOFError):
            return False
        return sha == Path(ref).stem and (expected is None or sha == expected)
    overview_refs = state.get("institutionTableRefs") or []
    overview = {}
    for ref in overview_refs:
        if not archive_matches(ref):
            raise ValueError("Missing report institution overview source")
        page = json.loads(gzip.decompress((run / ref).read_bytes()))
        for row in page.get("aaData", []):
            partner = parse_partner(row)
            if partner["id"] in overview:
                raise ValueError("Duplicate institution in report overview")
            overview[partner["id"]] = (partner, ref)
    if set(overview) != set(state.get("institutions", {})):
        raise ValueError("Report institution overview does not match run state")
    if any(partner["reportCount"] != state["institutions"][institution_id]["reportedCount"]
           for institution_id, (partner, _) in overview.items()):
        raise ValueError("Report institution count differs from overview")
    referenced = []
    for institution_id, progress in state.get("institutions", {}).items():
        ids = progress.get("reportIds") or []
        if len(ids) != progress.get("reportedCount"):
            raise ValueError(f"Incomplete report list for {institution_id}")
        if ids and not archive_matches(progress.get("listRef")):
            raise ValueError(f"Missing report list source for {institution_id}")
        referenced.extend(ids)
    if (len(referenced) != len(set(referenced)) or set(referenced) != set(reports)
            or len(referenced) != quality.get("collectedReports")):
        raise ValueError("Report IDs or validated total do not match run state")
    if any(item["institutionId"] not in overview for item in reports.values()):
        raise ValueError("Report references an institution outside its overview")
    if any(not archive_matches(item.get("sourceRef"), item.get("rawSha256"))
           for item in reports.values()):
        raise ValueError("Missing or changed report detail body")
    if any(report_id not in state["institutions"][item["institutionId"]]["reportIds"]
           for report_id, item in reports.items()):
        raise ValueError("Report institution association does not match its list")

    insert_many(connection, "INSERT INTO metadata.report_runs VALUES (?, ?, ?, ?, ?, ?)", [(
        report_run_id, state["completedAt"], str(state_path.relative_to(ROOT)),
        source_sha256(state_path), len(reports), json_value(quality))])
    insert_many(connection, "INSERT INTO catalog.report_institutions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
        (report_run_id, institution_id, partner["name"], partner["country"],
         blank_to_none(partner["city"]), blank_to_none(partner["continent"]),
         partner["reportCount"], ref)
        for institution_id, (partner, ref) in overview.items()))
    insert_many(connection, "INSERT INTO catalog.reports VALUES (" + ",".join("?" * 11) + ")", (
        (report_run_id, report_id, item["institutionId"], item["sourceRef"],
         item["rawSha256"], item["contentSha256"], item.get("questionnaireType"),
         item.get("academicYear"), item.get("studyField"), item.get("language"),
         json_value(item.get("sourceFields") or {}))
        for report_id, item in reports.items()))
    insert_many(connection, "INSERT INTO catalog.report_answers VALUES (" + ",".join("?" * 9) + ")", (
        (report_run_id, report_id, question["ordinal"], question.get("section"),
         question["question"], question["normalizedQuestion"],
         question.get("answer"), question.get("sourceField"),
         json_value(question.get("links") or []))
        for report_id, item in reports.items() for question in item["questions"]))


def build_database(run_id: str, output: Path, report_run_id: str | None = None) -> None:
    output = output.resolve()
    if report_run_id and output == DEFAULT_OUTPUT.resolve():
        raise ValueError("Questionnaire answers require a separate reports.duckdb output")
    run_dir = DATA / "portal-runs" / run_id
    state_path = run_dir / "state.json"
    manifest_path = run_dir / "manifest.jsonl"
    verification_path = run_dir / "verification.json"
    quality_path = run_dir / "quality-report.json"
    required = (state_path, manifest_path, verification_path, quality_path)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required run files: {', '.join(missing)}")

    state = read_json(state_path)
    verification = read_json(verification_path)
    quality = read_json(quality_path)
    if state.get("runId") != run_id:
        raise ValueError(f"state.json runId {state.get('runId')!r} does not match {run_id!r}")
    if not state.get("completedAt"):
        raise ValueError("Run is incomplete: completedAt is missing")
    if verification.get("status") != "passed" or quality.get("status") != "complete":
        raise ValueError("Only verified, quality-complete runs can be loaded")

    pointer = read_json(DATA / "current_portal_run.json")
    coordinates = load_coordinates(run_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    if temporary.exists():
        temporary.unlink()

    connection = duckdb.connect(str(temporary))
    try:
        connection.execute(SCHEMA_SQL)
        source_url = verification.get("sourceUrl")
        connection.execute(
            """INSERT INTO metadata.dataset_runs
               (run_id, schema_version, started_at, completed_at, source_url,
                source_state_path, source_state_sha256, verification_status,
                quality_status, is_current, verification, quality_report)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                run_id,
                state["schemaVersion"],
                state.get("startedAt"),
                state["completedAt"],
                source_url,
                str(state_path.relative_to(ROOT)),
                source_sha256(state_path),
                verification["status"],
                quality["status"],
                pointer.get("runId") == run_id,
                json_value(verification),
                json_value(quality),
            ],
        )
        insert_many(
            connection,
            "INSERT INTO metadata.table_grains VALUES (?, ?, ?)",
            TABLE_GRAINS,
        )
        quality_rows = [
            (run_id, "baseline_discrepancy", "warning", message)
            for message in quality.get("baselineDiscrepancies", [])
        ] + [
            (run_id, "failed_query", "error", json_value(item))
            for item in quality.get("failedQueries", [])
        ]
        insert_many(
            connection,
            "INSERT INTO metadata.data_quality_issues VALUES (?, ?, ?, ?)",
            quality_rows,
        )

        detail_years = {
            year.strip()
            for agreement in state["agreements"].values()
            for year in (agreement.get("details", {}).get("Academic year") or "").splitlines()
            if year.strip()
        }
        portal_years = set(state["academicYears"])
        insert_many(
            connection,
            "INSERT INTO catalog.academic_years VALUES (?, ?, ?, ?, ?)",
            (
                (run_id, year, *academic_year_parts(year), year in portal_years)
                for year in sorted(portal_years | detail_years)
            ),
        )
        insert_many(
            connection,
            "INSERT INTO catalog.study_fields VALUES (?, ?)",
            ((run_id, field) for field in state["studyFields"]),
        )

        institution_rows = []
        attribute_rows = []
        document_rows = []
        excluded_institution_ids = {
            institution_id
            for institution_id, institution in state["institutions"].items()
            if (institution.get("partnerDetails") or {}).get("code")
            in EXCLUDED_INSTITUTION_CODES
        }
        for institution_id, institution in state["institutions"].items():
            if institution_id in excluded_institution_ids:
                continue
            partner = institution.get("partnerDetails") or {}
            lat, lon = coordinates.get(institution_id, (None, None))
            institution_rows.append(
                (
                    run_id,
                    institution_id,
                    institution["name"],
                    partner.get("code"),
                    institution["country"],
                    blank_to_none(institution.get("city")),
                    blank_to_none(institution.get("continent")),
                    lat,
                    lon,
                    institution.get("agreementCount", 0),
                    institution.get("cooperationCount", 0),
                    institution.get("multilateralCount", 0),
                    institution.get("reportCount", 0),
                    institution.get("eventCount", 0),
                    blank_to_none(partner.get("additionalDescription")),
                    blank_to_none(partner.get("description")),
                    blank_to_none(partner.get("ectsConverter")),
                    blank_to_none(partner.get("semesterDates")),
                    blank_to_none(partner.get("academicCalendar")),
                    blank_to_none(partner.get("facultyContact")),
                    blank_to_none(partner.get("housingContact")),
                    blank_to_none(partner.get("comment")),
                    institution.get("sourceRef"),
                    json_value(partner),
                )
            )
            for name, values in (partner.get("fields") or {}).items():
                for ordinal, value in enumerate(values, start=1):
                    attribute_rows.append((run_id, institution_id, name, ordinal, value))
            for ordinal, document in enumerate(partner.get("documents") or [], start=1):
                document_rows.append((run_id, institution_id, ordinal, document.get("label"), document["url"]))

        insert_many(connection, "INSERT INTO catalog.institutions VALUES (" + ",".join("?" * 24) + ")", institution_rows)
        insert_many(connection, "INSERT INTO catalog.institution_attributes VALUES (?, ?, ?, ?, ?)", attribute_rows)
        insert_many(connection, "INSERT INTO catalog.institution_documents VALUES (?, ?, ?, ?, ?)", document_rows)

        agreement_rows = []
        agreement_attribute_rows = []
        agreement_year_rows = []
        for agreement_id, agreement in state["agreements"].items():
            if agreement["institutionId"] in excluded_institution_ids:
                continue
            details = agreement.get("details") or {}
            agreement_rows.append(
                (
                    run_id,
                    agreement_id,
                    agreement["institutionId"],
                    agreement["partner"],
                    agreement["hostCountry"],
                    blank_to_none(details.get("Agreement name")),
                    blank_to_none(details.get("Description")),
                    blank_to_none(details.get("Type of person")),
                    blank_to_none(details.get("Type of application")),
                    blank_to_none(details.get("Name of program")),
                    integer(details.get("Total number")),
                    yes_no(details.get("Bachelor")),
                    yes_no(details.get("Second cycle/Master/Postgraduate")),
                    yes_no(details.get("Third cycle/Phd/Doctoral")),
                    blank_to_none(details.get("Comment")),
                    blank_to_none(details.get("Partner information")),
                    blank_to_none(details.get("Academic calendar")),
                    blank_to_none(details.get("GPA for undergraduate admission")),
                    blank_to_none(details.get("GPA for graduate admission")),
                    blank_to_none(details.get("Accepted proof of language proficiency (required AFTER nomination)")),
                    blank_to_none(details.get("Study load for undergraduate students") or details.get("Study load")),
                    blank_to_none(details.get("Study load for graduate students")),
                    blank_to_none(details.get("Restrictions")),
                    blank_to_none(details.get("Important links")),
                    blank_to_none(details.get("Housing")),
                    blank_to_none(details.get("Scholarships")),
                    blank_to_none(details.get("Additional information")),
                    agreement.get("portalUrl"),
                    agreement.get("sourceRef"),
                    json_value(details),
                )
            )
            agreement_attribute_rows.extend(
                (run_id, agreement_id, name, value) for name, value in details.items()
            )
            agreement_year_rows.extend(
                (run_id, agreement_id, year.strip())
                for year in (details.get("Academic year") or "").splitlines()
                if year.strip()
            )

        insert_many(connection, "INSERT INTO catalog.agreements VALUES (" + ",".join("?" * 30) + ")", agreement_rows)
        insert_many(connection, "INSERT INTO catalog.agreement_attributes VALUES (?, ?, ?, ?)", agreement_attribute_rows)
        insert_many(connection, "INSERT INTO catalog.agreement_academic_years VALUES (?, ?, ?)", agreement_year_rows)

        query_rows = []
        query_institution_rows = []
        query_agreement_rows = []
        for query_key, query in state["queries"].items():
            matches = query.get("matches") or []
            query_rows.append(
                (
                    run_id,
                    query_key,
                    query["academicYear"],
                    query.get("studyField"),
                    query["status"],
                    query.get("collectedAt"),
                    query.get("method"),
                    json_value(query.get("tableRefs") or []),
                    len(matches),
                    sum(len(match.get("agreementIds") or []) for match in matches),
                )
            )
            for match in matches:
                if match["institutionId"] in excluded_institution_ids:
                    continue
                agreement_ids = match.get("agreementIds") or []
                query_institution_rows.append(
                    (
                        run_id,
                        query_key,
                        match["institutionId"],
                        len(agreement_ids),
                        match.get("method"),
                        match.get("sourceRef"),
                    )
                )
                query_agreement_rows.extend(
                    (run_id, query_key, match["institutionId"], agreement_id)
                    for agreement_id in agreement_ids
                )

        insert_many(connection, "INSERT INTO availability.portal_queries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", query_rows)
        insert_many(connection, "INSERT INTO availability.query_institution_matches VALUES (?, ?, ?, ?, ?, ?)", query_institution_rows)
        insert_many(connection, "INSERT INTO availability.query_agreement_matches VALUES (?, ?, ?, ?)", query_agreement_rows)

        baseline_rows = []
        for key, observation in state.get("baselineProgress", {}).items():
            year, institution_id = key.split("|", 1)
            if institution_id in excluded_institution_ids:
                continue
            baseline_rows.append(
                (
                    run_id,
                    year,
                    institution_id,
                    observation["reportedCount"],
                    len(observation.get("ids") or []),
                    observation.get("sourceDiscrepancy"),
                    observation.get("sourceRef"),
                )
            )
        insert_many(connection, "INSERT INTO availability.baseline_observations VALUES (?, ?, ?, ?, ?, ?, ?)", baseline_rows)

        if report_run_id:
            pointer = read_json(DATA / "current_report_run.json")
            if pointer.get("runId") != report_run_id:
                raise ValueError("Report run is not the validated current report run")
            load_report_run(connection, report_run_id)

        # DuckDB's vectorized NDJSON reader is dramatically faster here than
        # Python row insertion and still lets us omit the bulky POST values.
        connection.execute(
            """INSERT INTO raw.http_events
               SELECT
                 ? AS run_id,
                 row_number() OVER ()::INTEGER AS event_number,
                 "at"::TIMESTAMPTZ,
                 method,
                 kind,
                 status::INTEGER,
                 url,
                 sha256 AS body_sha256,
                 body AS body_ref,
                 CASE WHEN postData IS NULL THEN NULL ELSE sha256(postData) END,
                 octet_length(encode(coalesce(postData, ''))) AS post_data_bytes,
                 context.academicYear,
                 context.studyField,
                 context.institution,
                 context.application,
                 context.person,
                 to_json(context)
               FROM read_ndjson_auto(?, union_by_name = true)""",
            [run_id, str(manifest_path)],
        )
        connection.execute("CHECKPOINT")
    except Exception:
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()
        os.replace(temporary, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", help="Run ID; defaults to data/current_portal_run.json")
    parser.add_argument("--reports-run", help="Validated report run to load into reports.duckdb")
    parser.add_argument("--output", type=Path, help="Output .duckdb path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = args.run or read_json(DATA / "current_portal_run.json")["runId"]
    output = args.output or (REPORT_OUTPUT if args.reports_run else DEFAULT_OUTPUT)
    build_database(run_id, output, args.reports_run)
    with duckdb.connect(str(output), read_only=True) as connection:
        counts = connection.execute(
            """SELECT
                 (SELECT count(*) FROM catalog.institutions),
                 (SELECT count(*) FROM catalog.agreements),
                 (SELECT count(*) FROM availability.portal_queries),
                 (SELECT count(*) FROM mart.current_exchange_options),
                 (SELECT count(*) FROM raw.http_events)"""
        ).fetchone()
    print(
        f"Built {output}: {counts[0]} institutions, {counts[1]} agreements, "
        f"{counts[2]} queries, {counts[3]} exchange options, {counts[4]} HTTP events."
    )


if __name__ == "__main__":
    main()
