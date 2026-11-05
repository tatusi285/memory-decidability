"""The shipped artifact must be complete, checksummed and portable."""

from __future__ import annotations

import csv
import hashlib
import unittest

from memdec import manifest, paths


class TestManifest(unittest.TestCase):
    def test_run_count_and_probes(self):
        runs = manifest.load_runs()
        self.assertEqual(len(runs), 37)
        self.assertEqual(sum(spec.probes for spec in runs.values()), 50_832)

    def test_every_run_has_a_directory(self):
        for run_id in manifest.load_runs():
            self.assertTrue(manifest.result_path(run_id).is_file(), run_id)

    def test_probe_counts_match_the_files(self):
        for run_id, spec in manifest.load_runs().items():
            self.assertEqual(manifest.probes_in(run_id), spec.probes, run_id)

    def test_summary_rows_cover_every_batch(self):
        for run_id, spec in manifest.load_runs().items():
            rows = manifest.summary_rows(run_id)
            policies = 4 if spec.policies == "all" else 1
            expected = len(spec.delay_list) * spec.seeds * policies
            self.assertEqual(len(rows), expected, run_id)

    def test_batch_rates_are_fractions(self):
        for run_id in manifest.load_runs():
            for value in manifest.batch_rates(run_id):
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)


class TestChecksums(unittest.TestCase):
    def test_every_csv_matches_its_recorded_hash(self):
        listing = (paths.data_dir() / "CHECKSUMS.sha256").read_text(encoding="utf-8")
        self.assertTrue(listing.strip())
        for line in listing.strip().splitlines():
            digest, relative = line.split("  ", 1)
            path = paths.repo_root() / relative
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, digest, f"checksum mismatch for {relative}")


class TestPortability(unittest.TestCase):
    def test_no_absolute_user_paths_in_the_data(self):
        """The original end-to-end script hard-coded an absolute Windows path."""
        for path in paths.data_dir().rglob("*"):
            if path.suffix not in {".csv", ".md", ".json"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            self.assertNotIn("C:\\Users", text, f"{path} embeds a local path")

    def test_no_credentials_in_the_data(self):
        for path in paths.data_dir().rglob("*"):
            if path.suffix not in {".csv", ".md", ".json"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            self.assertNotIn("sk-", text, f"{path} may contain a key")

    def test_manifest_source_is_preserved(self):
        source = paths.data_dir() / "source" / "run_manifest_zh.csv"
        self.assertTrue(source.is_file())
        with source.open(encoding="utf-8-sig") as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 37)


class TestKnownArtifacts(unittest.TestCase):
    def test_byte_identical_groups_are_documented(self):
        """Some files share a hash. This is expected; the test pins which ones."""
        from memdec.analysis.audit import duplicate_artifacts

        groups = duplicate_artifacts()
        self.assertEqual(len(groups), 4)
        flattened = sorted(run for group in groups.values() for run in group)
        self.assertIn("out_glm_bare_old", flattened)
        self.assertIn("out_rsn_bare_new", flattened)

    def test_no_run_carries_run_meta(self):
        """The README claimed 23 runs had run_meta.json; none do."""
        runs = manifest.load_runs()
        self.assertEqual(sum(1 for r in runs if manifest.run_meta(r)), 0)


if __name__ == "__main__":
    unittest.main()
