from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from scripts.verify_android_apk import ApkVerificationError, verify_apk


def _write_apk(path: Path, *, omit: str | None = None) -> None:
    entries = {
        "AndroidManifest.xml": b"binary manifest",
        "classes.dex": b"dex",
        "resources.arsc": b"resources",
        "assets/flutter_assets/AssetManifest.bin": b"assets",
        "lib/arm64-v8a/libflutter.so": b"flutter",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            if name != omit:
                archive.writestr(name, content)


def _tool(path: Path) -> Path:
    path.write_text("tool", encoding="utf-8")
    path.chmod(0o755)
    return path


def _runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    del kwargs
    if "application-id" in command:
        output = "br.com.zenit.zenit_mobile\n"
    elif "version-name" in command:
        output = "1.0.0\n"
    elif "version-code" in command:
        output = "1\n"
    else:
        output = "Verified using v2 scheme\n"
    return subprocess.CompletedProcess(command, 0, output, "")


def test_verify_apk_records_non_operational_evidence(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    evidence = verify_apk(
        apk,
        expected_application_id="br.com.zenit.zenit_mobile",
        expected_version_name="1.0.0",
        expected_version_code="1",
        configured_api_base_url="https://api.example.invalid",
        apkanalyzer_path=_tool(tmp_path / "apkanalyzer"),
        apksigner_path=_tool(tmp_path / "apksigner"),
        runner=_runner,
    )

    payload = json.loads(json.dumps(evidence.__dict__))
    assert payload["artifact_status"] == "demonstration_build"
    assert payload["abis"] == ["arm64-v8a"]
    assert len(payload["sha256"]) == 64
    assert payload["signature_verified"] is True
    assert payload["eligible_for_field_execution"] is False
    assert payload["eligible_for_official_reporting"] is False
    assert payload["eligible_for_model_training"] is False


def test_verify_apk_rejects_incomplete_flutter_archive(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk, omit="assets/flutter_assets/AssetManifest.bin")

    with pytest.raises(ApkVerificationError, match="missing required entries"):
        verify_apk(
            apk,
            expected_application_id="br.com.zenit.zenit_mobile",
            expected_version_name="1.0.0",
            expected_version_code="1",
            configured_api_base_url="https://api.example.invalid",
        )


def test_verify_apk_rejects_operational_api_url(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    with pytest.raises(ApkVerificationError, match=r"reserved \.invalid domain"):
        verify_apk(
            apk,
            expected_application_id="br.com.zenit.zenit_mobile",
            expected_version_name="1.0.0",
            expected_version_code="1",
            configured_api_base_url="https://api.zenit.example.com",
        )


def test_verify_apk_rejects_unexpected_application_id(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    with pytest.raises(ApkVerificationError, match="APK application id"):
        verify_apk(
            apk,
            expected_application_id="br.com.zenit.wrong",
            expected_version_name="1.0.0",
            expected_version_code="1",
            configured_api_base_url="https://api.example.invalid",
            apkanalyzer_path=_tool(tmp_path / "apkanalyzer"),
            apksigner_path=_tool(tmp_path / "apksigner"),
            runner=_runner,
        )
