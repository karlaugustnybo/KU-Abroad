# KU Abroad DuckDB

`ku_abroad.duckdb` is a reproducible analytical projection of the current,
validated portal run. The source JSON and compressed response bodies remain the
authoritative archive.

Build it with:

```sh
uv run python scripts/build_duckdb.py
```

The build is atomic: it writes a temporary database and only replaces the
output after every table and view has been created successfully.

## Model

- `metadata`: run lineage, validation reports, data-quality issues, and a
  machine-readable data dictionary (`metadata.table_grains`).
- `raw`: a compact HTTP manifest. It keeps hashes and source references but
  intentionally does not duplicate ~313 MB of opaque POST payloads already
  preserved in `manifest.jsonl`.
- `catalog`: institutions, agreements, declared academic years, study fields,
  reports, ordered report answers, and lossless long-form attributes. Common
  agreement fields are also promoted to typed columns.
- `availability`: portal query coverage and the exact agreement matches for
  each academic-year/study-field query.
- `mart`: convenient views over the current run.

The important grains are deliberately distinct. `catalog.agreements` says an
agreement exists in a run. `availability.query_agreement_matches` says the
portal returned that agreement for a particular year and study-field query.
Use the latter when filtering actual exchange options.

`metadata.report_runs` identifies the separately validated questionnaire run.
`catalog.report_institutions` preserves the institution overview from the
questionnaire run, which can include institutions absent from the older
agreement snapshot. `catalog.reports` has one row per questionnaire and links
to that overview by `report_run_id` and `institution_id`.
`catalog.report_answers` has one row per question that appeared
in the form; `answer IS NULL` means that question was present but unanswered.
There is no inferred join to a current agreement. Original question wording
is preserved alongside `normalized_question`. `source_ref` points to a
compressed archived HTML body in the report run; the raw bodies and free-text
answers are not bundled into the tracked analytical database. The web export
publishes original answers as individual JSON files loaded on demand.

After `collect_reports.py` publishes `data/current_report_run.json`, run
`uv run python scripts/build_duckdb.py --reports-run RUN_ID` to build the
gitignored `data/reports.duckdb` atomically. The ordinary build leaves
report tables empty in the tracked `ku_abroad.duckdb`. The report build
rejects incomplete report runs, duplicate report IDs, and reports without an
institution in the report overview. Run `cd src && bun run build:reports` to
publish the verified report run to the web app after building this database.

## Useful queries

```sql
-- Start here for product/app use.
SELECT *
FROM mart.current_exchange_options
WHERE academic_year = '2026/2027'
  AND study_field = 'Computer Science'
ORDER BY country, institution_name, agreement_name;

-- Inspect the full, evolving source detail vocabulary without schema changes.
SELECT attribute_name, count(*) AS agreements_with_field
FROM catalog.agreement_attributes
GROUP BY attribute_name
ORDER BY agreements_with_field DESC;

-- Verify collection coverage.
SELECT * FROM mart.current_query_coverage;

-- Review known source/quality caveats before analysis.
SELECT * FROM metadata.data_quality_issues;

-- Inspect answers in their source order.
SELECT r.institution_id, r.academic_year, a.question_ordinal,
       a.question, a.answer
FROM mart.current_reports r
JOIN catalog.report_answers a USING (report_id)
ORDER BY r.institution_id, r.report_id, a.question_ordinal;

-- See every table's intended grain before joining it.
SELECT * FROM metadata.table_grains ORDER BY table_name;
```

Connect read-only from Python:

```python
import duckdb

con = duckdb.connect("data/ku_abroad.duckdb", read_only=True)
options = con.sql("SELECT * FROM mart.current_exchange_options").df()
```
