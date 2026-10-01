import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from portal_client import Portal, collapse_reviewed_duplicates


class PortalClientTests(unittest.TestCase):
    def test_reviewed_duplicate_preserves_both_source_references(self):
        details = {'Agreement name': 'Sorbonne University - Erasmus - 4EU+'}
        items = [dict(id='a', details=details, sourceRef='one'),
                 dict(id='a', details=details, sourceRef='two')]
        unique, duplicates = collapse_reviewed_duplicates(items, '2027/2028', 'Sorbonne University')
        self.assertEqual(duplicates, 1)
        self.assertEqual(unique[0]['sourceRef'], 'one')
        self.assertEqual(unique[0]['duplicateSourceRefs'], ['two'])

    def test_unreviewed_duplicate_remains_blocked(self):
        items = [dict(id='a', details={'Agreement name': 'Other'}, sourceRef='one'),
                 dict(id='a', details={'Agreement name': 'Other'}, sourceRef='two')]
        with self.assertRaisesRegex(ValueError, 'requires review'):
            collapse_reviewed_duplicates(items, '2027/2028', 'Sorbonne University')

    def test_resumed_session_can_request_popups_without_a_ui_search(self):
        browser, archive = MagicMock(), MagicMock()
        page = browser.new_context.return_value.new_page.return_value
        page.evaluate.side_effect = [
            {},
            "function openFancy(cause) { return '&cpif_live123=' + cause; }",
            {},
            "function openFancy(cause) { return '&cpif_new456=' + cause; }",
        ]
        portal = Portal(browser, archive)
        self.assertEqual(portal.cause_field, 'cpif_live123')
        # Reopened sessions must resolve the parameter from the new live form.
        portal.open()
        self.assertEqual(portal.cause_field, 'cpif_new456')


if __name__ == '__main__':
    unittest.main()
