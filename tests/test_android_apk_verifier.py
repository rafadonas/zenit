from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest
from scripts.verify_android_apk import ApkVerificationError, _debug_signer_sha256, verify_apk

DEBUG_DN = "C=US, O=Android, CN=Android Debug"
SDK_SIGNERS = (
    "Signer (minSdkVersion=33, maxSdkVersion=2147483647)",
    "Signer (minSdkVersion=24, maxSdkVersion=32)",
)
DEV_RELEASE_SIGNERS = (
    "Signer (minSdkVersion=33 (dev release=true), maxSdkVersion=2147483647)",
    "Signer (minSdkVersion=33, maxSdkVersion=2147483647 (dev release=true))",
    "Signer (minSdkVersion=33, maxSdkVersion=2147483647) (dev release=true)",
)


def _certificate(signer: str, *, dn: str = DEBUG_DN, digest: str = "a" * 64) -> str:
    return f"{signer} certificate DN: {dn}\n{signer} certificate SHA-256 digest: {digest}"


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


@pytest.mark.parametrize(
    "signers",
    [
        ("Signer #1",),
        SDK_SIGNERS,
        *((signer,) for signer in DEV_RELEASE_SIGNERS),
    ],
)
@pytest.mark.parametrize("dn", [DEBUG_DN, "CN=Android Debug, O=Android, C=US"])
def test_verify_apk_records_non_operational_evidence(
    tmp_path: Path, signers: tuple[str, ...], dn: str
) -> None:
    apk = tmp_path / "app-debug.apk"
    _write_apk(apk)

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = _runner(command, **kwargs)
        if "verify" in command:
            assert "--verbose" in command and "--print-certs" in command
            result.stdout = "\n".join(
                (
                    "Verifies",
                    "Verified using v2 scheme (APK Signature Scheme v2): true",
                    "Verified using v3.1 scheme (APK Signature Scheme v3.1): true",
                    "Number of signers: 1",
                    *(_certificate(signer, dn=dn) for signer in signers),
                    _certificate("Source Stamp Signer", dn="CN=Unrelated", digest="b" * 64),
                )
            )
        return result

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
        runner=runner,
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


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("", "missing signer certificate details"),
        (_certificate("Source Stamp Signer"), "missing signer certificate details"),
        (f"Signer #1 certificate DN: {DEBUG_DN}", "missing Signer #1 certificate fields"),
        ("Signer #1 certificate SHA-256 digest: " + "a" * 64, "missing Signer #1 certificate"),
        (_certificate("Signer #2"), "exactly one debug signer"),
        (_certificate("Signer #1", dn="CN=Release, O=Android, C=US"), "expected Android debug"),
        (_certificate("Signer #1", dn=DEBUG_DN + ", C=US"), "expected Android debug"),
        (_certificate("Signer #1", digest="g" * 64), "SHA-256 digest is invalid"),
        (_certificate("Signer #1", digest="a" * 63), "SHA-256 digest is invalid"),
        (_certificate("Signer #1") + "\n" + _certificate("Signer #1"), "repeats Signer #1"),
        (
            _certificate(SDK_SIGNERS[0]) + "\n" + _certificate(SDK_SIGNERS[1], digest="b" * 64),
            "same debug certificate for every SDK range",
        ),
        (
            _certificate("Signer #1") + "\n" + _certificate(SDK_SIGNERS[0]),
            "mixes numbered and SDK-targeted signers",
        ),
        (
            _certificate(SDK_SIGNERS[0]) + f"\n{SDK_SIGNERS[1]} certificate DN: {DEBUG_DN}",
            "missing .* certificate fields",
        ),
    ],
)
def test_signer_certificate_parser_rejects_incomplete_or_ambiguous_evidence(
    output: str, message: str
) -> None:
    with pytest.raises(ApkVerificationError, match=message):
        _debug_signer_sha256(output)


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
