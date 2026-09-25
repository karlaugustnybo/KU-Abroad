# Public questionnaire source inspection — 2026-09-24

Disposable source evidence is under `data/portal-investigation/reports-2026-09-24-details/`
in the content-addressed archive format. The archive is deliberately outside
the frontend bundle.

- The initial All page rendered institution report counts and `openFancy('quest',
  token)` actions. Its first ten institutions included counts from 0 to 62.
  Tokens changed between sessions and are request parameters, not identities.
- The `quest` popup POST returned JSON with `columns`, `data_header`, and
  `data`. The columns observed were home institution, partner institution,
  host country, study field, academic year, and a detail action. Three
  sampled institutions showed 2/2, 2/2, and 12/12 list rows relative to their
  displayed counts. The rendered popup for University of Buenos Aires also
  showed two rows, matching its JSON response.
- The detail action opens a public `DispQuestionServlet?match=...` page. Three
  sampled detail requests returned HTTP 200 HTML in the ordinary portal
  session. The read-only form contains `bew_id` and `q_set_id` source fields,
  section headings, ordered question blocks, selected radio choices, plain
  text answers, and read-only numeric answers. Some answers contain links.
  Six inspected pages across 2022/2023–2025/2026 contained 54–59 questions.
  `bew_id` is hashed for persistent identity; the raw value remains only in
  the private source archive.
- The Reports tab requires a study field. Selecting **all 172 study fields**
  with no academic year selected returned 339 report-bearing institutions and
  5,169 reports, matching the portal's outgoing-student questionnaire counter.
  Sample counts for University of Buenos Aires (2), Australian National
  University (12), and Monash University (62) matched the unfiltered initial
  page. This is the verified collection baseline. A current-year search
  followed by All returned 525 institutions but only one report in total, so
  that path is rejected for historic collection.
- During the first inspection, the unfiltered All AJAX table reported 525
  total rows while returning an empty `aaData` array. The verified Reports
  view above provides the complete public outgoing-student report set and
  avoids that source failure. The earlier blocked attempt is recorded in
  `data/report-runs/2026-09-24-attempt/last-attempt.json`; no report publication
  marker was written by that attempt.

Before any public use, review full free-text responses and attachments for
names, email addresses, and other identifying material. Current code only
creates private archive and DuckDB outputs.
