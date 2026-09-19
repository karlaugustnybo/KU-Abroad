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
