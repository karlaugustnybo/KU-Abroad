"""Browser-backed public searches. No saved form hashes or session-token identities."""
from __future__ import annotations

import json
import re
import time
from urllib.parse import urlencode, urljoin

from portal_data import (Archive, PORTAL_URL, PORTAL_POST, now, action,
                         collect_pages, parse_partner, agreement, partner_details,
                         report_list, report_detail, digest)


class Portal:
    def __init__(self, browser, archive: Archive, delay=0.5, concurrency=6):
        self.context = browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)
        self.archive, self.delay = archive, delay
        self.concurrency = max(1, concurrency)
        self.pending = []
        self.page.on('response', lambda response: self.pending.append(response))
        self.open()

    def drain(self):
        # Read bodies after the browser is idle, not recursively inside response callbacks.
        pending, self.pending = self.pending, []
        for response in pending:
            if 'service4mobility.com/europe/' not in response.url:
                continue
            request = response.request
            if request.headers.get('x-codex-archive') == 'explicit':
                continue
            try:
                body = response.body()
            except Exception as error:
                self.archive.save(b'playwright-error: ' + str(error).encode(),
                                  url=response.url, status=response.status, kind='unavailable-response',
                                  method=request.method, post_data=request.post_data)
                continue
            self.archive.save(body, url=response.url, status=response.status,
                              method=request.method, post_data=request.post_data)

    def idle(self):
        self.page.wait_for_function('window.jQuery && jQuery.active === 0')
        try:
            self.drain()
        except Exception as error:
            print(f'Archive drain error (state preserved): {error}', flush=True)

    def open(self):
        self.page.goto(PORTAL_URL, wait_until='domcontentloaded', timeout=90000)
        self.idle()
        self.archive.save(self.page.content().encode(), url=PORTAL_URL, kind='dom')
        self.options = self.page.evaluate('''() => Object.fromEntries([...document.querySelectorAll('#search_form select')].map(s=>[document.querySelector('label[for="'+s.id+'"]')?.innerText, [...s.options].map(o=>({label:o.text,value:o.value}))]))''')
        self.page.locator('button[value="Agreements"]').click()
        self.idle()

    def search(self, year, field=None):
        self.archive.context = dict(academicYear=year, studyField=field, application='Outgoing', person='Students')
        # Reset every optional filter, then apply the entire query in one reload.
        # Selecting all study fields is the portal-supported unfiltered baseline:
        # an empty study field is invalid (mandatory) and returns misleading totals.
        self.page.evaluate('''({year,field}) => {
          for(const s of document.querySelectorAll('#search_form select')) {
            const label=document.querySelector('label[for="'+s.id+'"]')?.innerText;
            const values=[...s.options].filter(o=>label==='Academic year'?o.text===year:label==='Study field'?(!field||o.text===field):false).map(o=>o.value);
            if((label==='Academic year'||label==='Study field')&&!values.length) throw Error('Missing query option: '+label);
            jQuery(s).selectpicker('val',values);
          }
          for(const label of ['Outgoing','Students']) {
            const radio=[...document.querySelectorAll('#search_form input[type=radio]')].find(r=>r.closest('label')?.textContent.trim()===label || document.querySelector('label[for="'+r.id+'"]')?.textContent.trim()===label);
            if(!radio) throw Error('Missing radio '+label);
            radio.checked=true;
          }
          document.querySelector('#keyword_field').value='';
          reloadFields();
        }''', dict(year=year, field=field))
        self.idle()
        selected = self.page.evaluate('''()=>Object.fromEntries([...document.querySelectorAll('#search_form select')].map(s=>[document.querySelector('label[for="'+s.id+'"]')?.innerText,[...s.selectedOptions].map(o=>o.text)]))''')
        if selected.get('Academic year') != [year] or (field and selected.get('Study field') != [field] and set(selected.get('Study field', [])) != {field}):
            raise ValueError('Portal did not retain selected year/field')
        self.archive.save(json.dumps(selected).encode(), url=PORTAL_URL, kind='selected-filters')
        self.params = self.page.evaluate('''()=>{const disabled=jQuery('#search_form :input:disabled').removeAttr('disabled');const str=jQuery('#search_form').find(':not(.none_request)').serialize();disabled.attr('disabled','disabled');return str;}''')
        self.resolve_cause_field()
        return self.table()

    def resolve_cause_field(self):
        fn = self.page.evaluate('openFancy.toString()')
        match = re.search(r'&(cpif_[a-z0-9_]+)=["\']\s*\+\s*cause', fn)
        if not match:
            raise ValueError('Could not resolve live popup parameter')
        self.cause_field = match.group(1)
        return self.cause_field

    def filtered_params(self, year, field=None):
        params = self.page.evaluate('''({year,field}) => {
          for(const s of document.querySelectorAll('#search_form select')) {
            const label=document.querySelector('label[for="'+s.id+'"]')?.innerText;
            const values=[...s.options].filter(o=>label==='Academic year'?o.text===year:label==='Study field'?(field&&o.text===field):false).map(o=>o.value);
            if((label==='Academic year'||label==='Study field')&&!values.length) throw Error('Missing query option: '+label);
            jQuery(s).selectpicker('val',values);
          }
          const disabled=jQuery('#search_form :input:disabled').removeAttr('disabled');
          const str=jQuery('#search_form').find(':not(.none_request)').serialize();
          disabled.attr('disabled','disabled');
          return str;
        }''', dict(year=year,field=field))
        if not params:
            raise ValueError('Missing filtered form parameters')
        return params

    def available_study_fields(self, year):
        """Return study fields the portal offers after selecting one year.

        The two selects are dependent. A field can exist in the initial catalog
        but disappear when a later academic year is selected. Start from a fresh
        form so the result cannot inherit the preceding query's narrowed options.
        """
        self.open()
        self.archive.context = dict(academicYear=year, studyField=None,
                                    application='Outgoing', person='Students')
        self.page.evaluate('''({year}) => {
          for(const s of document.querySelectorAll('#search_form select')) {
            const label=document.querySelector('label[for="'+s.id+'"]')?.innerText;
            const values=[...s.options].filter(o=>label==='Academic year'?o.text===year:label==='Study field'?true:false).map(o=>o.value);
            if(label==='Academic year'&&!values.length) throw Error('Missing query option: '+label);
            jQuery(s).selectpicker('val',values);
          }
          for(const label of ['Outgoing','Students']) {
            const radio=[...document.querySelectorAll('#search_form input[type=radio]')].find(r=>r.closest('label')?.textContent.trim()===label || document.querySelector('label[for="'+r.id+'"]')?.textContent.trim()===label);
            if(!radio) throw Error('Missing radio '+label);
            radio.checked=true;
          }
          document.querySelector('#keyword_field').value='';
          reloadFields();
        }''', dict(year=year))
        self.idle()
        evidence = self.page.evaluate('''()=>Object.fromEntries([...document.querySelectorAll('#search_form select')].map(s=>[document.querySelector('label[for="'+s.id+'"]')?.innerText,{selected:[...s.selectedOptions].map(o=>o.text),options:[...s.options].map(o=>o.text)}]))''')
        if evidence.get('Academic year', {}).get('selected') != [year]:
            raise ValueError('Portal did not retain selected academic year')
        fields = evidence.get('Study field', {}).get('options')
        if fields is None:
            raise ValueError('Portal did not expose study-field options')
        ref = self.archive.save(json.dumps(evidence).encode(), url=PORTAL_URL,
                                kind='year-study-field-options')
        return fields, ref

    def live_params(self):
        params = self.page.evaluate('''()=>{const disabled=jQuery('#search_form :input:disabled').removeAttr('disabled');const str=jQuery('#search_form').find(':not(.none_request)').serialize();disabled.attr('disabled','disabled');return str;}''')
        if not params:
            raise ValueError('Missing live form parameters')
        return params

    def request(self, url, *, params=None):
        if self.delay:
            time.sleep(self.delay)
        if params is None:
            response = self.page.request.get(
                url, headers={'X-Codex-Archive':'explicit'}, timeout=60000)
        else:
            response = self.page.request.post(url, data=params,
                headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                         'X-Requested-With':'XMLHttpRequest',
                         'X-Codex-Archive':'explicit'}, timeout=60000)
        body = response.body()
        ref = self.archive.save(body, url=url, method='POST' if params is not None else 'GET',
                                post_data=params, status=response.status)
        if not response.ok:
            raise ValueError(f'Portal HTTP {response.status}')
        return body.decode('utf-8'), ref

    def request_many(self, jobs):
        """Fetch text responses concurrently in the authenticated page session."""
        if not jobs:
            return {}
        if self.delay:
            time.sleep(self.delay)
        payload = [dict(key=job['key'], url=job['url'], method=job.get('method','GET'),
                        body=job.get('body'), headers=job.get('headers', {}))
                   for job in jobs]
        results = self.page.evaluate('''async ({jobs, concurrency}) => {
          const output = new Array(jobs.length);
          let cursor = 0;
          async function worker() {
            while (cursor < jobs.length) {
              const index = cursor++;
              const job = jobs[index];
              for (let attempt = 0; attempt < 3; attempt++) {
                try {
                  const controller = new AbortController();
                  const timeout = setTimeout(() => controller.abort(), 60000);
                  const response = await fetch(job.url, {
                    method: job.method,
                    body: job.body || undefined,
                    headers: {...job.headers, 'X-Codex-Archive':'explicit'},
                    credentials: 'same-origin', signal: controller.signal
                  });
                  clearTimeout(timeout);
                  const body = await response.text();
                  if ((response.status === 429 || response.status >= 500) && attempt < 2) {
                    await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)));
                    continue;
                  }
                  output[index] = {key:job.key, url:response.url,
                    status:response.status, ok:response.ok, body};
                  break;
                } catch (error) {
                  if (attempt < 2) {
                    await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)));
                    continue;
                  }
                  output[index] = {key:job.key, url:job.url, status:0, ok:false,
                    error:String(error), body:''};
                }
              }
            }
          }
          await Promise.all(Array.from({length:Math.min(concurrency,jobs.length)}, worker));
          return output;
        }''', dict(jobs=payload, concurrency=self.concurrency))
        by_key = {}
        job_by_key = {job['key']:job for job in jobs}
        for result in results:
            job = job_by_key[result['key']]
            body = result['body'].encode()
            ref = self.archive.save(
                body, url=result['url'], method=job.get('method','GET'),
                post_data=job.get('body'), status=result['status'],
                context=job.get('context'))
            if not result['ok']:
                raise ValueError(
                    f"Portal HTTP {result['status']} for {result['key']}: "
                    f"{result.get('error','request failed')}"
                )
            by_key[result['key']] = (result['body'], ref)
        return by_key

    def post(self, params, *, base_params=None):
        text, ref = self.request(
            PORTAL_POST,
            params=(self.params if base_params is None else base_params)+'&'+urlencode(params))
        try:
            return json.loads(text), ref
        except json.JSONDecodeError as e:
            raise ValueError('Not JSON; possible expired portal session') from e

    def table_for_params(self, params, *, context=None):
        """Select a direct-query payload and fetch its filtered table."""
        self.params = params
        if context is not None:
            self.archive.context = context
        return self.table(base_params=params)

    def table(self, page_size=100, *, base_params=None):
        self.table_refs = []
        def fetch(start, length):
            result, ref = self.post(dict(is_reload_table=1, row_start=start, row_length=length,
                                         order_col=1, order_kind='asc', is_show_counter=1),
                                    base_params=base_params)
            self.table_refs.append(ref)
            return result
        # -1 is the portal's visible "All" page size. collect_pages still rejects truncation.
        return collect_pages(fetch, page_size=-1 if page_size == 100 else page_size)

    def verify_visible(self, rows, *, paginate=False):
        page = self.page
        page.evaluate("jQuery('#result_table').DataTable().page.len(-1).draw()")
        self.idle()
        visible = page.evaluate('''()=>[...document.querySelectorAll('#result_table tbody tr')].filter(r=>!r.querySelector('.dataTables_empty')).map(r=>({name:r.cells[1].innerText.trim(),count:Number(r.cells[5].innerText.trim())}))''')
        expected = [dict(name=parse_partner(r)['name'], count=parse_partner(r)['agreementCount']) for r in rows]
        if visible != expected:
            raise ValueError('API rows differ from rendered institution names/counts')
        if paginate:
            paged = self.table(page_size=50)
            if [parse_partner(r) | {'detailUrl':None,'agreementToken':None,'reportToken':None} for r in paged] != [parse_partner(r) | {'detailUrl':None,'agreementToken':None,'reportToken':None} for r in rows]:
                raise ValueError('Paginated rows differ from All rows')
        self.archive.save(page.content().encode(), url=PORTAL_URL, kind='verified-dom')
        return dict(at=now(), year=self.archive.context['academicYear'],
                    field=self.archive.context['studyField'], institutions=len(rows),
                    agreements=sum(p['count'] for p in expected), visibleMatches=True, pagination=paginate)

    def agreements(self, partner, *, verify_visible=False, return_data=True):
        token = partner['agreementToken']
        if partner['agreementCount'] and not token:
            raise ValueError('Positive agreement count without a detail action')
        data, ref = self.post({self.cause_field:token, 'target':'agree', 'is_load_data':1, 'is_show_counter':1})
        if not isinstance(data.get('data'), list):
            raise ValueError('Agreement popup is not a valid result')
        if verify_visible:
            self.page.evaluate('token=>openFancy("agree",token)', token)
            self.idle()
            names = self.page.evaluate("jQuery('#partner_result_table').DataTable().rows().data().toArray().map(r=>r.slice(0,2))")
            if names != [row[:2] for row in data['data']]:
                raise ValueError('Rendered agreement popup differs from API')
            self.archive.save(self.page.content().encode(), url=PORTAL_URL, kind='verified-agreement-dom')
            self.page.evaluate("jQuery('#modal_dialog').modal('hide')")
        results = []
        for row in data['data']:
            url = action(row[2], 'partnerTableDetails')
            if not url:
                raise ValueError('Missing agreement detail link')
            html, detail_ref = self.request(urljoin(PORTAL_POST, url))
            item = agreement(html, partner['id'])
            if self.archive.context['academicYear'] not in item['details']['Academic year']:
                raise ValueError('Agreement detail does not contain selected year')
            item['sourceRef'] = detail_ref
            results.append(item)
        if not return_data:
            return [item['id'] for item in results], ref
        if len({a['id'] for a in results}) != len(results):
            raise ValueError('Indistinguishable duplicate agreements; requires review')
        return results, ref

    def agreement_list(self, partner, *, verify_visible=False):
        token = partner['agreementToken']
        if partner['agreementCount'] and not token:
            raise ValueError('Positive agreement count without a detail action')
        data, ref = self.post({self.cause_field:token, 'target':'agree', 'is_load_data':1, 'is_show_counter':1})
        if not isinstance(data.get('data'), list):
            raise ValueError('Agreement popup is not a valid result')
        if verify_visible:
            self.page.evaluate('token=>openFancy("agree",token)', token)
            self.idle()
            names = self.page.evaluate("jQuery('#partner_result_table').DataTable().rows().data().toArray().map(r=>r.slice(0,2))")
            if names != [row[:2] for row in data['data']]:
                raise ValueError('Rendered agreement popup differs from API')
            self.archive.save(self.page.content().encode(), url=PORTAL_URL, kind='verified-agreement-dom')
            self.page.evaluate("jQuery('#modal_dialog').modal('hide')")
        if len(data['data']) != partner['agreementCount']:
            raise ValueError(f"{partner['name']}: table reports {partner['agreementCount']} agreements, popup contains {len(data['data'])}")
        return [agreement_id(row, partner['id']) for row in data['data']], ref

    def agreement_details(self, partner):
        return self.agreement_details_many([partner])[partner['id']]

    def agreement_details_many(self, partners):
        """Fetch agreement lists and their detail pages in bounded concurrent batches."""
        if not partners:
            return {}
        context = dict(self.archive.context)
        headers = {'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                   'X-Requested-With':'XMLHttpRequest'}
        list_jobs = []
        partner_by_id = {}
        for partner in partners:
            token = partner['agreementToken']
            if partner['agreementCount'] and not token:
                raise ValueError('Positive agreement count without a detail action')
            partner_by_id[partner['id']] = partner
            body = self.params+'&'+urlencode({self.cause_field:token, 'target':'agree',
                'is_load_data':1, 'is_show_counter':1})
            list_jobs.append(dict(key=partner['id'], url=PORTAL_POST, method='POST',
                                  body=body, headers=headers,
                                  context=context | {'institution':partner['name']}))
        list_responses = self.request_many(list_jobs)
        lists = {}
        detail_jobs = []
        for institution_id, (text, source_ref) in list_responses.items():
            try:
                data = json.loads(text)
            except json.JSONDecodeError as error:
                raise ValueError('Not JSON; possible expired portal session') from error
            if not isinstance(data.get('data'), list):
                raise ValueError('Agreement popup is not a valid result')
            lists[institution_id] = (data['data'], source_ref)
            partner = partner_by_id[institution_id]
            for ordinal, row in enumerate(data['data']):
                url = action(row[2], 'partnerTableDetails')
                if not url:
                    raise ValueError('Missing agreement detail link')
                detail_jobs.append(dict(
                    key=f'{institution_id}:{ordinal}', url=urljoin(PORTAL_POST, url),
                    context=context | {'institution':partner['name']}))
        detail_responses = self.request_many(detail_jobs)
        output = {}
        for institution_id, (rows, source_ref) in lists.items():
            partner = partner_by_id[institution_id]
            results = []
            for ordinal, row in enumerate(rows):
                html, detail_ref = detail_responses[f'{institution_id}:{ordinal}']
                item = agreement(html, institution_id)
                if context['academicYear'] not in item['details']['Academic year']:
                    raise ValueError('Agreement detail does not contain selected year')
                item['sourceRef'] = detail_ref
                detail_token = action(row[2], 'partnerTableDetails')
                if detail_token:
                    item['detailTokenBase'] = detail_token.split('_sep_', 1)[0]
                results.append(item)
            if len({item['id'] for item in results}) != len(results):
                raise ValueError('Indistinguishable duplicate agreements; requires review')
            if len(results) != partner['agreementCount']:
                error = (f"{partner['name']}: table reports {partner['agreementCount']} "
                         f"agreements, popup contains {len(rows)} (source discrepancy)")
                if abs(len(results) - partner['agreementCount']) == 1:
                    results.append(dict(sourceDiscrepancy=error, details={}, ids=[]))
                else:
                    raise ValueError(error)
            output[institution_id] = (results, source_ref)
        return output

    def reports(self, partner):
        """Fetch one institution's public quest popup and every answer page."""
        if partner['reportCount'] == 0:
            return [], None
        token = partner.get('reportToken')
        if not token:
            raise ValueError('Positive report count without a report action')
        self.archive.context = {'institution': partner['name'],
                                'institutionId': partner['id'], 'phase': 'report-list'}
        data, list_ref = self.post({self.cause_field: token, 'target': 'quest',
                                    'is_load_data': 1, 'is_show_counter': 1})
        listing = report_list(data, partner)
        jobs = [dict(key=str(index), url=item['detailUrl'],
                     context={'institution': partner['name'],
                              'institutionId': partner['id'], 'phase': 'report-detail'})
                for index, item in enumerate(listing)]
        responses = self.request_many(jobs)
        reports = []
        for index, item in enumerate(listing):
            html, ref = responses[str(index)]
            parsed = report_detail(html, partner['id'], item['fields'], ref)
            reports.append(parsed)
        ids = [item['id'] for item in reports]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{partner['name']}: duplicate questionnaire identities")
        return reports, list_ref

    def reports_many(self, partners):
        """Batch independent popup and detail requests in the same live session."""
        if not partners:
            return {}
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                   'X-Requested-With': 'XMLHttpRequest'}
        list_jobs = []
        by_id = {partner['id']: partner for partner in partners}
        result = {partner['id']: ([], None) for partner in partners
                  if partner['reportCount'] == 0}
        for partner in partners:
            if not partner['reportCount']:
                continue
            token = partner.get('reportToken')
            if not token:
                raise ValueError('Positive report count without a report action')
            body = self.params + '&' + urlencode({self.cause_field: token,
                'target': 'quest', 'is_load_data': 1, 'is_show_counter': 1})
            list_jobs.append(dict(key=partner['id'], url=PORTAL_POST,
                method='POST', body=body, headers=headers,
                context={'institution': partner['name'],
                         'institutionId': partner['id'], 'phase': 'report-list'}))
        lists = self.request_many(list_jobs)
        detail_jobs = []
        listing_by_id = {}
        for institution_id, (text, list_ref) in lists.items():
            partner = by_id[institution_id]
            try:
                data = json.loads(text)
            except json.JSONDecodeError as error:
                raise ValueError('Report popup is not JSON') from error
            listing = report_list(data, partner)
            listing_by_id[institution_id] = (listing, list_ref)
            for index, item in enumerate(listing):
                detail_jobs.append(dict(key=f'{institution_id}:{index}',
                    url=item['detailUrl'], context={
                        'institution': partner['name'],
                        'institutionId': institution_id, 'phase': 'report-detail'}))
        details = {}
        for start in range(0, len(detail_jobs), 50):
            details.update(self.request_many(detail_jobs[start:start+50]))
        for institution_id, (listing, list_ref) in listing_by_id.items():
            reports = []
            for index, item in enumerate(listing):
                html, ref = details[f'{institution_id}:{index}']
                reports.append(report_detail(html, institution_id,
                                             item['fields'], ref))
            if len({item['id'] for item in reports}) != len(reports):
                raise ValueError(f"{by_id[institution_id]['name']}: duplicate questionnaire identities")
            result[institution_id] = (reports, list_ref)
        return result

    def details(self, partner):
        if not partner['detailUrl']:
            raise ValueError('Missing institution detail link')
        html, ref = self.request(partner['detailUrl'])
        return partner_details(html), ref

    def details_many(self, partners):
        jobs = []
        for partner in partners:
            if not partner['detailUrl']:
                raise ValueError('Missing institution detail link')
            jobs.append(dict(key=partner['id'], url=partner['detailUrl'],
                             context=dict(self.archive.context) |
                                     {'institution':partner['name']}))
        responses = self.request_many(jobs)
        return {institution_id:(partner_details(html), ref)
                for institution_id, (html, ref) in responses.items()}

    def details_partner(self, institution_id):
        raise NotImplementedError('Partner table rows are needed to fetch agreement details')

    def close(self):
        self.drain()
        self.context.close()


def agreement_id(row, institution_id):
    identity = [row[0], row[1], action(row[2], 'partnerTableDetails')]
    return 'agree-' + digest(identity)
