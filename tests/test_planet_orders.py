import unittest
from collections.abc import Mapping
from typing import Any

import pytest

from zenit_geospatial.planet_orders import (
    EXPECTED_ANALYTIC_UDM2_ASSETS,
    PLANET_ORDERS_URL,
    PlanetOrderError,
    PlanetOrdersClient,
    asset_role,
    build_scenes_order_request,
    media_type,
    order_results,
)

AOI = {
    "type": "Polygon",
    "coordinates": [[[1.0, 2.0], [1.1, 2.0], [1.1, 2.1], [1.0, 2.0]]],
}


class FakeOrderTransport:
    def __init__(self) -> None:
        self.post_calls: list[tuple[str, Mapping[str, Any], Mapping[str, str] | None]] = []
        self.get_calls: list[tuple[str, Mapping[str, str] | None]] = []
        self.bytes_calls: list[tuple[str, int | None]] = []

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.post_calls.append((url, payload, headers))
        return {"id": "order-1", "state": "queued"}

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.get_calls.append((url, headers))
        return {"id": "order-1", "state": "success", "results": []}

    def get_bytes(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        maximum_bytes: int | None = None,
    ) -> Any:
        self.bytes_calls.append((url, maximum_bytes))
        return None


class PlanetOrderTests(unittest.TestCase):
    def test_order_request_is_one_scene_and_clipped(self) -> None:
        request = build_scenes_order_request(
            name="pilot",
            scene_id="scene-1",
            aoi=AOI,
        )

        self.assertEqual(request["source_type"], "scenes")
        self.assertEqual(request["products"][0]["item_ids"], ["scene-1"])
        self.assertEqual(request["products"][0]["product_bundle"], "analytic_udm2")
        self.assertEqual(request["tools"][0]["clip"]["aoi"], AOI)

    def test_order_client_keeps_api_key_in_header(self) -> None:
        transport = FakeOrderTransport()
        client = PlanetOrdersClient(transport, "private-key")

        response = client.create({"name": "pilot"})

        self.assertEqual(response["id"], "order-1")
        url, _, headers = transport.post_calls[0]
        self.assertEqual(url, PLANET_ORDERS_URL)
        self.assertEqual(headers, {"Authorization": "api-key private-key"})
        self.assertNotIn("private-key", url)

    def test_result_roles_and_bundle_media_types_are_stable(self) -> None:
        results = order_results(
            {
                "_links": {"results": [
                    {
                        "delivery": "success",
                        "name": "scene_3B_AnalyticMS_clip.tif",
                        "location": "https://api.planet.com/compute/ops/download/?token=x",
                    },
                    {
                        "delivery": "success",
                        "name": "scene_3B_AnalyticMS_metadata_clip.xml",
                        "location": "https://api.planet.com/compute/ops/download/?token=y",
                    },
                    {
                        "delivery": "success",
                        "name": "scene_ortho_udm2.tif",
                        "location": "https://api.planet.com/compute/ops/download/?token=z",
                    },
                ]}
            }
        )

        self.assertEqual({item.asset_role for item in results}, EXPECTED_ANALYTIC_UDM2_ASSETS)
        self.assertEqual(asset_role("scene_3B_udm2_clip.tif"), "ortho_udm2")
        self.assertEqual(media_type("application/octet-stream", "x.xml"), "application/xml")

    def test_result_rejects_untrusted_download_location(self) -> None:
        with pytest.raises(PlanetOrderError, match="invalid download location"):
            order_results(
                {
                    "results": [
                        {
                            "delivery": "success",
                            "name": "scene.tif",
                            "location": "https://evil.invalid/download?token=x",
                        }
                    ]
                }
            )
