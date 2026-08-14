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
        "assets/flutter_assets/kernel_blob.bin": b"https://api.example.invalid",
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
    elif "min-sdk" in command:
        output = "24\n"
    elif "target-sdk" in command:
        output = "36\n"
    elif "debuggable" in command:
        output = "true\n"
    else:
        output = "\n".join(
            (
                "Verifies",
                "Verified using v2 scheme (APK Signature Scheme v2): true",
                "Number of signers: 1",
                "Signer #1 certificate DN: C=US, O=Android, CN=Android Debug",
                "Signer #1 certificate SHA-256 digest: " + "a" * 64,
            )
        )
    return subprocess.CompletedProcess(command, 0, output, "")


def test_verify_apk_records_non_operational_evidence(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    evidence = verify_apk(
        apk,
        expected_application_id="br.com.zenit.zenit_mobile",
        expected_version_name="1.0.0",
        expected_version_code="1",
        expected_min_sdk="24",
        expected_target_sdk="36",
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
    assert payload["signature_scheme_v2_verified"] is True
    assert payload["signer_certificate_sha256"] == "a" * 64
    assert payload["min_sdk"] == "24"
    assert payload["target_sdk"] == "36"
    assert payload["debuggable"] is True
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
            expected_min_sdk="24",
            expected_target_sdk="36",
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
            expected_min_sdk="24",
            expected_target_sdk="36",
            configured_api_base_url="https://api.zenit.example.com",
        )


def test_verify_apk_rejects_demo_url_missing_from_flutter_kernel(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    with pytest.raises(ApkVerificationError, match="kernel does not contain"):
        verify_apk(
            apk,
            expected_application_id="br.com.zenit.zenit_mobile",
            expected_version_name="1.0.0",
            expected_version_code="1",
            expected_min_sdk="24",
            expected_target_sdk="36",
            configured_api_base_url="https://other.invalid",
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
            expected_min_sdk="24",
            expected_target_sdk="36",
            configured_api_base_url="https://api.example.invalid",
            apkanalyzer_path=_tool(tmp_path / "apkanalyzer"),
            apksigner_path=_tool(tmp_path / "apksigner"),
            runner=_runner,
        )


def test_verify_apk_rejects_signature_without_v2_scheme(tmp_path: Path) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = _runner(command, **kwargs)
        if "verify" in command:
            result.stdout = result.stdout.replace(
                "Verified using v2 scheme (APK Signature Scheme v2): true",
                "Verified using v2 scheme (APK Signature Scheme v2): false",
            )
        return result

    with pytest.raises(ApkVerificationError, match="required v2 scheme"):
        verify_apk(
            apk,
            expected_application_id="br.com.zenit.zenit_mobile",
            expected_version_name="1.0.0",
            expected_version_code="1",
            expected_min_sdk="24",
            expected_target_sdk="36",
            configured_api_base_url="https://api.example.invalid",
            apkanalyzer_path=_tool(tmp_path / "apkanalyzer"),
            apksigner_path=_tool(tmp_path / "apksigner"),
            runner=runner,
        )
