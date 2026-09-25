#!/usr/bin/env python3
"""Collect public exchange questionnaires into a separate validated run."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from portal_client import Portal
from portal_data import Archive, PORTAL_URL, ROOT, atomic_json, now, parse_partner


def archived(run: Path, ref: str | None, expected_sha: str | None = None) -> bool:
    if not ref or not ref.startswith('bodies/') or '/' in ref[7:-3]:
        return False
    path = run / ref
    if not path.is_file():
        return False
    try:
        raw = gzip.decompress(path.read_bytes())
    except (OSError, EOFError):
        return False
    digest = hashlib.sha256(raw).hexdigest()
    return ref == f'bodies/{digest}.gz' and (expected_sha is None or digest == expected_sha)


def complete_institution(run, progress, reports, reported_count, institution_id=None):
    if progress.get('reportedCount') != reported_count:
        return False
    ids = progress.get('reportIds')
    if not isinstance(ids, list) or len(ids) != reported_count or len(set(ids)) != len(ids):
        return False
    if reported_count and not archived(run, progress.get('listRef')):
        return False
    return all(report_id in reports and
               (institution_id is None or reports[report_id].get('institutionId') == institution_id) and
               bool(reports[report_id].get('questions')) and
               archived(run, reports[report_id].get('sourceRef'),
                        reports[report_id].get('rawSha256'))
               for report_id in ids)


def open_unfiltered_overview(portal):
    portal.page.locator('button[value="Reports"]').click()
    portal.idle()
    # The Reports view requires a study field. Selecting every offered value
    # yields the portal's full historic outgoing-student report count, while
    # leaving academic year empty keeps earlier exchanges in scope.
    portal.page.evaluate('''() => {
        const select = [...document.querySelectorAll('#search_form select')]
          .find(s => document.querySelector('label[for="' + s.id + '"]')?.innerText === 'Study field');
        if (!select || !select.options.length) throw Error('Missing study-field options');
        jQuery(select).selectpicker('val', [...select.options].map(o => o.value));
    }''')
    selected = portal.page.evaluate('''() => Object.fromEntries(
        [...document.querySelectorAll('#search_form select')]
          .filter(s => ['Academic year', 'Study field'].includes(
              document.querySelector('label[for="' + s.id + '"]')?.innerText))
          .map(s => [document.querySelector('label[for="' + s.id + '"]')?.innerText,
                     {selected:[...s.selectedOptions].map(o => o.value),
                      offered:[...s.options].map(o => o.value)}]))''')
    if set(selected) != {'Academic year', 'Study field'}:
        raise ValueError(f'Could not verify unfiltered report baseline: {selected}')
    if (selected['Academic year']['selected'] or
            selected['Study field']['selected'] != selected['Study field']['offered']):
        raise ValueError(f'Report baseline is filtered: {selected}')
    portal.params = portal.live_params()
    portal.resolve_cause_field()
    portal.archive.save(json.dumps(selected).encode(), url=PORTAL_URL,
                        kind='report-baseline-filters')


def collect(portal, run, state, retries=3):
    # Reports with all study fields and no academic year is the verified
    # historic outgoing-student baseline.
    open_unfiltered_overview(portal)
    rows = portal.table()
    table_refs = list(portal.table_refs)
    partners = [parse_partner(row) for row in rows]
    if not partners:
        raise ValueError('All institutions table is empty')
    state['institutionTableRefs'] = table_refs
    state['observedInstitutions'] = len(partners)
    state['reportedTotal'] = sum(item['reportCount'] for item in partners)
    portal_count = portal.page.evaluate(
        "Number(document.querySelector('.count_quest')?.getAttribute('data-to')) || null")
    state['portalReportCount'] = portal_count
    if portal_count is not None and state['reportedTotal'] != portal_count:
        raise ValueError(f'Report table total {state["reportedTotal"]} differs '
                         f'from portal counter {portal_count}')
    global_label = portal.page.evaluate(
        "document.querySelector('.quest_stat_text')?.textContent || ''")
    global_match = re.search(r'([\d,]+)\s+questionnaires', global_label)
    state['portalGlobalCount'] = (int(global_match.group(1).replace(',', ''))
                                  if global_match else None)
    state['updatedAt'] = now()
    atomic_json(run / 'state.json', state)

    batch_results = {}
    batch_size = max(1, portal.concurrency)
    for index, partner in enumerate(partners, 1):
        if (index - 1) % batch_size == 0:
            candidates = partners[index-1:index-1+batch_size]
            pending = [item for item in candidates if not complete_institution(
                run, state['institutions'].get(item['id'], {}), state['reports'],
                item['reportCount'], item['id'])]
            try:
                batch_results = portal.reports_many(pending)
            except Exception as error:
                print(f'Batch fetch fallback: {error}', flush=True)
                batch_results = {}
        institution_id = partner['id']
        progress = state['institutions'].get(institution_id, {})
        if (progress.get('reportedCount') is not None and
                progress['reportedCount'] != partner['reportCount']):
            raise ValueError(f"Report count changed for {partner['name']}; start a new run")
        if complete_institution(run, progress, state['reports'], partner['reportCount'], institution_id):
            continue
        for attempt in range(retries):
            try:
                prefetched = batch_results.pop(institution_id, None)
                reports, list_ref = (prefetched if prefetched is not None
                                     else portal.reports(partner))
                new_ids = [item['id'] for item in reports]
                if progress.get('reportIds') and progress['reportIds'] != new_ids:
                    raise ValueError(f"Report list changed for {partner['name']}; start a new run")
                for item in reports:
                    old = state['reports'].get(item['id'])
                    if old and (old['institutionId'] != institution_id or
                                old['contentSha256'] != item['contentSha256']):
                        raise ValueError(f"Changed content or ID collision: {item['id']}")
                for item in reports:
                    state['reports'][item['id']] = item
                state['institutions'][institution_id] = dict(
                    name=partner['name'], reportedCount=partner['reportCount'],
                    reportIds=new_ids, listRef=list_ref,
                    collectedAt=now())
                state['updatedAt'] = now()
                atomic_json(run / 'state.json', state)
                print(f'Reports {index}/{len(partners)}: {partner["name"]} '
                      f'({len(reports)})', flush=True)
                break
            except Exception as error:
                if attempt + 1 == retries:
                    state['institutions'][institution_id] = dict(
                        name=partner['name'], reportedCount=partner['reportCount'],
                        status='error', error=str(error), attemptedAt=now())
                    atomic_json(run / 'state.json', state)
                    print(f'ERROR {partner["name"]}: {error}', flush=True)
                else:
                    time.sleep(2 * (attempt + 1))
                    portal.open()
                    open_unfiltered_overview(portal)

    discrepancies = []
    for partner in partners:
        progress = state['institutions'].get(partner['id'], {})
        if not complete_institution(run, progress, state['reports'], partner['reportCount'], partner['id']):
            discrepancies.append(dict(institutionId=partner['id'],
                institution=partner['name'], reportedCount=partner['reportCount'],
                archivedCount=len(progress.get('reportIds', [])),
                sourceRefs=table_refs, error=progress.get('error')))
    referenced = [report_id for progress in state['institutions'].values()
                  for report_id in progress.get('reportIds', [])]
    if len(referenced) != len(set(referenced)):
        discrepancies.append(dict(error='Report ID appears under multiple institutions'))
    unreferenced = set(state['reports']) - set(referenced)
    if unreferenced:
        discrepancies.append(dict(error='Orphaned reports in run state', count=len(unreferenced)))
    quality = dict(at=now(), sourceUrl=PORTAL_URL,
                   status='complete' if not discrepancies else 'incomplete',
                   observedInstitutions=len(partners),
                   reportedTotal=state['reportedTotal'],
                   portalReportCount=state['portalReportCount'],
                   portalGlobalCount=state['portalGlobalCount'],
                   differenceFromGlobal=(state['portalGlobalCount'] - state['reportedTotal']
                       if state['portalGlobalCount'] is not None else None),
                   collectedReports=len(referenced), discrepancies=discrepancies,
                   note='Global questionnaire counter includes questionnaires outside the outgoing-student report set.')
    atomic_json(run / 'quality-report.json', quality)
    if discrepancies:
        raise ValueError('Report run is incomplete; publication marker retained')
    state['completedAt'] = now()
    atomic_json(run / 'state.json', state)
    atomic_json(ROOT / 'data' / 'current_report_run.json',
                dict(runId=run.name, completedAt=state['completedAt']))
    print(json.dumps(quality, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--delay', type=float, default=0.5)
    parser.add_argument('--concurrency', type=int, default=6)
    args = parser.parse_args()
    if args.run != Path(args.run).name:
        parser.error('--run must be a directory name')
    run = ROOT / 'data' / 'report-runs' / args.run
    run.mkdir(parents=True, exist_ok=True)
    state_path = run / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else dict(
        schemaVersion=1, runId=args.run, startedAt=now(),
        institutions={}, reports={})
    if state.get('runId') != args.run:
        raise ValueError('State run ID does not match directory')
    if not state_path.exists():
        atomic_json(state_path, state)
    archive = Archive(run)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        portal = Portal(browser, archive, delay=max(args.delay, 0.05),
                        concurrency=max(1, min(args.concurrency, 16)))
        try:
            collect(portal, run, state)
        except Exception as error:
            atomic_json(run / 'last-attempt.json', dict(
                at=now(), status='blocked', error=str(error),
                tableRefs=getattr(portal, 'table_refs', [])))
            raise
        finally:
            portal.close()
            browser.close()


if __name__ == '__main__':
    main()
