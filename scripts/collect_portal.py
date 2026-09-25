#!/usr/bin/env python3
"""Verified, resumable portal collection.

uv run python scripts/collect_portal.py --verify --run RUN_ID
uv run python scripts/collect_portal.py --collect --run RUN_ID --concurrency 6
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import time

from playwright.sync_api import sync_playwright
from portal_client import Portal
from portal_data import ROOT, Archive, PORTAL_URL, atomic_json, now, parse_partner


ACCEPTED_SOURCE_DISCREPANCIES = {
    ('2026/2027', 'Houston Methodist Hospital – Texas Medical Center',
     'Houston Methodist Hospital – Texas Medical Center: table reports 2 agreements, popup contains 1')
}


def key(year, field=None):
    return year + '|' + (field or '*')


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def verify(portal, run):
    years = sorted(set(o['label'] for o in portal.options['Academic year']))
    fields = ['Laws', 'Medicine', 'Computer Science']
    atomic_json(ROOT/'data'/'portal_catalog.json', dict(observedAt=now(), academicYears=years, studyFields=sorted(set(o['label'] for o in portal.options['Study field']))))
    evidence, errors = [], []
    atomic_json(run/'verification.json', dict(status='running', at=now()))
    if len(years) < 2:
        raise ValueError('Verification requires at least two available years')
    for year in years[:2]:
        baseline = portal.search(year)
        identities = {parse_partner(r)['id']:parse_partner(r)['agreementCount'] for r in baseline}
        evidence.append(portal.verify_visible(baseline, paginate=True))
        for field in fields:
            rows = portal.search(year, field)
            item = portal.verify_visible(rows)
            partners = [parse_partner(r) for r in rows]
            if any(p['id'] not in identities or p['agreementCount'] > identities[p['id']] for p in partners):
                errors.append(f'{year}/{field}: result not a subset of baseline')
            # Check the first narrowed institution and the first full-count institution.
            # Include the observed Houston discrepancy on every verification run.
            samples = {p['id']:p for p in [
                next((p for p in partners if p['agreementCount'] < identities.get(p['id'],0)), None),
                next((p for p in partners if p['agreementCount'] == identities.get(p['id'],0)), None),
                next((p for p in partners if 'Houston Methodist' in p['name']), None),
            ] if p}
            item['agreementSamples'] = []
            for partner in samples.values():
                try:
                    details, ref = portal.agreements(partner, verify_visible=True)
                    item['agreementSamples'].append(dict(institution=partner['name'], count=len(details), status='passed', sourceRef=ref))
                except ValueError as error:
                    error_text = str(error)
                    if (year, partner['name'], error_text) in ACCEPTED_SOURCE_DISCREPANCIES:
                        item['agreementSamples'].append(dict(
                            institution=partner['name'], status='source-discrepancy', error=error_text,
                            accepted=True, sourceRef=portal.table_refs[-1] if portal.table_refs else None))
                    else:
                        errors.append(f'{year}/{field}: {error_text}')
                        item['agreementSamples'].append(dict(
                            institution=partner['name'], status='failed', error=error_text))
            evidence.append(item)
            atomic_json(run/'verification-progress.json', evidence)
            print(f'Checked {year} / {field}: {len(rows)} institutions; {len(errors)} discrepancies', flush=True)
        reset = portal.search(year)
        if {parse_partner(r)['id']:parse_partner(r)['agreementCount'] for r in reset} != identities:
            errors.append(f'{year}: reset did not restore baseline')
    report = dict(status='failed' if errors else 'passed', at=now(), sourceUrl=PORTAL_URL,
                  evidence=evidence, errors=errors, resetVerified=not any('reset' in e for e in errors))
    atomic_json(run/'verification.json', report)
    if errors:
        raise ValueError('Verification failed; full collection is blocked. See verification.json.')
    return report


def save_state(run, state):
    state['updatedAt'] = now()
    atomic_json(run/'state.json', state)


def checkpoint_query(run, query_key, query):
    """Persist one completed/failed query without rewriting the full run state."""
    path = run/'checkpoint.sqlite3'
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as database:
        database.execute('PRAGMA journal_mode=WAL')
        database.execute('''CREATE TABLE IF NOT EXISTS query_checkpoint (
            query_key TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL
        )''')
        database.execute(
            '''INSERT INTO query_checkpoint(query_key,payload,updated_at) VALUES(?,?,?)
               ON CONFLICT(query_key) DO UPDATE SET
                 payload=excluded.payload, updated_at=excluded.updated_at''',
            (query_key, json.dumps(query, ensure_ascii=False, separators=(',',':')), now()))


def restore_query_checkpoints(run, state):
    path = run/'checkpoint.sqlite3'
    if not path.exists():
        return state
    with sqlite3.connect(path) as database:
        exists = database.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='query_checkpoint'"
        ).fetchone()
        if not exists:
            return state
        for query_key, payload in database.execute(
                'SELECT query_key,payload FROM query_checkpoint'):
            query = json.loads(payload)
            # Never resurrect mappings produced by the old count-only subset path.
            if any(match.get('method') == 'filtered-count-subset-reusing-baseline'
                   for match in query.get('matches', [])):
                continue
            state.setdefault('queries', {})[query_key] = query
    return state


def migrate_state(state):
    """Upgrade resumable state without trusting the old inexact subset mapping."""
    if state.get('schemaVersion', 1) >= 2:
        return state
    state['queries'] = {
        query_key: query for query_key, query in state.get('queries', {}).items()
        if all(match.get('method') != 'filtered-count-subset-reusing-baseline'
               for match in query.get('matches', []))
    }
    known_agreements = set(state.get('agreements', {}))
    state['baselineProgress'] = {
        item_key: record for item_key, record in state.get('baselineProgress', {}).items()
        if set(record.get('ids', [])).issubset(known_agreements)
    }
    state.pop('completedAt', None)
    state['schemaVersion'] = 2
    return state


def map_filtered_partner(portal, partner, baseline_record, agreements, resolved=None):
    """Return exact canonical agreement IDs for one filtered institution row."""
    baseline_ids = list(baseline_record['ids'])
    baseline_set = set(baseline_ids)
    baseline_count = baseline_record.get('reportedCount', len(baseline_ids))
    filtered_count = partner['agreementCount']
    if filtered_count > baseline_count:
        raise ValueError(
            f"{partner['name']}: filtered count {filtered_count} exceeds "
            f"baseline count {baseline_count}"
        )
    if filtered_count == baseline_count:
        return dict(institutionId=partner['id'], agreementIds=baseline_ids,
                    sourceRef=baseline_record['sourceRef'],
                    method=('filtered-count-equals-discrepant-baseline'
                            if baseline_record.get('sourceDiscrepancy') else
                            'filtered-count-equals-baseline'))

    # Popup rows only expose institution/country plus an opaque, request-specific
    # detail token. Narrowed results must fetch their detail pages to identify the
    # exact canonical agreements.
    details, source_ref = resolved or portal.agreement_details(partner)
    discrepancies = [item.get('sourceDiscrepancy') for item in details
                     if item.get('sourceDiscrepancy')]
    details = [item for item in details if not item.get('sourceDiscrepancy')]
    if discrepancies or len(details) != filtered_count:
        raise ValueError(
            f"{partner['name']}: cannot map filtered agreements exactly "
            f"(table {filtered_count}, details {len(details)})"
        )
    ids = [item['id'] for item in details]
    if len(ids) != len(set(ids)):
        raise ValueError('Filtered result contains indistinguishable duplicate agreements')
    unknown_ids = [agreement_id for agreement_id in ids if agreement_id not in baseline_set]
    if unknown_ids:
        raise ValueError(f'Filtered agreements not in year baseline: {unknown_ids}')
    for item in details:
        agreements.setdefault(item['id'], item)
    return dict(institutionId=partner['id'], agreementIds=ids,
                sourceRef=source_ref, method='filtered-details-mapped-to-baseline')


def collect(portal, run, state):
    migrate_state(state)
    years = sorted(set(o['label'] for o in portal.options['Academic year']))
    fields = sorted(set(o['label'] for o in portal.options['Study field']))
    if state.get('academicYears') and (state['academicYears']!=years or state['studyFields']!=fields):
        raise ValueError('Portal vocabulary changed; start a new run to avoid mixing snapshots')
    state.update(academicYears=years, studyFields=fields)
    if not state.get('overviewComplete'):
        portal.search(years[0])
        portal.page.locator('button[value="All"]').click()
        portal.idle()
        # Capture the exact post-search form for the general partner overview.
        portal.params = portal.page.evaluate("jQuery('#search_form').find(':not(.none_request)').serialize()")
        overview = portal.table()
        missing = [parse_partner(row) for row in overview
                   if parse_partner(row)['id'] not in state['institutions']]
        batch_size = max(1, portal.concurrency * 8)
        for start in range(0, len(missing), batch_size):
            batch = missing[start:start+batch_size]
            resolved = portal.details_many(batch)
            for partner in batch:
                details, ref = resolved[partner['id']]
                safe = {k:v for k,v in partner.items() if k not in ('detailUrl','agreementToken','reportToken')}
                safe.update(partnerDetails=details, sourceRef=ref)
                state['institutions'][partner['id']] = safe
            save_state(run, state)
            print(f"Institution details: {len(state['institutions'])}/{len(overview)}", flush=True)
        state['overviewComplete'] = True
        save_state(run, state)
        portal.page.locator('button[value="Agreements"]').click()
        portal.idle()
    state.setdefault('yearInstitutions', {})
    state.setdefault('yearTableRefs', {})
    state.setdefault('baselineYearComplete', [])
    for year in years:
        baseline_partners = None
        if state['yearInstitutions'].get(year) is None:
            rows = portal.search(year)
            state['yearInstitutions'][year] = {parse_partner(row)['id']:parse_partner(row)['agreementCount'] for row in rows}
            state['yearTableRefs'][year] = list(portal.table_refs)
            save_state(run,state)
        if year not in state['baselineYearComplete']:
            baseline_partners = {parse_partner(row)['id']:parse_partner(row) for row in portal.search(year)}
        year_ids = set(state['yearInstitutions'][year])
        baseline_record_by_year = {
            item_key.split('|',1)[1]: record
            for item_key, record in state['baselineProgress'].items()
            if item_key.startswith(year+'|')
        }
        if year not in state['baselineYearComplete'] or len(baseline_record_by_year) != len(year_ids):
            if baseline_partners is None:
                baseline_partners = {
                    parse_partner(row)['id']:parse_partner(row)
                    for row in portal.search(year)
                }
            missing = []
            for institution_id in state['yearInstitutions'][year]:
                item_key = key(year, institution_id)
                existing = state['baselineProgress'].get(item_key)
                if existing and set(existing.get('ids', [])).issubset(state['agreements']):
                    continue
                missing.append(baseline_partners[institution_id])
            batch_size = max(1, portal.concurrency * 8)
            for start in range(0, len(missing), batch_size):
                batch = missing[start:start+batch_size]
                resolved = portal.agreement_details_many(batch)
                for current_partner in batch:
                    institution_id = current_partner['id']
                    agreement_count = state['yearInstitutions'][year][institution_id]
                    agreement_details, source_ref = resolved[institution_id]
                    source_discrepancies = [item.get('sourceDiscrepancy') for item in agreement_details if item.get('sourceDiscrepancy')]
                    agreement_details = [item for item in agreement_details if not item.get('sourceDiscrepancy')]
                    if len(agreement_details) != agreement_count and not source_discrepancies:
                        raise ValueError(f"Year baseline count mismatch for {institution_id}: table {agreement_count}, details {len(agreement_details)}")
                    ids=[item['id'] for item in agreement_details]
                    if len(ids)!=len(set(ids)):
                        raise ValueError('Year baseline contains indistinguishable duplicate agreements')
                    for item in agreement_details:
                        state['agreements'].setdefault(item['id'],item)
                    state['baselineProgress'][key(year,institution_id)] = dict(
                        ids=ids, sourceRef=source_ref, reportedCount=agreement_count,
                        sourceDiscrepancy=source_discrepancies[0] if source_discrepancies else None)
                save_state(run,state)
                completed = len([k for k in state['baselineProgress'] if k.startswith(year+'|')])
                print(f"Year baseline: {completed}/{len(year_ids)}",flush=True)
            if len([k for k in state['baselineProgress'] if k.startswith(year+'|')]) == len(year_ids):
                if year not in state['baselineYearComplete']:
                    state['baselineYearComplete'].append(year)
                save_state(run,state)
        baseline_agreement_ids = {
            item_key.split('|',1)[1]: dict(
                ids=record['ids'], sourceRef=record['sourceRef'],
                reportedCount=record.get(
                    'reportedCount',
                    state['yearInstitutions'][year][item_key.split('|',1)[1]]),
                sourceDiscrepancy=record.get('sourceDiscrepancy'))
            for item_key, record in state['baselineProgress'].items()
            if item_key.startswith(year+'|')
        }
        state['queries'][key(year)] = dict(
            academicYear=year, studyField=None, status='success', collectedAt=now(),
            tableRefs=state['yearTableRefs'].get(year, []),
            matches=[dict(institutionId=institution_id,
                          agreementIds=baseline_agreement_ids[institution_id]['ids'],
                          sourceRef=baseline_agreement_ids[institution_id]['sourceRef'],
                          method='year-baseline')
                     for institution_id in sorted(year_ids)],
            method='year-baseline')
        checkpoint_query(run, key(year), state['queries'][key(year)])
        for field in fields:
            query_key = key(year, field)
            previous = state['queries'].get(query_key, {})
            if previous.get('status') == 'success':
                continue
            accepted_source_discrepancies = []
            for attempt in range(3):
                institution_id = None
                try:
                    # Build the request from the complete form vocabulary. After
                    # a UI search, dependent selects may omit valid combinations
                    # that simply have zero rows. Retried attempts reopen the form
                    # below, so they also use this direct, deterministic path.
                    params = portal.filtered_params(year, field)
                    rows = portal.table_for_params(params, context=dict(academicYear=year, studyField=field,
                        application='Outgoing', person='Students'))
                    table_refs = list(portal.table_refs)
                    matches = []
                    partners = [parse_partner(row) for row in rows]
                    partial = []
                    for partner in partners:
                        institution_id = partner['id']
                        if institution_id not in year_ids:
                            raise ValueError('Filtered result contains institution outside year baseline')
                        if not partner['agreementCount']:
                            raise ValueError('Agreements tab returned an institution without agreements')
                        baseline_record = baseline_agreement_ids[institution_id]
                        if partner['agreementCount'] < baseline_record['reportedCount']:
                            partial.append(partner)
                    resolved_partial = portal.agreement_details_many(partial)
                    for partner in partners:
                        institution_id = partner['id']
                        baseline_record = baseline_agreement_ids[institution_id]
                        matches.append(map_filtered_partner(
                            portal, partner, baseline_record, state['agreements'],
                            resolved_partial.get(institution_id)))
                        if institution_id not in state['institutions']:
                            details, ref = portal.details(partner)
                            safe_partner = {k:v for k,v in partner.items() if k not in ('detailUrl','agreementToken','reportToken')}
                            safe_partner.update(partnerDetails=details, sourceRef=ref)
                            state['institutions'][institution_id] = safe_partner
                    query = dict(academicYear=year, studyField=field, status='success',
                        collectedAt=now(), tableRefs=table_refs, matches=matches,
                        method='exact-filtered-agreement-mapping',
                        acceptedSourceDiscrepancies=accepted_source_discrepancies)
                    state['queries'][query_key] = query
                    checkpoint_query(run, query_key, query)
                    if sum(q.get('status') == 'success'
                           for q in state['queries'].values()) % 25 == 0:
                        save_state(run, state)
                    print(f'{year} / {field}: {len(matches)} institutions, {sum(len(m["agreementIds"]) for m in matches)} agreements', flush=True)
                    break
                except Exception as e:
                    state['queries'][query_key] = dict(academicYear=year, studyField=field,
                        status='error', attemptedAt=now(), error=str(e), attempts=attempt+1,
                        institutionId=institution_id)
                    checkpoint_query(run, query_key, state['queries'][query_key])
                    print(f'ERROR {query_key} attempt {attempt+1}: {e}', flush=True)
                    selection_error = (str(e).startswith('Missing query option:') or
                                       str(e) == 'Portal did not retain selected year/field')
                    if selection_error and attempt > 0:
                        try:
                            available_fields, evidence_ref = portal.available_study_fields(year)
                        except Exception as availability_error:
                            print(f'Could not verify fields available for {year}: '
                                  f'{availability_error}', flush=True)
                        else:
                            if field not in available_fields:
                                query = dict(
                                    academicYear=year, studyField=field, status='success',
                                    collectedAt=now(), tableRefs=[], matches=[],
                                    method='year-unavailable-study-field',
                                    availabilityEvidenceRef=evidence_ref,
                                    acceptedSourceDiscrepancies=[])
                                state['queries'][query_key] = query
                                checkpoint_query(run, query_key, query)
                                print(f'{year} / {field}: unavailable for academic year; '
                                      'recorded as 0 institutions', flush=True)
                                break
                    if attempt < 2:
                        time.sleep(2*(attempt+1))
                        portal.open()
    baseline_errors=[]
    for record in state['baselineProgress'].values():
        if record.get('sourceDiscrepancy'):
            baseline_errors.append(record['sourceDiscrepancy'])
    expected = len(years)*(len(fields)+1)
    errors = [q for q in state['queries'].values() if q['status']!='success']
    report = dict(at=now(), expectedQueries=expected, successfulQueries=sum(q['status']=='success' for q in state['queries'].values()),
                  failedQueries=errors, institutions=len(state['institutions']), agreements=len(state['agreements']),
                  duplicateInstitutions=0, unresolvedMatches=0, baselineDiscrepancies=baseline_errors,
                  status='complete' if not errors and len(state['queries'])==expected else 'incomplete')
    # Keep state.json aligned with the query checkpoint even when publication is
    # blocked, so diagnostics do not under-report late successes or failures.
    save_state(run, state)
    atomic_json(run/'quality-report.json', report)
    if report['status'] != 'complete':
        raise ValueError('Incomplete run; previous published dataset retained')
    state['completedAt'] = now()
    save_state(run,state)
    atomic_json(ROOT/'data'/'current_portal_run.json',dict(runId=run.name, completedAt=state['completedAt']))
    print(json.dumps(report,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--verify',action='store_true')
    mode.add_argument('--collect',action='store_true')
    parser.add_argument('--run',default=None)
    parser.add_argument('--delay',type=float,default=0.5)
    parser.add_argument('--concurrency',type=int,default=6)
    args=parser.parse_args()
    run_id=args.run or now().replace(':','-').replace('+','-')
    if Path(run_id).name != run_id:
        parser.error('--run must be a directory name')
    run=ROOT/'data'/'portal-runs'/run_id
    archive=Archive(run)
    state=load(run/'state.json',dict(schemaVersion=2,runId=run_id,startedAt=now(),
        institutions={},agreements={},queries={},baselineProgress={},queryProgress={}))
    restore_query_checkpoints(run, state)
    print(f'Run: {run_id}',flush=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        portal=Portal(browser,archive,delay=max(args.delay,0.05),
                      concurrency=max(1,min(args.concurrency,16)))
        try:
            if args.verify:
                verify(portal,run)
            else:
                proof=load(run/'verification.json',{})
                if proof.get('status')!='passed':
                    raise ValueError('Run --verify for this run before full collection')
                collect(portal,run,state)
        finally:
            portal.close()
            browser.close()


if __name__ == '__main__':
    main()
