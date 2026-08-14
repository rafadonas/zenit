from pathlib import Path

COMPOSE_FILE = Path("compose.yaml")


def test_dashboard_healthcheck_uses_dependency_aware_route() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    dashboard = compose.split("\n  dashboard:\n", maxsplit=1)[1].split(
        "\nvolumes:", maxsplit=1
    )[0]

    assert "http://127.0.0.1:3000/api/health" in dashboard
    assert "condition: service_healthy" in dashboard
