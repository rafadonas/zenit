import json
import unittest
from datetime import UTC, datetime

from zenit_geospatial.sentinel_process import (
    PROCESS_EVALSCRIPT,
    build_process_request,
    parse_process_response,
)


class SentinelProcessTests(unittest.TestCase):
    def test_request_uses_metric_aoi_ten_meter_output_and_userdata(self) -> None:
        geometry = {"type": "Polygon", "coordinates": [[[1, 1], [2, 1], [1, 1]]]}
        request = build_process_request(
            geometry,
            datetime(2026, 7, 29, tzinfo=UTC),
            datetime(2026, 7, 30, tzinfo=UTC),
        )

        self.assertEqual(request["output"]["resx"], 10)
        self.assertEqual(request["output"]["resy"], 10)
        self.assertIn("/3857", request["input"]["bounds"]["properties"]["crs"])
        self.assertEqual(len(request["output"]["responses"]), 2)
        self.assertIn('mosaicking: "TILE"', PROCESS_EVALSCRIPT)
        self.assertIn("outputMetadata.userData", PROCESS_EVALSCRIPT)
        json.dumps(request)

    def test_multipart_response_preserves_tiff_and_contributor_metadata(self) -> None:
        boundary = "zenit-test-boundary"
        body = (
            f"--{boundary}\r\nContent-Type: image/tiff\r\n\r\n".encode()
            + b"II*\x00fixture"
            + f"\r\n--{boundary}\r\nContent-Type: application/json\r\n\r\n".encode()
            + b'{"scenes":[{"tileId":"tile-1"}]}'
            + f"\r\n--{boundary}--\r\n".encode()
        )

        artifacts = parse_process_response(body, f'multipart/mixed; boundary="{boundary}"')

        self.assertTrue(artifacts.geotiff.startswith(b"II*\x00"))
        self.assertEqual(len(artifacts.user_data["scenes"]), 1)


if __name__ == "__main__":
    unittest.main()
