from datetime import date

import pytest
from pydantic import SecretStr

from zenit_api.config import Settings
from zenit_geospatial.planet_cli import build_parser, run


def test_planet_parser_accepts_bounded_discovery_arguments() -> None:
    arguments = build_parser().parse_args(
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
        ]
    )

    assert arguments.bbox == [-46.80, -23.55, -46.76, -23.50]
    assert arguments.from_date == date(2026, 8, 1)
    assert arguments.limit == 25
    assert arguments.require_download_permission is False


def test_planet_parser_supports_download_permission_filter_without_download() -> None:
    arguments = build_parser().parse_args(
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
            "--require-download-permission",
        ]
    )

    assert arguments.require_download_permission is True


def test_planet_run_requires_backend_key_before_network() -> None:
    arguments = build_parser().parse_args(
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
        ]
    )

    with pytest.raises(RuntimeError, match="Planet API key is not configured"):
        run(arguments, Settings(_env_file=None, PL_API_KEY=None))


def test_planet_key_is_loaded_as_secret() -> None:
    settings = Settings(_env_file=None, PL_API_KEY="private-planet-key")

    assert isinstance(settings.planet_api_key, SecretStr)
    assert "private-planet-key" not in repr(settings)
