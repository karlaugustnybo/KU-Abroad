# Portal collection

`collect_portal.py` is the supported dataset collector. It uses the browser to
establish and verify a live Mobility-Online session, then sends explicit request
payloads for bulk collection.

Run verification and collection with the same run ID:

```sh
uv run python scripts/collect_portal.py --verify --run 2026-09-19
uv run python scripts/collect_portal.py --collect --run 2026-09-19 --concurrency 6
```

The collector has four stages:

1. Fetch institution metadata.
2. Fetch each academic year's complete agreement baseline.
3. Fetch year/study-field tables and map them to canonical baseline agreements.
4. Validate coverage and atomically update `data/current_portal_run.json`.

Institution pages, agreement lists, and agreement detail pages use bounded
concurrency. `--concurrency` defaults to 6 and is capped at 16. `--delay`
applies between request batches. Transient HTTP failures are retried with
backoff.

Raw responses remain content-addressed under the run's `bodies/` directory and
are recorded in `manifest.jsonl`. Query progress is journaled in
`checkpoint.sqlite3`; the complete publication state remains `state.json`.
Interrupted runs reuse completed institution, baseline, and query work.

Filtered rows that report the complete baseline count reuse the baseline IDs.
Narrowed rows fetch their filtered agreement details and match the resulting
canonical IDs against the baseline. Count-only subsets are rejected because
the portal's popup tokens are opaque and change between requests.

Academic-year and study-field selects are dependent. If a field from the
overall catalog is not offered after selecting a particular year, the
collector archives the year-specific option list and records that combination
as a verified empty query.

`archive_portal.py` is the broader source-snapshot workflow. The older
`scrape_*` and `fetch_*` scripts are retained for historical data recovery and
targeted investigation; they are not part of the publication path.

## Analytical database

After a run passes verification and quality checks, build the query-friendly
DuckDB projection:

```sh
uv run python scripts/build_duckdb.py
```

See [`data/DUCKDB.md`](../data/DUCKDB.md) for the model, grains, and example
queries.

## Exchange student questionnaires

Inspect a small public sample before each new collector format change:

```sh
uv run python scripts/inspect_reports.py --run sample-2026-09-24 --samples 3
```

The inspection run archives the initial institution rows, the `quest` popup
JSON, and one public answer page per sampled institution under
`data/portal-investigation/<run>/`. See
[`report-investigation.md`](report-investigation.md) for the observed format and
the current source limitation.

Collect all institutions in a **separate** resumable run:

```sh
uv run python scripts/collect_reports.py --run 2026-09-24 --concurrency 6
uv run python scripts/build_duckdb.py --reports-run 2026-09-24
```

Report progress and raw responses stay under `data/report-runs/<run>/`. Each
institution is checkpointed only after its list and all detail pages have
been parsed and archived. Restart with the same run ID to verify archived
bodies and skip complete institutions. The collector updates
`data/current_report_run.json` only when every observed count matches and all
details have a unique institution association. It does not change
`data/current_portal_run.json`.

The report projection is written to gitignored `data/reports.duckdb`.
The ordinary `build_duckdb.py` command keeps questionnaire answers out of the
tracked database. The public web export includes the original free-text
answers and source links; the raw HTML archive remains private.

The web app publishes all reports in the validated report run. After building
`data/reports.duckdb`, run `cd src && bun run build:reports` to regenerate the
small count index, institution lists, and one JSON file per report under
`src/public/reports/<run-id>/`. Run it again after refreshing the explorer
data with `bun run build:data`. The exporter checks run completeness, report
counts, institution matches, and report IDs before replacing public files.
