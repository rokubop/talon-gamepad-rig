"""Tests for trigger set/release/interpolation"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_left_trigger_set(on_success, on_failure):
    """rig.left_trigger.to(1) → full press"""
    setup()
    r = rig()
    r.left_trigger.to(1).run()

    def check():
        try:
            assert abs(r.state.left_trigger - 1.0) < 0.01, \
                f"Expected 1.0, got {r.state.left_trigger}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_right_trigger_set(on_success, on_failure):
    """rig.right_trigger.to(0.5) → half press"""
    setup()
    r = rig()
    r.right_trigger.to(0.5).run()

    def check():
        try:
            assert abs(r.state.right_trigger - 0.5) < 0.01, \
                f"Expected 0.5, got {r.state.right_trigger}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_release(on_success, on_failure):
    """Set trigger then release to 0"""
    setup()
    r = rig()
    r.left_trigger.to(1).run()

    def release():
        r.left_trigger.to(0).run()

        def check():
            try:
                assert abs(r.state.left_trigger) < 0.01, \
                    f"Expected 0, got {r.state.left_trigger}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, release)


def test_trigger_over(on_success, on_failure):
    """rig.left_trigger.to(1).over(100) → interpolates"""
    setup()
    r = rig()
    r.left_trigger.to(1).over(100)

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 1.0) < 0.05, f"Expected ~1.0, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("400ms", check)


def test_trigger_hold_revert(on_success, on_failure):
    """trigger.to(1).over(80).hold(200).revert(80)"""
    setup()
    r = rig()
    r.left_trigger.to(1).over(80).hold(200).revert(80)

    def check_hold():
        try:
            val = r.state.left_trigger
            assert abs(val - 1.0) < 0.1, f"Expected ~1.0 during hold, got {val}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_revert)

    def check_revert():
        try:
            val = r.state.left_trigger
            assert val < 0.1, f"Expected ~0 after revert, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("150ms", check_hold)


def test_triggers_independent(on_success, on_failure):
    """Left and right triggers are independent"""
    setup()
    r = rig()
    r.left_trigger.to(0.3).run()
    r.right_trigger.to(0.9).run()

    def check():
        try:
            assert abs(r.state.left_trigger - 0.3) < 0.01
            assert abs(r.state.right_trigger - 0.9) < 0.01
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


TRIGGER_TESTS = [
    ("left trigger set", test_left_trigger_set),
    ("right trigger set", test_right_trigger_set),
    ("trigger release", test_trigger_release),
    ("trigger over", test_trigger_over),
    ("trigger hold revert", test_trigger_hold_revert),
    ("triggers independent", test_triggers_independent),
]
