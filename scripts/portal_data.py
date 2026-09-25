"""Lossless archive and strict parsers for KU's public Mobility-Online portal."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from parse_agreement_details import parse_detail_html

PORTAL_URL = 'https://www.service4mobility.com/europe/PortalServlet?identifier=KOBENHA01'
PORTAL_POST = 'https://www.service4mobility.com/europe/PortalServlet'
ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


# Display names diverge from the portal's raw "Country" / "Host country" values.
COUNTRY_DISPLAY_NAMES = {
    'China (Hong Kong)': 'Hong Kong (China)',
    'China (Taiwan)': 'Taiwan',
}


def display_country(value):
    if value is None:
        return None
    return COUNTRY_DISPLAY_NAMES.get(value.strip(), value) if isinstance(value, str) else value


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


class Archive:
    """Immutable, content-addressed response bytes; append-only provenance manifest."""
    def __init__(self, directory):
        self.directory = Path(directory)
        (self.directory / 'bodies').mkdir(parents=True, exist_ok=True)
        self.context = {}

    def save(self, body: bytes, *, url, method='GET', post_data=None, status=200,
             kind='response', context=None):
        sha = hashlib.sha256(body).hexdigest()
        rel = f'bodies/{sha}.gz'
        path = self.directory / rel
        if not path.exists():
            with path.open('xb') as f:
                f.write(gzip.compress(body, mtime=0))
        item = dict(at=now(), url=url, method=method, postData=post_data,
                    status=status, kind=kind, sha256=sha, body=rel,
                    context=dict(self.context if context is None else context))
        with (self.directory / 'manifest.jsonl').open('a') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        return rel


def clean(html):
    return BeautifulSoup(str(html), 'html.parser').get_text(' ', strip=True)


def action(html, target):
    match = re.search(r"openFancy\(['\"]" + re.escape(target) + r"['\"],\s*['\"]([^'\"]+)", html)
    return match.group(1) if match else None


def parse_partner(row):
    if not isinstance(row, list) or len(row) < 10:
        raise ValueError('Unexpected partner table row')
    name, continent, country, city = [clean(v) for v in row[1:5]]
    country = display_country(country)
    if not name or not country:
        raise ValueError('Partner without name/country')
    def count(index):
        value = clean(row[index])
        if value in ('', 'N/A'):
            return 0
        if not value.isdigit():
            raise ValueError(f'Unexpected count: {value}')
        return int(value)
    detail = BeautifulSoup(row[0], 'html.parser').find(attrs={'data-rel': True})
    identity = [normalize(v) for v in (name, country, city)]
    report_count = count(8)
    report_token = action(row[8], 'quest')
    if report_count and not report_token:
        raise ValueError('Positive report count without a report action')
    return dict(id='inst-' + digest(identity), name=name, country=country, city=city,
                continent=continent, agreementCount=count(5), cooperationCount=count(6),
                multilateralCount=count(7), reportCount=report_count, eventCount=count(9),
                detailUrl=urljoin(PORTAL_POST, detail['data-rel']) if detail else None,
                agreementToken=action(row[5], 'agree'), reportToken=report_token)


def validate_table(data):
    if not isinstance(data, dict) or not isinstance(data.get('aaData'), list):
        raise ValueError('Missing aaData: not a successful table response')
    total = int(data['iTotalDisplayRecords'])
    if total < 0:
        raise ValueError('Negative table count')
    return data['aaData'], total


def collect_pages(fetch, page_size=100):
    """A reported nonempty result with no rows is an error, never a zero match."""
    rows, total, seen = [], None, set()
    while total is None or len(rows) < total:
        batch, reported = validate_table(fetch(len(rows), page_size))
        if total is not None and total != reported:
            raise ValueError('Result count changed during pagination')
        total = reported
        if not batch and len(rows) < total:
            raise ValueError('Empty page before end of results (session or required field error)')
        for row in batch:
            identity = parse_partner(row)['id']
            if identity in seen:
                raise ValueError(f'Duplicate/ambiguous institution: {identity}')
            seen.add(identity)
        rows.extend(batch)
        if len(rows) > total:
            raise ValueError('More rows than reported')
    return rows


def agreement(html, institution_id):
    parsed = parse_detail_html(html)
    fields = parsed['fields']
    if not fields.get('Partner institution') or not fields.get('Academic year'):
        raise ValueError('Missing agreement fields; possible expired session')
    if fields.get('Type of person') != 'Student' or fields.get('Type of application') != 'Outgoing':
        raise ValueError('Agreement is not outgoing student mobility')
    host_country = display_country(fields.get('Host country', ''))
    # Keep the raw fields intact for provenance, but expose the display name.
    if 'Host country' in fields:
        fields = {**fields, 'Host country': host_country}
    return dict(id='agree-' + digest([institution_id, fields]), institutionId=institution_id,
                partner=fields['Partner institution'], hostCountry=host_country,
                details=fields, portalUrl=PORTAL_URL, detailToken=None)


def partner_details(html):
    # Preserve every field, including fields the current UI does not yet display.
    soup = BeautifulSoup(html, 'html.parser')
    fields = {}
    for row in soup.select('div.form-group.row'):
        label, value = row.find('label'), row.select_one('.form-control-plaintext')
        if label and value:
            fields.setdefault(label.get_text(' ', strip=True), []).append(value.get_text('\n', strip=True))
    detail_table = soup.select_one('table.table-detail')
    if detail_table:
        labels = [clean(cell) for cell in detail_table.select('thead th')]
        values = [clean(cell) for cell in detail_table.select('tbody td')]
        if len(labels) != len(values):
            raise ValueError('Unexpected partner detail table layout')
        for label, value in zip(labels, values):
            fields.setdefault(label, []).append(value)
    if 'Name of institution' not in fields:
        raise ValueError('Missing partner details; possible expired session')
    def get(key):
        return '\n'.join(fields.get(key, [])) or None
    links = [dict(label=a.get_text(' ', strip=True) or a['href'], url=urljoin(PORTAL_POST, a['href']))
             for a in soup.select('a[href]')]
    return dict(name=get('Name of institution'), code=get('Institution code'),
                additionalDescription=get('Additional description'), country=display_country(get('Country')),
                description=get('Description'), ectsConverter=get('ECTS converter'),
                semesterDates=get('Semester dates'), academicCalendar=get('Academic calendar'),
                facultyContact=get('Faculty information (e-mail contact)'),
                housingContact=get('Housing (e-mail contact)'), comment=get('Comment'),
                documents=links, fields=fields)


def report_list(data, partner):
    """Validate the observed quest popup without treating its link as an ID."""
    if not isinstance(data, dict) or not isinstance(data.get('data'), list):
        raise ValueError('Report popup has no data rows')
    columns = [clean(value) for value in data.get('columns', [])]
    required = ['Home institution', 'Partner institution', 'Host country',
                'Study field', 'Academic year']
    if columns[:5] != required:
        raise ValueError(f'Unexpected report popup columns: {columns}')
    if len(data['data']) != partner['reportCount']:
        raise ValueError(f"{partner['name']}: table reports {partner['reportCount']} "
                         f"questionnaires, popup contains {len(data['data'])}")
    output = []
    for row in data['data']:
        if not isinstance(row, list) or len(row) < 6:
            raise ValueError('Unexpected report popup row')
        fields = {label: clean(value) for label, value in zip(columns[:5], row[:5])}
        if normalize(fields['Partner institution']) != normalize(partner['name']):
            raise ValueError('Report popup row belongs to another institution')
        match = re.search(r"window\.open\(['\"]([^'\"]+)", row[5])
        if not match or not match.group(1).startswith('/europe/DispQuestionServlet?'):
            raise ValueError('Missing public report detail action')
        output.append(dict(fields=fields, detailUrl=urljoin(PORTAL_POST, match.group(1))))
    return output


def report_detail(html, institution_id, metadata, source_ref):
    """Parse the observed read-only DispQuestionServlet form, preserving all prompts."""
    soup = BeautifulSoup(html, 'html.parser')
    form = soup.select_one('form#inputForm')
    if not form or not form.select_one('input[name="fromPortal"][value="1"]'):
        raise ValueError('Not a public questionnaire detail page')
    def hidden(name):
        field = form.select_one(f'input[name="{name}"]')
        return field.get('value') if field else None
    questions = []
    section = None
    for element in form.select('.bt-collapsible-card-header h5, .bt-input-wrapper'):
        if element.name == 'h5':
            section = element.get_text(' ', strip=True)
            continue
        label = element.select_one('.bt-input-label-wrapper > label, .bt-input-label-wrapper > legend')
        if not label:
            raise ValueError('Question without a label')
        question = label.get_text(' ', strip=True)
        if not question:
            raise ValueError('Empty question label')
        answer = None
        selected = element.select('input[type="radio"]:checked, input[type="checkbox"]:checked')
        if selected:
            values = []
            for choice in selected:
                choice_label = element.select_one(f'label[for="{choice.get("id", "")}"]')
                values.append(choice_label.get_text(' ', strip=True) if choice_label else choice.get('value', ''))
            answer = '\n'.join(values)
        else:
            plain = element.select_one('[id^="plain_text_"]')
            if plain:
                answer = plain.get_text('\n', strip=True) or None
            else:
                value = element.select_one('input.bt-input[readonly], textarea[readonly]')
                if value:
                    answer = (value.get('value') if value.name == 'input'
                              else value.get_text('\n', strip=True)) or None
        links = [urljoin(PORTAL_POST, link['href']) for link in element.select('a[href]')]
        field = element.select_one('[name^="zu_q_set_id_"]')
        questions.append(dict(ordinal=len(questions)+1, section=section,
                              question=question, normalizedQuestion=normalize(question.rstrip(' *')),
                              answer=answer, links=links,
                              sourceField=(field.get('name', '').removesuffix('--view')
                                           if field else label.get('for'))))
    if not questions:
        raise ValueError('Questionnaire has no question/answer fields')
    source_key = [hidden('bew_id'), hidden('q_set_id')]
    raw_sha = hashlib.sha256(html.encode('utf-8') if isinstance(html, str) else html).hexdigest()
    identity = [institution_id, *source_key] if all(source_key) else [
        institution_id, metadata.get('Academic year'), metadata.get('Study field'),
        [(q['question'], q['answer']) for q in questions]]
    content_sha = hashlib.sha256(json.dumps(
        [metadata, [(q['section'], q['question'], q['answer'], q['links']) for q in questions]],
        ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return dict(id='report-' + digest(identity), institutionId=institution_id,
                sourceRef=source_ref, rawSha256=raw_sha, contentSha256=content_sha,
                questionnaireType=soup.select_one('h2').get_text(' ', strip=True) if soup.select_one('h2') else None,
                academicYear=metadata.get('Academic year'), studyField=metadata.get('Study field'),
                language=hidden('sprache'), sourceFields=metadata,
                questions=questions)
