#!/usr/bin/env python3
"""Archive a small public questionnaire sample before designing bulk collection."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from portal_client import Portal
from portal_data import (Archive, PORTAL_POST, PORTAL_URL, ROOT, atomic_json,
                         now, parse_partner, report_detail, report_list)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, help='Disposable investigation run name')
    parser.add_argument('--samples', type=int, default=3)
    args = parser.parse_args()
    if args.run != Path(args.run).name or args.samples < 1:
        parser.error('Use a simple run name and at least one sample')
    run = ROOT / 'data' / 'portal-investigation' / args.run
    archive = Archive(run)
    evidence = dict(at=now(), sourceUrl=PORTAL_URL, status='investigating', samples=[])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        portal = Portal(browser, archive, delay=0.5, concurrency=1)
        try:
            # The initial server-rendered rows are independent of the AJAX table.
            # Capture both so a broken reload cannot masquerade as zero reports.
            response = portal.page.goto(PORTAL_URL, wait_until='domcontentloaded')
            html = response.body()
            page_ref = archive.save(html, url=PORTAL_URL, status=response.status,
                                    kind='initial-report-page')
            soup = BeautifulSoup(html, 'html.parser')
            rows = []
            for tr in soup.select('#result_table tbody tr'):
                cells = [str(td) for td in tr.select('td')]
                if len(cells) >= 10:
                    rows.append(parse_partner(cells))
            candidates = [partner for partner in rows if partner['reportCount']]
            evidence.update(initialPageRef=page_ref, initialRows=len(rows),
                            initialReportCount=sum(p['reportCount'] for p in rows))
            if not candidates:
                raise ValueError('Initial page has no report actions')
            portal.resolve_cause_field()
            portal.params = portal.live_params()
            for partner in candidates[:args.samples]:
                archive.context = {'institution': partner['name'],
                                   'institutionId': partner['id'], 'phase': 'report-list'}
                result, ref = portal.post({portal.cause_field: partner['reportToken'],
                                           'target': 'quest', 'is_load_data': 1,
                                           'is_show_counter': 1})
                report_list(result, partner)
                sample = dict(institutionId=partner['id'],
                    institution=partner['name'], reportedCount=partner['reportCount'],
                    listRef=ref, responseKeys=sorted(result) if isinstance(result, dict) else None,
                    dataRows=len(result.get('data', [])) if isinstance(result, dict)
                             and isinstance(result.get('data'), list) else None)
                if isinstance(result, dict) and result.get('data'):
                    sample['details'] = []
                    observed_years = set()
                    for row in result['data']:
                        if row[4] in observed_years:
                            continue
                        observed_years.add(row[4])
                        links = [re.search(r"window\.open\(['\"]([^'\"]+)", str(cell))
                                 for cell in row]
                        detail_link = next((match.group(1) for match in links if match), None)
                        if not detail_link:
                            continue
                        detail_url = urljoin(PORTAL_POST, detail_link)
                        archive.context = {'institution': partner['name'],
                                           'institutionId': partner['id'],
                                           'phase': 'report-detail'}
                        detail = portal.page.request.get(detail_url, timeout=60000)
                        detail_body = detail.body()
                        detail_ref = archive.save(detail_body, url=detail_url,
                            status=detail.status, kind='report-detail',
                            context=archive.context | {'contentType':
                                detail.headers.get('content-type')})
                        if not detail.ok:
                            raise ValueError(f'Public detail returned HTTP {detail.status}')
                        metadata = dict(zip(result['columns'][:5], row[:5]))
                        parsed = report_detail(detail_body.decode('utf-8'),
                                               partner['id'], metadata, detail_ref)
                        sample['details'].append(dict(academicYear=row[4],
                            detailRef=detail_ref, detailStatus=detail.status,
                            detailContentType=detail.headers.get('content-type'),
                            questionnaireType=parsed['questionnaireType'],
                            questionCount=len(parsed['questions'])))
                evidence['samples'].append(sample)
                atomic_json(run / 'inspection.json', evidence)
            evidence['status'] = 'lists-archived'
        except Exception as error:
            evidence.update(status='blocked', error=str(error))
            raise
        finally:
            atomic_json(run / 'inspection.json', evidence)
            portal.close()
            browser.close()
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
