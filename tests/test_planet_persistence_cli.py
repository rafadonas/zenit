from datetime import date

import pytest

from zenit_api.config import Settings
from zenit_geospatial.planet_persistence_cli import build_parser, run


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
