#!/usr/bin/env python3
"""Validate and describe the non-operational ZENIT demonstration APK."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_ENTRIES = (
    "AndroidManifest.xml",
    "classes.dex",
    "resources.arsc",
    "assets/flutter_assets/AssetManifest.bin",
    "assets/flutter_assets/kernel_blob.bin",
)
RunCommand = Callable[..., subprocess.CompletedProcess[str]]


class ApkVerificationError(RuntimeError):
    """Raised when an APK does not meet the demonstrative delivery contract."""


@dataclass(frozen=True)
class ApkEvidence:
    artifact_role: str
    artifact_status: str
    apk_path: str
    sha256: str
    size_bytes: int
    application_id: str
    version_name: str
    version_code: str
    min_sdk: str
    target_sdk: str
    debuggable: bool
    configured_api_base_url: str
    abis: tuple[str, ...]
    signature_verified: bool
    signature_scheme_v2_verified: bool
    signer_certificate_sha256: str
    eligible_for_field_execution: bool
    eligible_for_official_reporting: bool
    eligible_for_model_training: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_key(path: Path) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in path.parent.name.split("."))


def _find_sdk_tool(name: str, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        candidates = (explicit_path,)
    else:
        discovered = shutil.which(name)
        candidates: tuple[Path, ...] = (Path(discovered),) if discovered else ()
        for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
            sdk_value = os.environ.get(variable)
            if not sdk_value:
                continue
            sdk_root = Path(sdk_value)
            if name == "apkanalyzer":
                candidates += tuple(
                    sorted(
                        sdk_root.glob("cmdline-tools/*/bin/apkanalyzer"),
                        reverse=True,
                    )
                )
            elif name == "apksigner":
                candidates += tuple(
                    sorted(
                        sdk_root.glob("build-tools/*/apksigner"),
                        key=_version_key,
                        reverse=True,
                    )
                )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise ApkVerificationError(
        f"required Android SDK tool '{name}' was not found; set ANDROID_HOME or pass its path"
    )


def _run_tool(
    command: Sequence[str | Path],
    *,
    name: str,
    runner: RunCommand,
) -> str:
    result = runner(
        [str(part) for part in command],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
        raise ApkVerificationError(f"{name} failed: {detail}")
    return result.stdout.strip()


def _validate_demo_api_base_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname is None:
        raise ApkVerificationError("configured API base URL must use HTTPS")
    if parsed.hostname != "invalid" and not parsed.hostname.endswith(".invalid"):
        raise ApkVerificationError(
            "configured API base URL must use the reserved .invalid domain for this demo artifact"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ApkVerificationError(
            "configured API base URL must not contain credentials or metadata"
        )


def _inspect_archive(apk_path: Path, configured_api_base_url: str) -> tuple[str, ...]:
    try:
        with zipfile.ZipFile(apk_path) as archive:
            entries = archive.namelist()
            entry_set = set(entries)
            if len(entries) != len(entry_set):
                raise ApkVerificationError("APK contains duplicate archive entries")
            missing = [entry for entry in REQUIRED_ENTRIES if entry not in entry_set]
            if missing:
                raise ApkVerificationError(
                    f"APK is missing required entries: {', '.join(missing)}"
                )
            unsafe = [
                entry
                for entry in entries
                if entry.startswith(("/", "\\")) or ".." in Path(entry).parts
            ]
            if unsafe:
                raise ApkVerificationError(f"APK contains unsafe entry path: {unsafe[0]}")
            kernel_blob = archive.read("assets/flutter_assets/kernel_blob.bin")
            if configured_api_base_url.encode() not in kernel_blob:
                raise ApkVerificationError(
                    "APK Flutter kernel does not contain the configured demonstration API URL"
                )
            abis = sorted(
                {
                    parts[1]
                    for entry in entries
                    if len(parts := Path(entry).parts) == 3
                    and parts[0] == "lib"
                    and parts[2] == "libflutter.so"
                }
            )
    except zipfile.BadZipFile as exc:
        raise ApkVerificationError("APK is not a valid ZIP archive") from exc
    if not abis:
        raise ApkVerificationError("APK does not contain a Flutter engine native library")
    return tuple(abis)


def _signature_value(output: str, label: str) -> str:
    prefix = f"{label}:"
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    raise ApkVerificationError(f"APK signature output is missing {label!r}")


def verify_apk(
    apk_path: Path,
    *,
    expected_application_id: str,
    expected_version_name: str,
    expected_version_code: str,
    expected_min_sdk: str,
    expected_target_sdk: str,
    configured_api_base_url: str,
    apkanalyzer_path: Path | None = None,
    apksigner_path: Path | None = None,
    runner: RunCommand = subprocess.run,
) -> ApkEvidence:
    if not apk_path.is_file():
        raise ApkVerificationError(f"APK does not exist: {apk_path}")
    if apk_path.stat().st_size == 0:
        raise ApkVerificationError("APK is empty")
    _validate_demo_api_base_url(configured_api_base_url)
    abis = _inspect_archive(apk_path, configured_api_base_url)

    apkanalyzer = _find_sdk_tool("apkanalyzer", apkanalyzer_path)
    apksigner = _find_sdk_tool("apksigner", apksigner_path)
    application_id = _run_tool(
        (apkanalyzer, "manifest", "application-id", apk_path),
        name="APK application-id inspection",
        runner=runner,
    )
    version_name = _run_tool(
        (apkanalyzer, "manifest", "version-name", apk_path),
        name="APK version-name inspection",
        runner=runner,
    )
    version_code = _run_tool(
        (apkanalyzer, "manifest", "version-code", apk_path),
        name="APK version-code inspection",
        runner=runner,
    )
    min_sdk = _run_tool(
        (apkanalyzer, "manifest", "min-sdk", apk_path),
        name="APK min-sdk inspection",
        runner=runner,
    )
    target_sdk = _run_tool(
        (apkanalyzer, "manifest", "target-sdk", apk_path),
        name="APK target-sdk inspection",
        runner=runner,
    )
    debuggable = _run_tool(
        (apkanalyzer, "manifest", "debuggable", apk_path),
        name="APK debuggable inspection",
        runner=runner,
    )
    expected = {
        "application id": (application_id, expected_application_id),
        "version name": (version_name, expected_version_name),
        "version code": (version_code, expected_version_code),
        "minimum SDK": (min_sdk, expected_min_sdk),
        "target SDK": (target_sdk, expected_target_sdk),
        "debuggable flag": (debuggable, "true"),
    }
    for label, (actual, expected_value) in expected.items():
        if actual != expected_value:
            raise ApkVerificationError(
                f"APK {label} is {actual!r}; expected {expected_value!r}"
            )

    signature_output = _run_tool(
        (apksigner, "verify", "--verbose", "--print-certs", apk_path),
        name="APK signature verification",
        runner=runner,
    )
    if _signature_value(signature_output, "Verified using v2 scheme (APK Signature Scheme v2)") != (
        "true"
    ):
        raise ApkVerificationError("APK signature does not use the required v2 scheme")
    if _signature_value(signature_output, "Number of signers") != "1":
        raise ApkVerificationError("APK must have exactly one debug signer")
    signer_dn = _signature_value(signature_output, "Signer #1 certificate DN")
    if signer_dn != "C=US, O=Android, CN=Android Debug":
        raise ApkVerificationError(
            f"APK signer is not the expected Android debug signer: {signer_dn}"
        )
    signer_certificate_sha256 = _signature_value(
        signature_output, "Signer #1 certificate SHA-256 digest"
    )
    if len(signer_certificate_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in signer_certificate_sha256
    ):
        raise ApkVerificationError("APK signer certificate SHA-256 digest is invalid")
    return ApkEvidence(
        artifact_role="zenit_mvp_demonstration_android_debug_apk",
        artifact_status="demonstration_build",
        apk_path=str(apk_path),
        sha256=_sha256(apk_path),
        size_bytes=apk_path.stat().st_size,
        application_id=application_id,
        version_name=version_name,
        version_code=version_code,
        min_sdk=min_sdk,
        target_sdk=target_sdk,
        debuggable=True,
        configured_api_base_url=configured_api_base_url,
        abis=abis,
        signature_verified=True,
        signature_scheme_v2_verified=True,
        signer_certificate_sha256=signer_certificate_sha256,
        eligible_for_field_execution=False,
        eligible_for_official_reporting=False,
        eligible_for_model_training=False,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--expected-application-id", required=True)
    parser.add_argument("--expected-version-name", required=True)
    parser.add_argument("--expected-version-code", required=True)
    parser.add_argument("--expected-min-sdk", required=True)
    parser.add_argument("--expected-target-sdk", required=True)
    parser.add_argument("--configured-api-base-url", required=True)
    parser.add_argument("--apkanalyzer", type=Path)
    parser.add_argument("--apksigner", type=Path)
    parser.add_argument("--evidence-out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evidence = verify_apk(
            args.apk,
            expected_application_id=args.expected_application_id,
            expected_version_name=args.expected_version_name,
            expected_version_code=args.expected_version_code,
            expected_min_sdk=args.expected_min_sdk,
            expected_target_sdk=args.expected_target_sdk,
            configured_api_base_url=args.configured_api_base_url,
            apkanalyzer_path=args.apkanalyzer,
            apksigner_path=args.apksigner,
        )
    except ApkVerificationError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    serialized = json.dumps(asdict(evidence), indent=2, sort_keys=True) + "\n"
    if args.evidence_out is not None:
        args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
        args.evidence_out.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
