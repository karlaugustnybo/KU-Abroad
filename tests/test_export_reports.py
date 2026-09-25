import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from export_reports import match_institutions, safe_links


class ReportExportTests(unittest.TestCase):
    def test_unique_display_identity_reconciles_changed_source_id(self):
        report_institution = dict(institution_id="old", name="University of Hong Kong",
                                  country="Hong Kong (China)", city="Hong Kong")
        explorer_institution = dict(id="new", name="University of Hong Kong",
                                    country="Hong Kong (China)", city="Hong Kong")
        self.assertEqual(match_institutions([report_institution], [explorer_institution]),
                         {"old": "new"})
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            match_institutions([report_institution], [explorer_institution,
                                                     explorer_institution | {"id": "duplicate"}])

    def test_only_http_links_are_exported(self):
        self.assertEqual(safe_links('["https://ku.dk/file", "javascript:alert(1)", "file:///secret"]'),
                         ["https://ku.dk/file"])


if __name__ == "__main__":
    unittest.main()
