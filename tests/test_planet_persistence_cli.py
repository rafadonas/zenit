from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from zenit_api.config import Settings
from zenit_geospatial.planet_persistence_cli import build_parser, resolve_database_url, run
from zenit_geospatial.satellite_catalog import CatalogedScene
from zenit_geospatial.satellite_providers import Acquisition, SearchPage


def _arguments(*extra: str):
    return build_parser().parse_args(
        [
            "--bbox",
            "-46.80",
            "-23.55",
            "-46.76",
            "-23.50",
            "--from-date",
            "2026-08-01",
            "--to-date",
            "2026-08-07",
            *extra,
        ]
    )


def test_persistence_parser_requires_explicit_confirmation() -> None:
    arguments = _arguments()

    assert arguments.from_date == date(2026, 8, 1)
    assert arguments.persist is False


def test_persistence_refuses_writes_without_confirmation() -> None:
    with pytest.raises(RuntimeError, match="--persist confirmation"):
        run(_arguments(), Settings(_env_file=None, PL_API_KEY="private-planet-key"))


def test_persistence_checks_key_before_network_after_confirmation() -> None:
    with pytest.raises(RuntimeError, match="Planet API key is not configured"):
        run(_arguments("--persist"), Settings(_env_file=None, PL_API_KEY=None))


def _acquisition(scene_id: str) -> Acquisition:
    return Acquisition(
        provider="planet",
        collection="PSScene",
        sensor="planet-scope",
        external_scene_id=scene_id,
        acquired_at=datetime(2026, 8, 5, 13, 53, tzinfo=UTC),
        bbox=(-46.80, -23.55, -46.76, -23.50),
        geometry=None,
        cloud_cover_percent=1.5,
        assets={"ortho_analytic_4b": "active"},
        source_metadata={"item_type": "PSScene"},
    )


class _Client:
    def __init__(self, page: SearchPage) -> None:
        self._page = page
        self.searches = 0

    def search(self, payload):
        self.searches += 1
        return self._page


class _Catalog:
    def __init__(self, known: set[str] | None = None) -> None:
        self.known = known or set()
        self.registered: list[str] = []

    def register(self, acquisition: Acquisition, discovered_at: datetime) -> CatalogedScene:
        assert discovered_at.tzinfo is not None
        self.registered.append(acquisition.external_scene_id)
        created = acquisition.external_scene_id not in self.known
        self.known.add(acquisition.external_scene_id)
        return CatalogedScene(id=uuid4(), created=created, cache_status="discovered")


def _settings(database_url: str = "postgresql+psycopg://zenit:pw@localhost:5433/zenit") -> Settings:
    return Settings(_env_file=None, PL_API_KEY="private-planet-key", DATABASE_URL=database_url)


def test_persistence_counts_created_and_existing_scenes() -> None:
    page = SearchPage(acquisitions=(_acquisition("a"), _acquisition("b")), next_url=None)
    catalog = _Catalog(known={"b"})

    result = run(_arguments("--persist"), _settings(), client=_Client(page), catalog=catalog)

    assert result["catalog_acquisitions"] == 2
    assert result["scenes_created"] == 1
    assert result["scenes_existing"] == 1
    assert result["order_requested"] is False
    assert result["download_requested"] is False
    assert catalog.registered == ["a", "b"]


def test_repeating_the_same_search_creates_no_duplicate() -> None:
    page = SearchPage(acquisitions=(_acquisition("a"),), next_url=None)
    catalog = _Catalog()

    first = run(_arguments("--persist"), _settings(), client=_Client(page), catalog=catalog)
    second = run(_arguments("--persist"), _settings(), client=_Client(page), catalog=catalog)

    assert (first["scenes_created"], first["scenes_existing"]) == (1, 0)
    assert (second["scenes_created"], second["scenes_existing"]) == (0, 1)


def test_empty_catalog_page_touches_no_database() -> None:
    catalog = _Catalog()

    result = run(
        _arguments("--persist"),
        _settings(),
        client=_Client(SearchPage(acquisitions=(), next_url="https://example.invalid/next")),
        catalog=catalog,
    )

    assert result["catalog_acquisitions"] == 0
    assert result["has_next_page"] is True
    assert catalog.registered == []


def test_compose_only_host_requires_explicit_destination(monkeypatch) -> None:
    import zenit_geospatial.database_target as target

    monkeypatch.setattr(target, "_resolves", lambda host: False)
    with pytest.raises(RuntimeError, match="only reachable inside Compose"):
        run(
            _arguments("--persist"),
            _settings("postgresql+psycopg://zenit:pw@postgres:5432/zenit"),
            client=_Client(SearchPage(acquisitions=(), next_url=None)),
            catalog=_Catalog(),
        )


def test_explicit_destination_is_used_without_rewriting_the_host() -> None:
    assert resolve_database_url(
        "postgresql://zenit:pw@127.0.0.1:5433/zenit",
        "postgresql+psycopg://zenit:pw@postgres:5432/zenit",
    ) == "postgresql://zenit:pw@127.0.0.1:5433/zenit"
    assert resolve_database_url(None, "postgresql+psycopg://zenit:pw@db.example:5432/zenit") == (
        "postgresql://zenit:pw@db.example:5432/zenit"
    )
