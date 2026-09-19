# Scraping plan — Faculty / Study field / Study area filters

**Scope:** Add Faculty, Study area and Study field filters to the KU Abroad app.
**Source:** `https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01` (UCPH Mobility-Online portal).
**Decision:** Do the mapping. We will scrape the static option lists, then run filtered searches through the portal to map each Study field / Faculty / Study area to the partners that appear.

## Is it even possible?

- The existing partner-detail and agreement-detail HTML files **do not** contain clean UCPH Faculty/Department/Study-field fields. Those modals are partner-centric.
- However, the portal search form itself exposes hardcoded dropdowns for **Faculty** (6), **Study area** (6) and **Study field** (~174 values).
- The portal already supports filtered searches, so we can discover mappings by executing a search for each filter value and recording which partners/agreements show up.
- **Bottom line:** yes, it is possible. We need to interact with the search form, not just parse detail HTML.

## Proposed workflow

### Phase 1 — Scrape static filter vocabularies

**Goal:** Capture human-readable labels and their current hashed form-field names/values.

1. Add a script: `scripts/scrape_portal_filter_options.py`
   - Fetches the portal search form HTML.
   - Parses every `<select>` and `<input type="radio">` inside `<form name="search_form">`.
   - Records:
     - Field label
     - Hashed form-field `name`
     - Human-readable text for each option
     - Hashed `value` for each option
   - Outputs:
     - `data/portal_filter_options.json`
     - `data/portal_form_params.json` (matching format already in `.firecrawl/`)

This script is read-only, low load, and can be re-run whenever the portal refreshes its hashes.

### Phase 2 — Map filters to partner IDs

**Goal:** For each Faculty, Study area and Study field, find which `partner_match` values appear in the result table.

1. Add a script: `scripts/scrape_filter_to_partner.py`
   - Opens the portal once in Playwright (same pattern as `fetch_partner_details_playwright.py`).
   - Loads the current form parameters from the page.
   - For each value of **Study field** (main driver), **Faculty** and **Study area**:
     1. Set the corresponding hidden `<select>` to the target value.
     2. Trigger Bootstrap-select refresh and `onchange`.
     3. Click `#search_button`.
     4. Wait for the DataTable to reload.
     5. Extract `aaData` rows and collect `partner_match` tokens.
     6. Record them under the human-readable filter label.
   - Uses checkpointing (same style as existing Playwright scripts) so it can resume.
   - Outputs:
     - `data/filter_partner_mappings.json`
     - Expected shape:
       ```json
       {
         "generatedAt": "...",
         "faculty": {
           "Faculty of Law": ["match1", "match2", ...],
           ...
         },
         "studyArea": {
           "Law": [...],
           ...
         },
         "studyField": {
           "Laws": [...],
           ...
         }
       }
       ```

2. Derive a Study field → Faculty/Study area lookup.
   - Because the same search results can overlap, compute the overlap between each Study field result set and each Faculty / Study area result set.
   - Output:
     - `data/study_field_to_metadata.json`
     - Expected shape:
       ```json
       {
         "Laws": {
           "faculty": "Faculty of Law",
           "studyArea": "Law"
         },
         ...
       }
       ```
   - This lets us display each Study field under its Faculty/Study area in the UI without manual data entry.

**Estimated load:** ~6 Faculty + 6 Study area + ~174 Study field = ~186 searches. With small delays and checkpointing, this is well within polite scraping limits for a one-time build.

### Phase 3 — Merge into the dataset

1. Update `scripts/build-data.ts`:
   - Load `data/filter_partner_mappings.json`.
   - For each institution, add the filter labels that contain its `partner_match`:
     ```ts
     faculties: string[]
     studyAreas: string[]
     studyFields: string[]
     ```
   - Keep the arrays sorted and deduplicated.

2. Update `src/lib/types.ts`:
   - Add the three arrays to the `Institution` interface.

3. Update `src/components/filter-bar.tsx` and `src/components/dashboard-shell.tsx`:
   - Add three new filters.
   - Compute passing institutions as before: if an institution-level filter matches or any agreement matches, the institution is kept.

### Phase 4 — UI polish (optional but recommended)

- Show Study field grouped by Faculty or Study area in the dropdown.
- Add a reset button for the new filters (or extend the existing reset).
- Update summary cards / counts so users see how many partners are available per Faculty.

## Files that will be created or changed

| Path | Action |
|---|---|
| `scripts/scrape_portal_filter_options.py` | Create |
| `scripts/scrape_filter_to_partner.py` | Create |
| `data/portal_filter_options.json` | Generated |
| `data/filter_partner_mappings.json` | Generated |
| `data/study_field_to_metadata.json` | Generated |
| `scripts/build-data.ts` | Update |
| `src/lib/types.ts` | Update |
| `src/components/filter-bar.tsx` | Update |
| `src/components/dashboard-shell.tsx` | Update |

## Key technical concerns

- **Hashed form names and values.** Mobility-Online uses long `cpif_..._sep_...` tokens for field names and values. We must parse them fresh from the HTML every session; they likely change between deployments.
- **Bootstrap-select interaction.** The visible selects are Bootstrap-select widgets. Setting the value directly on the hidden `<select>` must be followed by `.selectpicker('refresh')` and a `change` trigger before `#search_button` works.
- **Dynamic Department dropdown.** We are not scraping Department (per the scope "we just need study field"), but note that the Department select is populated after Faculty changes and could be added later using the same pattern.
- **Session binding.** All detail tokens are session-bound. We already handle this by doing everything in a single Playwright browser context, so the same approach applies here.
- **Rate limiting / politeness.** Add ~0.5–1 s delay between filtered searches, use checkpointing, and avoid parallelizing across multiple sessions.
- **Data freshness.** This is a point-in-time scrape. When the portal updates academic years or study fields, re-run Phases 1–2.

## Open question before implementation

The plan assumes each Study field maps to one Faculty and one Study area. The overlap heuristic in Phase 2 should confirm this, but if a Study field belongs to multiple faculties we may need to adjust the mapping to support multiple values. We can detect such cases automatically when computing overlaps.

Ready to proceed with Phases 1 and 2.
