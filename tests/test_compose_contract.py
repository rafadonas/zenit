from pathlib import Path

COMPOSE_FILE = Path("compose.yaml")


def test_dashboard_healthcheck_uses_dependency_aware_route() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    dashboard = compose.split("\n  dashboard:\n", maxsplit=1)[1].split(
        "\nvolumes:", maxsplit=1
    )[0]

    assert "http://127.0.0.1:3000/api/health" in dashboard
    assert "condition: service_healthy" in dashboard


def test_local_dashboards_use_distinct_ports_identities_and_cookies() -> None:
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    manager = compose.split("\n  dashboard:\n", maxsplit=1)[1].split(
        "\n  dashboard-supervisor:\n", maxsplit=1
    )[0]
    supervisor = compose.split("\n  dashboard-supervisor:\n", maxsplit=1)[1].split(
        "\nvolumes:", maxsplit=1
    )[0]

    assert '"3000:3000"' in manager
    assert "DASHBOARD_FIXED_USER_EMAIL: ${DASHBOARD_MANAGER_EMAIL" in manager
    assert "DASHBOARD_FIXED_HOME_PATH: /overview" in manager
    assert "DASHBOARD_SESSION_COOKIE_NAME: zenit_manager_session" in manager
    assert '"3002:3000"' in supervisor
    assert "DASHBOARD_FIXED_USER_EMAIL: ${DASHBOARD_SUPERVISOR_EMAIL" in supervisor
    assert "DASHBOARD_FIXED_HOME_PATH: /mowing-photo-reviews" in supervisor
    assert "DASHBOARD_SESSION_COOKIE_NAME: zenit_supervisor_session" in supervisor
