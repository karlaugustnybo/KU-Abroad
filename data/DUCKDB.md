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
  and lossless long-form attributes. Common agreement fields are also promoted
  to typed columns.
- `availability`: portal query coverage and the exact agreement matches for
  each academic-year/study-field query.
- `mart`: convenient views over the current run.

The important grains are deliberately distinct. `catalog.agreements` says an
agreement exists in a run. `availability.query_agreement_matches` says the
portal returned that agreement for a particular year and study-field query.
Use the latter when filtering actual exchange options.

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

-- See every table's intended grain before joining it.
SELECT * FROM metadata.table_grains ORDER BY table_name;
```

Connect read-only from Python:

```python
import duckdb

con = duckdb.connect("data/ku_abroad.duckdb", read_only=True)
options = con.sql("SELECT * FROM mart.current_exchange_options").df()
```
