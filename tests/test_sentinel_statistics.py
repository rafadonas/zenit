import unittest
from datetime import UTC, datetime

from zenit_geospatial.sentinel_statistics import (
    NDVI_SCL_EVALSCRIPT,
    QualityPolicy,
    QualityStatus,
    StatisticalResponseError,
    build_statistical_request,
    parse_statistical_response,
)

AOI = {
    "type": "Polygon",
    "coordinates": [
        [[-46.80, -23.55], [-46.79, -23.55], [-46.79, -23.54], [-46.80, -23.55]]
    ],
}


def response(sample_count: int, no_data_count: int) -> dict:
    return {
        "data": [
            {
                "interval": {
                    "from": "2026-08-05T00:00:00Z",
                    "to": "2026-08-06T00:00:00Z",
                },
                "outputs": {
                    "ndvi": {
                        "bands": {
                            "B0": {
                                "stats": {
                                    "min": 0.1,
                                    "max": 0.9,
                                    "mean": 0.55,
                                    "stDev": 0.08,
                                    "sampleCount": sample_count,
                                    "noDataCount": no_data_count,
                                    "percentiles": {
                                        "25.0": 0.48,
                                        "50.0": 0.56,
                                        "75.0": 0.63,
                                    },
                                }
                            }
                        }
                    }
                },
            }
        ],
        "status": "OK",
    }


class SentinelStatisticsTests(unittest.TestCase):
    def test_request_uses_scl_data_mask_and_ten_meter_resolution(self) -> None:
        request = build_statistical_request(
            AOI,
            datetime(2026, 8, 5, tzinfo=UTC),
            datetime(2026, 8, 6, tzinfo=UTC),
            max_cloud_coverage=80,
        )

        self.assertEqual(request["input"]["data"][0]["type"], "sentinel-2-l2a")
        self.assertEqual(request["aggregation"]["resx"], 10)
        self.assertEqual(request["aggregation"]["resy"], 10)
        self.assertIn('"SCL"', NDVI_SCL_EVALSCRIPT)
        self.assertIn("dataMask", NDVI_SCL_EVALSCRIPT)
        self.assertIn("[0, 1, 3, 6, 7, 8, 9, 10, 11]", NDVI_SCL_EVALSCRIPT)

    def test_response_calculates_valid_ratio_and_percentiles(self) -> None:
        result = parse_statistical_response(response(100, 20))[0]

        self.assertEqual(result.mean_ndvi, 0.55)
        self.assertEqual(result.ndvi_p50, 0.56)
        self.assertEqual(result.valid_pixel_ratio, 0.8)
        self.assertEqual(result.quality_status, QualityStatus.ACCEPTED)

    def test_quality_policy_preserves_warning_rejection_and_no_observation(self) -> None:
        policy = QualityPolicy()

        self.assertEqual(policy.classify(0.7), QualityStatus.ACCEPTED)
        self.assertEqual(policy.classify(0.4), QualityStatus.WARNING)
        self.assertEqual(policy.classify(0.39), QualityStatus.REJECTED)
        self.assertEqual(policy.classify(None), QualityStatus.NO_OBSERVATION)

    def test_zero_samples_are_no_observation_not_zero_ndvi(self) -> None:
        result = parse_statistical_response(response(0, 0))[0]

        self.assertIsNone(result.valid_pixel_ratio)
        self.assertEqual(result.quality_status, QualityStatus.NO_OBSERVATION)

    def test_malformed_stats_fail_closed(self) -> None:
        with self.assertRaisesRegex(StatisticalResponseError, "NDVI stats"):
            parse_statistical_response(
                {
                    "data": [
                        {
                            "interval": {
                                "from": "2026-08-05T00:00:00Z",
                                "to": "2026-08-06T00:00:00Z",
                            }
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
