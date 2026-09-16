from uuid import UUID, uuid4

import numpy as np
import pytest
from tests.test_planet_process import analytic, full_zone, udm2

from zenit_geospatial.planet_process import ProcessingError
from zenit_geospatial.planet_process_cli import build_parser, run
from zenit_geospatial.planet_process_repository import CachedAsset, CachedScene, PilotZone

SCENE_ID = UUID("48000000-0000-4000-8000-000000000010")


def asset(role: str, status: str = "verified") -> CachedAsset:
    return CachedAsset(
        id=uuid4(),
        asset_role=role,
        storage_uri=f"s3://zenit-raw/planet/{role}.aesgcm",
        checksum_sha256="a" * 64 if role.startswith("ortho") else "b" * 64,
        storage_version_id="v1",
        verification_status=status,
    )


def zone(segment_index: int = 195, operational: bool = False) -> PilotZone:
    return PilotZone(
        id=uuid4(),
        segment_index=segment_index,
        zone_type="left",
        geometry=full_zone(),
        data_status="prepared",
        eligible_for_operations=operational,
    )


class _Repository:
    def __init__(self, assets, zones) -> None:
        self._assets = assets
        self._zones = zones
        self.persisted: list[str] = []
        self.known_keys: set[str] = set()

    def scene(self, external_scene_id: str) -> CachedScene:
        return CachedScene(id=SCENE_ID, external_scene_id=external_scene_id, assets=self._assets)

    def pilot_zones(self, *, road_code, from_segment, to_segment):
        return tuple(z for z in self._zones if from_segment <= z.segment_index <= to_segment)

    def persist(self, *, scene_id, statistics, idempotency_key, parameters, explanation) -> bool:
        self.persisted.append(idempotency_key)
        created = idempotency_key not in self.known_keys
        self.known_keys.add(idempotency_key)
        return created


class _Reader:
    def __init__(self, clear: np.ndarray | None = None) -> None:
        self.reads = 0
        self._clear = clear

    def read_plaintext(self, storage_uri: str, version_id: str | None) -> bytes:
        self.reads += 1
        return analytic() if "ortho" in storage_uri else udm2(self._clear)


def arguments(*extra: str):
    return build_parser().parse_args(
        ["--scene-id", "20260805_135356_12_253c", "--from-segment", "195", *extra]
    )


def test_pilot_run_reports_zone_statistics_without_provider_calls() -> None:
    repository = _Repository((asset("ortho_analytic_4b"), asset("udm2")), (zone(195), zone(196)))
    reader = _Reader()

    report = run(arguments("--segments", "2"), repository=repository, reader=reader)

    assert report["zones"] == 2
    assert report["provider_calls"] == 0
    assert report["conclusion"] == "inconclusive"
    assert report["eligible_for_operations"] is False
    assert report["analysis_runs_created"] == 2
    assert reader.reads == 2  # one analytic and one UDM2 read, reused across zones


def test_repeating_the_same_inputs_creates_no_new_analysis_run() -> None:
    repository = _Repository((asset("ortho_analytic_4b"), asset("udm2")), (zone(195),))

    first = run(arguments(), repository=repository, reader=_Reader())
    second = run(arguments(), repository=repository, reader=_Reader())

    assert first["analysis_runs_created"] == 1
    assert second["analysis_runs_created"] == 0
    assert repository.persisted[0] == repository.persisted[1]


def test_unverified_asset_blocks_processing() -> None:
    repository = _Repository(
        (asset("ortho_analytic_4b"), asset("udm2", status="mismatch")), (zone(195),)
    )

    with pytest.raises(ProcessingError, match="mismatch"):
        run(arguments(), repository=repository, reader=_Reader())


def test_asset_never_audited_blocks_processing() -> None:
    repository = _Repository(
        (asset("ortho_analytic_4b"), asset("udm2", status=None)), (zone(195),)
    )

    with pytest.raises(ProcessingError, match="unverified"):
        run(arguments(), repository=repository, reader=_Reader())


def test_operational_zone_is_refused() -> None:
    repository = _Repository(
        (asset("ortho_analytic_4b"), asset("udm2")), (zone(195, operational=True),)
    )

    with pytest.raises(ProcessingError, match="operational"):
        run(arguments(), repository=repository, reader=_Reader())


def test_dry_run_computes_without_persisting() -> None:
    repository = _Repository((asset("ortho_analytic_4b"), asset("udm2")), (zone(195),))

    report = run(arguments("--dry-run"), repository=repository, reader=_Reader())

    assert report["persisted"] is False
    assert report["zones"] == 1
    assert repository.persisted == []


def test_cloudy_zone_is_reported_as_no_observation() -> None:
    repository = _Repository((asset("ortho_analytic_4b"), asset("udm2")), (zone(195),))

    report = run(
        arguments("--dry-run"),
        repository=repository,
        reader=_Reader(clear=np.zeros((4, 4), dtype="uint8")),
    )

    assert report["zones_by_quality"] == {"no_observation": 1}


def test_missing_pilot_geometry_is_reported() -> None:
    repository = _Repository((asset("ortho_analytic_4b"), asset("udm2")), ())

    with pytest.raises(LookupError, match="no zone geometry"):
        run(arguments(), repository=repository, reader=_Reader())
