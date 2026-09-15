from datetime import date

import pytest
from pydantic import SecretStr

from zenit_api.config import Settings
from zenit_geospatial.planet_capabilities_cli import build_parser, run


def test_capabilities_parser_accepts_a_bounded_window() -> None:
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

    assert arguments.from_date == date(2026, 8, 1)
    assert arguments.to_date == date(2026, 8, 7)


def test_capabilities_requires_backend_key_before_network() -> None:
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


def test_capabilities_does_not_expose_the_secret_in_settings() -> None:
    settings = Settings(_env_file=None, PL_API_KEY="private-planet-key")

    assert isinstance(settings.planet_api_key, SecretStr)
    assert "private-planet-key" not in repr(settings)
