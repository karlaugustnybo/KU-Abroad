#!/usr/bin/env python3
"""Collect public source data first. Never publishes or infers missing agreement matches.

uv run python scripts/archive_portal.py --run 2026-09-18
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from portal_client import Portal
from portal_data import (ROOT, Archive, PORTAL_URL, PORTAL_POST, now, atomic_json,
                         parse_partner, partner_details, action, digest)
from parse_agreement_details import parse_detail_html


def load(path, fallback):
    return json.loads(path.read_text()) if path.exists() else fallback


def save(run, state):
    state['runId'] = run.name
    state['updatedAt'] = now()
    atomic_json(run/'source-state.json', state)


def inventory_links(html, ref, state):
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup.select('[href], img[src], iframe[src]'):
        value = element.get('href') or element.get('src')
        if not value or value.startswith(('#', 'javascript:')):
            continue
        url = urljoin(PORTAL_POST, value)
        item = state['links'].setdefault(url, dict(url=url, label=element.get_text(' ',strip=True), sourceRefs=[], status='reference-only'))
        if ref not in item['sourceRefs']:
            item['sourceRefs'].append(ref)


def fetch_html(portal, url, state):
    html, ref = portal.request(url)
    inventory_links(html, ref, state)
    return html, ref


def retry(portal, operation, *, refresh=None):
    for attempt in range(3):
        try:
            return operation()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2*(attempt+1))
            if refresh:
                refresh()


def collect_overview(portal, run, state, year):
    if state.get('overviewComplete'):
        return
    portal.search(year)
    portal.page.locator('button[value="All"]').click()
    portal.idle()
    portal.params = portal.page.evaluate("jQuery('#search_form').find(':not(.none_request)').serialize()")
    rows = portal.table()
    state['overviewTableRefs'] = list(portal.table_refs)
    state['overviewExpected'] = len(rows)
    for index, row in enumerate(rows, 1):
        partner = parse_partner(row)
        old = state['institutions'].get(partner['id'], {})
        if old.get('status') == 'success':
            continue
        portal.archive.context = dict(phase='institution', institution=partner['name'])
        try:
            html, ref = retry(portal, lambda: fetch_html(portal,partner['detailUrl'],state))
            parsed = partner_details(html)
            state['institutions'][partner['id']] = dict(**partner, rawRow=row, details=parsed, sourceRef=ref, status='success', collectedAt=now())
        except Exception as error:
            state['institutions'][partner['id']] = dict(**partner, rawRow=row, status='error', error=str(error))
        save(run,state)
        if index % 10 == 0:
            print(f'Institutions {index}/{len(rows)}',flush=True)
    state['overviewComplete'] = len(state['institutions'])==len(rows) and all(v['status']=='success' for v in state['institutions'].values())
    save(run,state)
    portal.page.locator('button[value="Agreements"]').click()
    portal.idle()


def collect_baselines(portal, run, state, years):
    for year in years:
        rows = portal.search(year)
        state['baselineTables'][year] = dict(sourceRefs=list(portal.table_refs), rows=rows, collectedAt=now())
        for index, row in enumerate(rows, 1):
            partner = parse_partner(row)
            item_key = year+'|'+partner['id']
            if state['agreementLists'].get(item_key,{}).get('status')=='success':
                continue
            portal.archive.context = dict(phase='agreements', academicYear=year, studyField=None, institution=partner['name'])
            try:
                data, ref = retry(portal, lambda: portal.post({portal.cause_field:partner['agreementToken'], 'target':'agree','is_load_data':1,'is_show_counter':1}))
                if not isinstance(data.get('data'),list):
                    raise ValueError('Missing agreement rows')
                ids=[]
                for ordinal, agreement_row in enumerate(data['data']):
                    url=action(agreement_row[2],'partnerTableDetails')
                    if not url:
                        raise ValueError('Missing agreement detail URL')
                    html, detail_ref = retry(portal, lambda: fetch_html(portal,urljoin(PORTAL_POST,url),state))
                    parsed=parse_detail_html(html)
                    if not parsed['fields'].get('Partner institution'):
                        raise ValueError('Agreement HTML has no partner; session may have expired')
                    # Preserve repeated rows as separate source records, even if the text is identical.
                    record_id=digest([year,partner['id'],ordinal,parsed['fields']])
                    state['agreements'][record_id]=dict(id=record_id, institutionId=partner['id'], academicYear=year,
                        ordinal=ordinal, parsed=parsed, sourceRef=detail_ref, rawRow=agreement_row, collectedAt=now())
                    ids.append(record_id)
                issue = None
                if partner['agreementCount'] != len(data['data']):
                    issue=dict(academicYear=year,institution=partner['name'],reportedCount=partner['agreementCount'],availableRows=len(data['data']),sourceRef=ref)
                    state['sourceDiscrepancies'][item_key]=issue
                state['agreementLists'][item_key]=dict(status='success',institutionId=partner['id'],academicYear=year,
                    reportedCount=partner['agreementCount'],agreementIds=ids,sourceRef=ref,sourceDiscrepancy=issue,collectedAt=now())
            except Exception as error:
                state['agreementLists'][item_key]=dict(status='error',institutionId=partner['id'],academicYear=year,error=str(error))
            save(run,state)
            if index%10==0:
                print(f'Agreement lists {year}: {index}/{len(rows)}; {len(state["agreements"])} detail records',flush=True)


def collect_filter_tables(portal,run,state,years,fields):
    for year in years:
        for index,field in enumerate(fields,1):
            query_key=year+'|'+field
            if state['searches'].get(query_key,{}).get('status')=='success':
                continue
            try:
                rows=retry(portal,lambda:portal.search(year,field),refresh=portal.open)
                state['searches'][query_key]=dict(status='success',academicYear=year,studyField=field,
                    sourceRefs=list(portal.table_refs),rows=rows,collectedAt=now(),
                    agreementMappingStatus='not-collected',
                    institutions=[dict(institutionId=parse_partner(r)['id'],reportedAgreementCount=parse_partner(r)['agreementCount']) for r in rows])
            except Exception as error:
                state['searches'][query_key]=dict(status='error',academicYear=year,studyField=field,error=str(error))
            save(run,state)
            print(f'Field searches {year}: {index}/{len(fields)} — {field}',flush=True)


def collect_documents(portal,run,state):
    # Follow public portal upload links only. Off-site links and KUnet references
    # stay in the inventory; this is not a recursive crawl of unrelated websites.
    documents=[item for item in state['links'].values() if urlparse(item['url']).hostname=='www.service4mobility.com' and '/GetUploadFileServlet' in item['url']]
    for index,item in enumerate(documents,1):
        if item['status']=='downloaded':continue
        portal.archive.context=dict(phase='document',url=item['url'])
        try:
            time.sleep(portal.delay)
            response=portal.page.request.get(item['url'],timeout=60000)
            body=response.body()
            ref=portal.archive.save(body,url=item['url'],status=response.status,kind='linked-document')
            content_type=response.headers.get('content-type','')
            if not response.ok or ('text/html' in content_type and b'<html' in body[:1000].lower()):
                raise ValueError(f'Not a downloadable file: HTTP {response.status}, {content_type}')
            item.update(status='downloaded',sourceRef=ref,contentType=content_type,size=len(body),collectedAt=now())
        except Exception as error:
            item.update(status='error',error=str(error))
        save(run,state)
        if index%25==0:print(f'Portal documents {index}/{len(documents)}',flush=True)


def report(run,state):
    years,fields=state['academicYears'],state['studyFields']
    expected_lists=sum(len(v['rows']) for v in state['baselineTables'].values())
    errors={category:[dict(key=k,error=v.get('error')) for k,v in state[category].items() if v.get('status')=='error'] for category in ['institutions','agreementLists','searches','links']}
    result=dict(at=now(),runId=run.name,
        institutions=dict(expected=state.get('overviewExpected'),success=sum(v.get('status')=='success' for v in state['institutions'].values())),
        agreementLists=dict(expected=expected_lists,success=sum(v.get('status')=='success' for v in state['agreementLists'].values())),
        agreementDetailRecords=len(state['agreements']),
        filterSearches=dict(expected=len(years)*len(fields),success=sum(v.get('status')=='success' for v in state['searches'].values())),
        downloadedDocuments=sum(v['status']=='downloaded' for v in state['links'].values()),
        linksPreserved=len(state['links']),sourceDiscrepancies=list(state['sourceDiscrepancies'].values()),errors=errors,
        exactFieldAgreementMapping='not-collected',
        coverageNote='All available institution and baseline agreement source pages, all year/field institution tables, and referenced public portal uploads. External sites and report subpages are linked, not recursively crawled. No source discrepancies are corrected by guessing.',
        published=False)
    result['status']='complete-source-snapshot' if state.get('overviewComplete') and len(state['baselineTables'])==len(years) and result['agreementLists']['success']==expected_lists and result['filterSearches']['success']==result['filterSearches']['expected'] and not any(errors.values()) else 'incomplete'
    atomic_json(run/'source-report.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--delay',type=float,default=.5)
    args=parser.parse_args()
    if Path(args.run).name!=args.run:parser.error('Invalid run name')
    run=ROOT/'data'/'portal-runs'/args.run
    state=load(run/'source-state.json',dict(schemaVersion=1,runId=run.name,startedAt=now(),institutions={},
        agreements={},agreementLists={},baselineTables={},searches={},links={},sourceDiscrepancies={}))
    # Never resume state from another archive run. It may contain old session
    # tokens and rows that no longer match the verified vocabulary.
    if state.get('runId') != run.name:
        state=dict(schemaVersion=1,runId=run.name,startedAt=now(),institutions={},agreements={},
            agreementLists={},baselineTables={},searches={},links={},sourceDiscrepancies={})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        portal=Portal(browser,Archive(run),delay=max(.25,args.delay))
        try:
            years=sorted(set(o['label'] for o in portal.options['Academic year']))
            fields=sorted(set(o['label'] for o in portal.options['Study field']))
            if state.get('academicYears') and (state['academicYears']!=years or state['studyFields']!=fields):
                raise ValueError('Vocabulary changed; use a new run')
            state.update(academicYears=years,studyFields=fields)
            atomic_json(ROOT/'data'/'portal_catalog.json',dict(observedAt=now(),academicYears=years,studyFields=fields))
            save(run,state)
            collect_overview(portal,run,state,years[0])
            collect_baselines(portal,run,state,years)
            collect_filter_tables(portal,run,state,years,fields)
            collect_documents(portal,run,state)
        finally:
            save(run,state)
            summary=report(run,state)
            portal.close()
            browser.close()
            print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
