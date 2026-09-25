import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from collect_reports import complete_institution
from portal_data import Archive, parse_partner, report_detail, report_list
from scripts.build_duckdb import DEFAULT_OUTPUT, SCHEMA_SQL, build_database, load_report_run


DETAIL = '''<h2>Travel report</h2><form id="inputForm">
<input name="fromPortal" value="1"><input name="bew_id" value="123">
<input name="q_set_id" value="7"><input name="sprache" value="en">
<div class="bt-collapsible-card-header"><h5>General evaluation</h5></div>
<div class="bt-input-wrapper rb-group"><fieldset>
<div class="bt-input-label-wrapper"><legend>Rate your experience *</legend></div>
<input type="radio" id="yes" name="zu_q_set_id_1--view" checked value="1">
<label for="yes">Great</label></fieldset></div>
<div class="bt-input-wrapper text-input"><div class="bt-input-label-wrapper">
<label for="zu_q_set_id_2">Additional comments</label></div>
<span id="plain_text_zu_q_set_id_2"></span></div></form>'''


class ReportsTests(unittest.TestCase):
    def test_answers_cannot_enter_tracked_database(self):
        with self.assertRaisesRegex(ValueError, 'separate reports.duckdb'):
            build_database('anything', DEFAULT_OUTPUT, 'report-run')

    def test_list_validates_count_and_institution(self):
        data = dict(columns=['Home institution', 'Partner institution', 'Host country',
                             'Study field', 'Academic year', ''], data=[
            ['KU', 'University', 'Denmark', 'Laws', '2025/2026',
             '<button onclick="window.open(\'/europe/DispQuestionServlet?match=abc\', \'_blank\')">']])
        partner = dict(name='University', reportCount=1)
        self.assertEqual(len(report_list(data, partner)), 1)
        with self.assertRaisesRegex(ValueError, 'popup contains'):
            report_list(data, partner | {'reportCount': 2})
        with self.assertRaisesRegex(ValueError, 'another institution'):
            report_list(data, partner | {'name': 'Other'})

    def test_detail_preserves_order_and_unanswered_question(self):
        metadata = {'Academic year': '2025/2026', 'Study field': 'Laws'}
        first = report_detail(DETAIL, 'inst-1', metadata, 'bodies/one.gz')
        second = report_detail(DETAIL.replace('bew_id" value="123', 'bew_id" value="456'),
                               'inst-1', metadata, 'bodies/two.gz')
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual([q['ordinal'] for q in first['questions']], [1, 2])
        self.assertEqual(first['questions'][0]['answer'], 'Great')
        self.assertIsNone(first['questions'][1]['answer'])
        self.assertEqual(first['questions'][1]['sourceField'], 'zu_q_set_id_2')
        self.assertEqual(first['academicYear'], '2025/2026')
        self.assertNotIn('123', json.dumps(first))

    def test_resume_requires_all_archived_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            archive = Archive(run)
            listing = archive.save(b'list', url='https://example.org')
            detail = archive.save(b'detail', url='https://example.org')
            digest = detail.split('/')[1].removesuffix('.gz')
            progress = dict(reportedCount=1, reportIds=['r1'], listRef=listing)
            reports = {'r1': dict(sourceRef=detail, rawSha256=digest,
                                  institutionId='inst-1', questions=[{'question':'Q'}])}
            self.assertTrue(complete_institution(run, progress, reports, 1))
            (run / detail).write_bytes(gzip.compress(b'changed'))
            self.assertFalse(complete_institution(run, progress, reports, 1))

    def test_private_duckdb_projection_keeps_question_grain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root/'data'/'report-runs'/'sample'
            archive = Archive(run)
            overview_row = ['', 'University', 'Europe', 'Denmark', 'Copenhagen',
                            '0', '0', '0', '<a onclick="openFancy(\'quest\', \'abc\')">1</a>', '0']
            institution_id = parse_partner(overview_row)['id']
            overview_ref = archive.save(json.dumps({'aaData': [overview_row]}).encode(),
                                        url='https://example.org')
            list_ref = archive.save(b'list', url='https://example.org')
            html = DETAIL.encode()
            detail_ref = archive.save(html, url='https://example.org')
            item = report_detail(DETAIL, institution_id, {'Academic year':'2025/2026'}, detail_ref)
            state = dict(runId='sample', completedAt='2026-09-24T00:00:00+00:00',
                         institutionTableRefs=[overview_ref],
                         institutions={institution_id:dict(reportedCount=1,
                             reportIds=[item['id']], listRef=list_ref)},
                         reports={item['id']:item})
            (run/'state.json').write_text(json.dumps(state))
            (run/'quality-report.json').write_text(json.dumps(dict(
                status='complete', discrepancies=[], collectedReports=1)))
            connection = duckdb.connect(':memory:')
            connection.execute(SCHEMA_SQL)
            with patch('scripts.build_duckdb.ROOT', root), \
                 patch('scripts.build_duckdb.DATA', root/'data'):
                load_report_run(connection, 'sample')
            self.assertEqual(connection.execute(
                'SELECT count(*) FROM catalog.reports').fetchone()[0], 1)
            self.assertEqual(connection.execute(
                'SELECT count(*) FROM catalog.report_institutions').fetchone()[0], 1)
            self.assertEqual(connection.execute(
                'SELECT count(*), count(answer) FROM catalog.report_answers').fetchone(),
                (2, 1))
            connection.close()


if __name__ == '__main__':
    unittest.main()
