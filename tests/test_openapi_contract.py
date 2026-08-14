from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, cast

import pytest
from scripts.export_openapi import (
    OpenApiContractError,
    build_openapi_contract,
    main,
    render_openapi_contract,
    validate_openapi_contract,
)

ROOT = Path(__file__).resolve().parents[1]
TRACKED_OPENAPI = ROOT / "contracts/openapi.json"


def _mutable_schema() -> dict[str, Any]:
    return cast(dict[str, Any], copy.deepcopy(build_openapi_contract()))


def test_tracked_openapi_matches_the_fastapi_application() -> None:
    assert TRACKED_OPENAPI.read_text(encoding="utf-8") == render_openapi_contract()


def test_openapi_rejects_unversioned_application_path() -> None:
    schema = _mutable_schema()
    schema["paths"]["/unsafe"] = copy.deepcopy(schema["paths"]["/health"])

    with pytest.raises(OpenApiContractError, match="outside the versioned contract"):
        validate_openapi_contract(schema)


def test_openapi_rejects_duplicate_operation_ids() -> None:
    schema = _mutable_schema()
    operations = [
        operation
        for path_item in schema["paths"].values()
        for method, operation in path_item.items()
        if method in {"get", "post"}
    ]
    operations[1]["operationId"] = operations[0]["operationId"]

    with pytest.raises(OpenApiContractError, match="duplicate operationId"):
        validate_openapi_contract(schema)


def test_openapi_rejects_development_credentials() -> None:
    schema = _mutable_schema()
    schema["info"]["description"] = "postgresql://zenit:change_me@postgres/zenit"

    with pytest.raises(OpenApiContractError, match="development secret or credential"):
        validate_openapi_contract(schema)


def test_openapi_requires_the_stable_error_response_on_every_operation() -> None:
    schema = _mutable_schema()
    del schema["paths"]["/health"]["get"]["responses"]["default"]

    with pytest.raises(OpenApiContractError, match=r"responses\.default must be an object"):
        validate_openapi_contract(schema)


def test_openapi_check_reports_a_stale_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stale_contract = tmp_path / "openapi.json"
    stale_contract.write_text("{}\n", encoding="utf-8")

    assert main(["--check", "--output", str(stale_contract)]) == 1
    assert "tracked OpenAPI contract is stale" in capsys.readouterr().err
