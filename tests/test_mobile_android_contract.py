from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID_APP = ROOT / "apps/mobile/android/app"


def test_android_build_uses_current_flutter_sdk_contract_without_release_debug_signing() -> None:
    build_config = (ANDROID_APP / "build.gradle.kts").read_text(encoding="utf-8")

    assert 'applicationId = "br.com.zenit.zenit_mobile"' in build_config
    assert "minSdk = flutter.minSdkVersion" in build_config
    assert "targetSdk = flutter.targetSdkVersion" in build_config
    assert "signingConfigs.getByName(\"debug\")" not in build_config


def test_cleartext_traffic_is_limited_to_debug_manifest() -> None:
    main_manifest = (ANDROID_APP / "src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    debug_manifest = (ANDROID_APP / "src/debug/AndroidManifest.xml").read_text(encoding="utf-8")

    assert "usesCleartextTraffic" not in main_manifest
    assert 'android:usesCleartextTraffic="true"' in debug_manifest


def test_ci_verifies_only_the_reserved_non_operational_debug_apk() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "flutter build apk --debug" in workflow
    assert "ZENIT_API_BASE_URL=https://api.example.invalid" in workflow
    assert "python ../../scripts/verify_android_apk.py" in workflow
    assert workflow.index("flutter build apk --debug") < workflow.index(
        "python ../../scripts/verify_android_apk.py"
    )
    assert "flutter build apk --release" not in workflow
