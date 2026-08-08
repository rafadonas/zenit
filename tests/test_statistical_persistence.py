import unittest
from datetime import UTC, datetime
from uuid import UUID

from zenit_geospatial.sentinel_statistics import QualityStatus, SentinelStatistic
from zenit_geospatial.statistical_persistence import (
    prepared_explanation,
    statistical_idempotency_key,
)


def statistic() -> SentinelStatistic:
    return SentinelStatistic(
        interval_from=datetime(2026, 8, 5, tzinfo=UTC),
        interval_to=datetime(2026, 8, 6, tzinfo=UTC),
        mean_ndvi=0.55,
        ndvi_std=0.08,
        ndvi_p25=0.48,
        ndvi_p50=0.56,
        ndvi_p75=0.63,
        sample_count=20,
        no_data_count=0,
        valid_pixel_ratio=1.0,
        quality_status=QualityStatus.ACCEPTED,
    )


class StatisticalPersistenceTests(unittest.TestCase):
    def test_idempotency_key_is_deterministic(self) -> None:
        scene_id = UUID("00000000-0000-0000-0000-000000000001")
        zone_id = UUID("00000000-0000-0000-0000-000000000002")

        first = statistical_idempotency_key(scene_id, zone_id, "a" * 64, statistic())
        second = statistical_idempotency_key(scene_id, zone_id, "a" * 64, statistic())

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_prepared_result_remains_inconclusive_despite_accepted_pixels(self) -> None:
        explanation = prepared_explanation(statistic(), geometry_hash="a" * 64)

        self.assertEqual(explanation["quality_status"], QualityStatus.ACCEPTED)
        self.assertEqual(explanation["input_data_status"], "prepared")
        self.assertEqual(explanation["result_data_status"], "inconclusive")
        self.assertTrue(explanation["statistical_api_mosaic"])
        self.assertIn("does not establish vegetation height", explanation["reasons"][1])


if __name__ == "__main__":
    unittest.main()
