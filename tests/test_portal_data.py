import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from portal_data import Archive, atomic_json, collect_pages, parse_partner, partner_details
from archive_portal import report
from collect_portal import (checkpoint_query, map_filtered_partner, migrate_state,
                            restore_query_checkpoints)


def row(name='University',count=1,country='Denmark',city='Copenhagen'):
    return ['<i data-rel="/detail"></i>',name,'Europe',country,city,f'<span>{count}</span>','N/A','0','0','0','']


def minimal_partner_detail(code='GB-826-1001',name='Aberystwyth University',country='United Kingdom'):
    return f'''<table class="table-detail"><thead><tr><th>Institution code</th>
               <th>Name of institution</th><th>Country</th></tr></thead>
               <tbody><tr><td>{code}</td><td>{name}</td><td>{country}</td></tr></tbody></table>'''


class PortalDataTests(unittest.TestCase):
    def test_pagination_collects_every_row(self):
        rows=[row('A'),row('B'),row('C')]
        calls=[]
        def fetch(start,length):
            calls.append(start)
            return dict(aaData=rows[start:start+length],iTotalDisplayRecords='3')
        self.assertEqual(len(collect_pages(fetch,2)),3)
        self.assertEqual(calls,[0,2])

    def test_true_empty_result(self):
        self.assertEqual(collect_pages(lambda *_:dict(aaData=[],iTotalDisplayRecords=0)),[])

    def test_missing_rows_are_not_an_empty_success(self):
        with self.assertRaisesRegex(ValueError,'Empty page'):
            collect_pages(lambda *_:dict(aaData=[],iTotalDisplayRecords=525))

    def test_expired_session_or_wrong_schema_is_not_success(self):
        with self.assertRaisesRegex(ValueError,'Missing aaData'):
            collect_pages(lambda *_:dict(error='session expired'))

    def test_ambiguous_duplicate_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate/ambiguous'):
            collect_pages(lambda *_:dict(aaData=[row(),row()],iTotalDisplayRecords=2))

    def test_same_name_other_city_is_distinct(self):
        self.assertNotEqual(parse_partner(row(city='A'))['id'],parse_partner(row(city='B'))['id'])

    def test_ids_ignore_session_tokens(self):
        first,second=row(),row()
        second[0]='<i data-rel="/different-session"></i>'
        self.assertEqual(parse_partner(first)['id'],parse_partner(second)['id'])

    def test_unexpected_counts_fail(self):
        with self.assertRaisesRegex(ValueError,'Unexpected count'):
            parse_partner(row(count='unknown'))

    def test_report_action_is_extracted_but_not_part_of_institution_id(self):
        first = row()
        first[8] = '<a onclick="openFancy(\'quest\', \'session-one\')">2</a>'
        second = row()
        second[8] = '<a onclick="openFancy(\'quest\', \'session-two\')">2</a>'
        parsed = parse_partner(first)
        self.assertEqual(parsed['reportCount'], 2)
        self.assertEqual(parsed['reportToken'], 'session-one')
        self.assertEqual(parsed['id'], parse_partner(second)['id'])

    def test_positive_report_count_requires_action(self):
        item = row()
        item[8] = '<span>2</span>'
        with self.assertRaisesRegex(ValueError, 'Positive report count'):
            parse_partner(item)

    def test_raw_bytes_are_lossless_and_versions_append(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory)
            original=b'\xff\x00 all fields, unparsed links, and unknown values'
            one=archive.save(original,url='https://example.test')
            archive.save(original,url='https://example.test',post_data='a=1&a=2')
            self.assertEqual(gzip.decompress((Path(directory)/one).read_bytes()),original)
            entries=(Path(directory)/'manifest.jsonl').read_text().splitlines()
            self.assertEqual(len(entries),2)
            self.assertEqual(json.loads(entries[1])['postData'],'a=1&a=2')
            self.assertEqual(len(list((Path(directory)/'bodies').iterdir())),1)

    def test_archive_can_record_job_specific_context(self):
        with tempfile.TemporaryDirectory() as directory:
            archive=Archive(directory)
            archive.context={'studyField':'baseline'}
            archive.save(b'body',url='https://example.test',
                         context={'studyField':'Laws','institution':'U'})
            entry=json.loads((Path(directory)/'manifest.jsonl').read_text())
            self.assertEqual(entry['context'],{'studyField':'Laws','institution':'U'})

    def test_interrupted_checkpoint_keeps_previous_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'checkpoint.json'
            atomic_json(path,{'query':{'status':'success','rows':[1,2]}})
            with patch('portal_data.os.replace',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):atomic_json(path,{'query':{'status':'error'}})
            self.assertEqual(json.loads(path.read_text())['query']['rows'],[1,2])

    def test_unknown_and_repeated_partner_fields_are_preserved(self):
        def field(label,value):
            return f'<div class="form-group row"><label>{label}</label><div class="form-control-plaintext">{value}</div></div>'
        html=field('Name of institution','U')+field('Future field','one')+field('Future field','two')
        self.assertEqual(partner_details(html)['fields']['Future field'],['one','two'])

    def test_minimal_partner_detail_table_is_valid(self):
        details=partner_details(minimal_partner_detail())
        self.assertEqual(details['name'],'Aberystwyth University')
        self.assertEqual(details['code'],'GB-826-1001')
        self.assertEqual(details['country'],'United Kingdom')

    def test_incomplete_snapshot_cannot_report_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            state=dict(academicYears=['2026/2027'],studyFields=['Laws'],institutions={},agreementLists={},searches={},links={},agreements={},sourceDiscrepancies={},baselineTables={})
            self.assertEqual(report(Path(directory),state)['status'],'incomplete')

    def test_state_migration_drops_inexact_queries_and_orphan_baselines(self):
        state={'schemaVersion':1,'completedAt':'old','agreements':{'a':{}},
               'baselineProgress':{'year|ok':{'ids':['a']},'year|bad':{'ids':['missing']}},
               'queries':{
                   'safe':{'matches':[{'method':'filtered-count-equals-baseline'}]},
                   'unsafe':{'matches':[{'method':'filtered-count-subset-reusing-baseline'}]},
               }}
        migrate_state(state)
        self.assertEqual(state['schemaVersion'],2)
        self.assertNotIn('completedAt',state)
        self.assertEqual(set(state['queries']),{'safe'})
        self.assertEqual(set(state['baselineProgress']),{'year|ok'})

    def test_query_checkpoint_round_trip_and_unsafe_filter(self):
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory)
            checkpoint_query(run,'2026|Laws',{'status':'success','matches':[]})
            checkpoint_query(run,'2026|Unsafe',{'status':'success','matches':[
                {'method':'filtered-count-subset-reusing-baseline'}]})
            state={'queries':{}}
            restore_query_checkpoints(run,state)
            self.assertEqual(set(state['queries']),{'2026|Laws'})

    def test_full_filtered_count_reuses_baseline_without_fetching(self):
        class Portal:
            def agreement_details(self, partner):
                raise AssertionError('full baseline should not fetch details')
        partner={'id':'i','name':'U','agreementCount':2}
        match=map_filtered_partner(Portal(),partner,
            {'ids':['a','b'],'sourceRef':'baseline'}, {})
        self.assertEqual(match['agreementIds'],['a','b'])
        self.assertEqual(match['method'],'filtered-count-equals-baseline')

    def test_reported_baseline_discrepancy_reuses_available_source_rows(self):
        class Portal:
            def agreement_details(self, partner):
                raise AssertionError('same reported count should reuse baseline evidence')
        partner={'id':'i','name':'U','agreementCount':2}
        match=map_filtered_partner(Portal(),partner,
            {'ids':['available'],'reportedCount':2,'sourceRef':'baseline',
             'sourceDiscrepancy':'portal reports 2 but exposes 1'}, {})
        self.assertEqual(match['agreementIds'],['available'])
        self.assertEqual(match['method'],'filtered-count-equals-discrepant-baseline')

    def test_partial_filtered_count_maps_exact_canonical_details(self):
        class Portal:
            def agreement_details(self, partner):
                return ([{'id':'b','details':{}}], 'filtered')
        agreements={}
        partner={'id':'i','name':'U','agreementCount':1}
        match=map_filtered_partner(Portal(),partner,
            {'ids':['a','b'],'sourceRef':'baseline'}, agreements)
        self.assertEqual(match['agreementIds'],['b'])
        self.assertEqual(match['method'],'filtered-details-mapped-to-baseline')
        self.assertIn('b',agreements)

    def test_partial_filtered_count_rejects_non_baseline_agreement(self):
        class Portal:
            def agreement_details(self, partner):
                return ([{'id':'other','details':{}}], 'filtered')
        partner={'id':'i','name':'U','agreementCount':1}
        with self.assertRaisesRegex(ValueError,'not in year baseline'):
            map_filtered_partner(Portal(),partner,
                {'ids':['a','b'],'sourceRef':'baseline'}, {})


if __name__=='__main__':unittest.main()
