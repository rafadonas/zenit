#!/usr/bin/env python3
"""Validate tracked evidence for the non-operational Android MVP artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
REVISION_PATTERN = re.compile(r"[0-9a-f]{7,40}")
EXPECTED_ABIS = ["arm64-v8a", "armeabi-v7a", "x86_64"]
EXPECTED_GENERATED_PATH = "apps/mobile/build/app/outputs/flutter-apk/app-debug.apk"


class ReleaseEvidenceError(RuntimeError):
    """Raised when tracked release evidence violates the MVP contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseEvidenceError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_manifest(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except OSError as exc:
        raise ReleaseEvidenceError(f"cannot read evidence manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseEvidenceError(f"invalid evidence JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping):
        raise ReleaseEvidenceError("evidence root must be a JSON object")
    return payload


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleaseEvidenceError(f"{name} must be a JSON object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], name: str) -> None:
    missing = expected - value.keys()
    unknown = value.keys() - expected
    if missing:
        raise ReleaseEvidenceError(f"{name} is missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ReleaseEvidenceError(f"{name} has unknown keys: {', '.join(sorted(unknown))}")


def _expect(value: Any, expected: Any, name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ReleaseEvidenceError(f"{name} must be {expected!r}")


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseEvidenceError(f"{name} must be a non-empty string")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_demo_url(value: Any) -> None:
    url = _nonempty_string(value, "build.configured_api_base_url")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname is None:
        raise ReleaseEvidenceError("build.configured_api_base_url must use HTTPS")
    if parsed.hostname != "invalid" and not parsed.hostname.endswith(".invalid"):
        raise ReleaseEvidenceError(
            "build.configured_api_base_url must use the reserved .invalid domain"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ReleaseEvidenceError(
            "build.configured_api_base_url must not contain credentials or metadata"
        )


def verify_release_evidence(
    manifest_path: Path,
    *,
    artifact_path: Path | None = None,
) -> Mapping[str, Any]:
    payload = _load_manifest(manifest_path)
    _exact_keys(
        payload,
        {"schema_version", "assessment_date", "artifact", "build", "scope", "verification"},
        "evidence",
    )
    _expect(payload["schema_version"], 1, "schema_version")
    assessment_date = _nonempty_string(payload["assessment_date"], "assessment_date")
    try:
        if date.fromisoformat(assessment_date).isoformat() != assessment_date:
            raise ValueError
    except ValueError as exc:
        raise ReleaseEvidenceError("assessment_date must use YYYY-MM-DD") from exc

    artifact = _object(payload["artifact"], "artifact")
    _exact_keys(
        artifact,
        {
            "abis",
            "application_id",
            "artifact_role",
            "artifact_status",
            "committed",
            "debuggable",
            "generated_path",
            "min_sdk",
            "sha256",
            "signature_scheme_v2_verified",
            "signature_verified",
            "signer_certificate_sha256",
            "size_bytes",
            "target_sdk",
            "version_code",
            "version_name",
        },
        "artifact",
    )
    expected_artifact_values = {
        "abis": EXPECTED_ABIS,
        "application_id": "br.com.zenit.zenit_mobile",
        "artifact_role": "zenit_mvp_demonstration_android_debug_apk",
        "artifact_status": "demonstration_build",
        "committed": False,
        "debuggable": True,
        "generated_path": EXPECTED_GENERATED_PATH,
        "min_sdk": 24,
        "signature_scheme_v2_verified": True,
        "signature_verified": True,
        "target_sdk": 36,
        "version_code": 1,
        "version_name": "1.0.0",
    }
    for key, expected in expected_artifact_values.items():
        _expect(artifact[key], expected, f"artifact.{key}")
    for key in ("sha256", "signer_certificate_sha256"):
        value = _nonempty_string(artifact[key], f"artifact.{key}")
        if SHA256_PATTERN.fullmatch(value) is None:
            raise ReleaseEvidenceError(f"artifact.{key} must be a lowercase SHA-256 digest")
    size_bytes = artifact["size_bytes"]
    if type(size_bytes) is not int or size_bytes <= 0:
        raise ReleaseEvidenceError("artifact.size_bytes must be a positive integer")

    build = _object(payload["build"], "build")
    _exact_keys(
        build,
        {
            "android_build_tools",
            "android_ndk",
            "android_platform",
            "configured_api_base_url",
            "flutter",
            "jdk",
            "source_revision",
            "source_worktree_clean",
        },
        "build",
    )
    for key in ("android_build_tools", "android_ndk", "flutter", "jdk"):
        _nonempty_string(build[key], f"build.{key}")
    _expect(build["android_platform"], artifact["target_sdk"], "build.android_platform")
    _expect(build["source_worktree_clean"], True, "build.source_worktree_clean")
    _validate_demo_url(build["configured_api_base_url"])
    source_revision = _nonempty_string(build["source_revision"], "build.source_revision")
    if REVISION_PATTERN.fullmatch(source_revision) is None:
        raise ReleaseEvidenceError("build.source_revision must be a lowercase Git revision")

    scope = _object(payload["scope"], "scope")
    scope_keys = {
        "eligible_for_field_execution",
        "eligible_for_model_training",
        "eligible_for_official_reporting",
        "operational_release",
    }
    _exact_keys(scope, scope_keys, "scope")
    for key in scope_keys:
        _expect(scope[key], False, f"scope.{key}")

    verification = _object(payload["verification"], "verification")
    _exact_keys(
        verification,
        {"configured_url_found_in_flutter_kernel", "passed", "verifier", "verifier_revision"},
        "verification",
    )
    _expect(
        verification["configured_url_found_in_flutter_kernel"],
        True,
        "verification.configured_url_found_in_flutter_kernel",
    )
    _expect(verification["passed"], True, "verification.passed")
    _expect(verification["verifier"], "scripts/verify_android_apk.py", "verification.verifier")
    _expect(verification["verifier_revision"], source_revision, "verification.verifier_revision")

    if artifact_path is not None:
        if not artifact_path.is_file():
            raise ReleaseEvidenceError(f"APK does not exist: {artifact_path}")
        if artifact_path.stat().st_size != size_bytes:
            raise ReleaseEvidenceError("APK size does not match tracked evidence")
        if _sha256(artifact_path) != artifact["sha256"]:
            raise ReleaseEvidenceError("APK SHA-256 does not match tracked evidence")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--artifact", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = verify_release_evidence(args.manifest, artifact_path=args.artifact)
    except ReleaseEvidenceError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    artifact = _object(payload["artifact"], "artifact")
    print(f"OK {args.manifest}: {artifact['sha256']} ({artifact['size_bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
