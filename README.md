# KU Abroad

A small web app for exploring the University of Copenhagen's partner institutions, mobility agreements, and global cooperation network.

License: [CC0 1.0 Universal License](LICENSE)

## Data pipeline

The Python pipeline scrapes the official KU portal and builds a DuckDB database.

```bash
# Requires Python ≥3.11 and uv. The first run creates the virtualenv.
uv run python scripts/collect_portal.py --collect --run $(date +%Y-%m-%d)
uv run python scripts/build_duckdb.py
```

The resulting database lives at `data/ku_abroad.duckdb`.

## Web app

The front end is a Vite + React + TanStack Router app inside `src/`.

```bash
cd src
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000).

To generate the front-end JSON assets from the DuckDB database:

```bash
cd src
bun run build:data
```

Student reports appear in each institution panel. The full report export is
built separately from the verified questionnaire run with `bun run build:reports`
inside `src/`. Report text is loaded only
when a reader opens an individual report.

## Author

Made by [Karl August Krogh Nybo](https://github.com/karlaugustnybo).
