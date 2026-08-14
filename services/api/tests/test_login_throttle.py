from datetime import UTC, datetime, timedelta

from zenit_api.login_throttle import (
    LoginThrottlePolicy,
    LoginThrottleState,
    advance_login_failure,
)

NOW = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
POLICY = LoginThrottlePolicy(
    version="local-login-throttle-v1",
    attempt_limit=3,
    window=timedelta(minutes=15),
    block_duration=timedelta(minutes=10),
)


def test_login_failure_starts_and_increments_one_window() -> None:
    first = advance_login_failure(None, policy=POLICY, now=NOW)
    second = advance_login_failure(first, policy=POLICY, now=NOW + timedelta(minutes=1))

    assert first == LoginThrottleState(1, NOW, None, POLICY.version)
    assert second == LoginThrottleState(2, NOW, None, POLICY.version)


def test_login_failure_reaching_limit_starts_temporary_block() -> None:
    current = LoginThrottleState(2, NOW, None, POLICY.version)

    state = advance_login_failure(
        current,
        policy=POLICY,
        now=NOW + timedelta(minutes=2),
    )

    assert state.failed_attempt_count == 3
    assert state.window_started_at == NOW
    assert state.blocked_until == NOW + timedelta(minutes=12)


def test_login_failure_after_window_resets_counter() -> None:
    current = LoginThrottleState(2, NOW, None, POLICY.version)
    after_window = NOW + POLICY.window

    state = advance_login_failure(current, policy=POLICY, now=after_window)

    assert state == LoginThrottleState(1, after_window, None, POLICY.version)


def test_login_failure_after_expired_block_starts_new_window() -> None:
    blocked_until = NOW + timedelta(minutes=5)
    current = LoginThrottleState(3, NOW, blocked_until, POLICY.version)
    after_block = blocked_until + timedelta(seconds=1)

    state = advance_login_failure(current, policy=POLICY, now=after_block)

    assert state == LoginThrottleState(1, after_block, None, POLICY.version)


def test_login_failure_under_new_policy_starts_new_window() -> None:
    current = LoginThrottleState(2, NOW, None, "local-login-throttle-v0")
    under_new_policy = NOW + timedelta(minutes=1)

    state = advance_login_failure(current, policy=POLICY, now=under_new_policy)

    assert state == LoginThrottleState(1, under_new_policy, None, POLICY.version)
