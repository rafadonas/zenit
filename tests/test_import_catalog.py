from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zenit_geospatial.import_catalog import (
    ImportDecision,
    ImportStatus,
    InMemoryImportCatalog,
    canonical_parameters,
    identify_source,
    make_idempotency_key,
    plan_import,
)


class ImportIdentityTests(unittest.TestCase):
    def test_canonical_parameters_are_order_independent(self) -> None:
        left = canonical_parameters({"crs": 4326, "strict": True})
        right = canonical_parameters({"strict": True, "crs": 4326})

        self.assertEqual(left, right)

    def test_key_changes_with_parser_version_or_parameters(self) -> None:
        checksum = "a" * 64
        baseline = make_idempotency_key(checksum, "km-markers", "1.0.0", {"strict": True})

        self.assertNotEqual(
            baseline,
            make_idempotency_key(checksum, "km-markers", "1.0.1", {"strict": True}),
        )
        self.assertNotEqual(
            baseline,
            make_idempotency_key(checksum, "km-markers", "1.0.0", {"strict": False}),
        )

    def test_successful_import_is_not_planned_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.kml"
            path.write_text("source bytes", encoding="utf-8")
            source = identify_source(path, "kml")
            catalog = InMemoryImportCatalog()
            first = plan_import(source, "km-markers", "1.0.0", catalog)
            catalog.set_status(first.identity.idempotency_key, ImportStatus.SUCCEEDED)

            second = plan_import(source, "km-markers", "1.0.0", catalog)

        self.assertEqual(first.decision, ImportDecision.PLANNED)
        self.assertEqual(second.decision, ImportDecision.ALREADY_SUCCEEDED)
        self.assertEqual(first.identity.idempotency_key, second.identity.idempotency_key)

    def test_failed_import_is_explicitly_retryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.kml"
            path.write_text("source bytes", encoding="utf-8")
            source = identify_source(path, "kml")
            catalog = InMemoryImportCatalog()
            first = plan_import(source, "km-markers", "1.0.0", catalog)
            catalog.set_status(first.identity.idempotency_key, ImportStatus.FAILED)

            retry = plan_import(source, "km-markers", "1.0.0", catalog)

        self.assertEqual(retry.decision, ImportDecision.RETRY_FAILED)
        self.assertEqual(retry.previous_status, ImportStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
