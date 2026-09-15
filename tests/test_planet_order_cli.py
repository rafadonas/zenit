import pytest

from zenit_api.config import Settings
from zenit_geospatial.planet_order_cli import build_parser, run


def _arguments(*extra: str):
    return build_parser().parse_args([*extra])


def test_order_parser_defaults_to_the_approved_bounded_pilot() -> None:
    arguments = _arguments()

    assert arguments.road_code == "SP021"
    assert arguments.segment_index == 195
    assert arguments.buffer_m == 25.0
    assert arguments.max_area_m2 == 10_000.0
    assert arguments.max_bytes == 104_857_600
    assert arguments.retention_days == 30
    assert arguments.execute is False


def test_order_requires_explicit_external_write_confirmation() -> None:
    with pytest.raises(RuntimeError, match="--execute confirmation"):
        run(_arguments(), Settings(_env_file=None, PL_API_KEY="private-planet-key"))


def test_order_checks_key_after_confirmation() -> None:
    with pytest.raises(RuntimeError, match="Planet API key is not configured"):
        run(_arguments("--execute"), Settings(_env_file=None, PL_API_KEY=None))


def test_order_rejects_limits_larger_than_ticket_contract() -> None:
    arguments = _arguments("--execute", "--max-bytes", "104857601")

    with pytest.raises(ValueError, match="max-bytes"):
        run(arguments, Settings(_env_file=None, PL_API_KEY="private-planet-key"))
