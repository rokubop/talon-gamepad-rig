"""Tests for stick lifecycle phases: over → hold → revert — async"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig


def test_hold_maintains_value(on_success, on_failure):
    """to().over(200).hold(300) keeps value during hold phase"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(200).hold(300)

    def check_hold():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.05, f"Expected ~1.0 during hold, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("350ms", check_hold)


def test_revert_returns_to_neutral(on_success, on_failure):
    """to().over(200).hold(200).revert(200) returns to neutral"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(200).hold(200).revert(200)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.1, f"Expected ~0 after revert, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    # over(200) + hold(200) + revert(200) = 600ms total
    cron.after("800ms", check)


def test_revert_without_hold(on_success, on_failure):
    """to().over(200).revert(200) skips hold"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(200).revert(200)

    def check_at_target():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.15, f"Expected ~1.0 before revert, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_reverted)

    def check_reverted():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.1, f"Expected ~0 after revert, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("190ms", check_at_target)


STICK_HOLD_REVERT_TESTS = [
    ("hold maintains value", test_hold_maintains_value),
    ("revert returns to neutral", test_revert_returns_to_neutral),
    ("revert without hold", test_revert_without_hold),
]
