import shutil
import tempfile
import unittest
from pathlib import Path

import duckdb

from scripts.build_duckdb import build_database


class BuildDuckDBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = Path(tempfile.mkdtemp())
        cls.database = cls.directory / "ku_abroad.duckdb"
        build_database("2026-09-19", cls.database)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.directory)

    def test_build_current_run(self) -> None:
        with duckdb.connect(str(self.database), read_only=True) as connection:
            # The source has 525 rows; DA-Overflytning is excluded from catalog.
            self.assertEqual(connection.execute("SELECT count(*) FROM catalog.institutions").fetchone()[0], 524)
            self.assertEqual(connection.execute("SELECT count(*) FROM catalog.agreements").fetchone()[0], 611)
            self.assertEqual(connection.execute("SELECT count(*) FROM availability.portal_queries").fetchone()[0], 342)
            self.assertEqual(connection.execute("SELECT count(*) FROM raw.http_events").fetchone()[0], 30_510)
            self.assertEqual(connection.execute("SELECT count(*) FROM metadata.data_quality_issues").fetchone()[0], 1)

            bad_references = connection.execute(
            """SELECT count(*)
               FROM availability.query_agreement_matches m
               LEFT JOIN catalog.agreements a USING (run_id, agreement_id, institution_id)
               WHERE a.agreement_id IS NULL"""
            ).fetchone()[0]
            self.assertEqual(bad_references, 0)

            coverage = connection.execute("SELECT * FROM mart.current_query_coverage").fetchone()
            self.assertEqual(coverage[0:4], (342, 342, 2, 340))

    def test_exchange_options_have_explicit_dimensions(self) -> None:
        with duckdb.connect(str(self.database), read_only=True) as connection:
            missing = connection.execute(
                """SELECT count(*) FROM mart.current_exchange_options
                   WHERE academic_year IS NULL OR study_field IS NULL
                      OR institution_id IS NULL OR agreement_id IS NULL"""
            ).fetchone()[0]
            self.assertEqual(missing, 0)


if __name__ == "__main__":
    unittest.main()
