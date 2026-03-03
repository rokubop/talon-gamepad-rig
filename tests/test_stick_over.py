"""Tests for stick .over() interpolation - async, uses real cron timing"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_over_interpolates(on_success, on_failure):
    """rig.left_stick.to(1, 0).over(300) → interpolates over time"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(300)

    def check_mid():
        try:
            pos = r.state.left_stick
            assert 0.2 < pos.x < 0.9, f"Expected mid-interpolation, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_end)

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.05, f"Expected ~1.0, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        def done():
            teardown()
            on_success()
        cron.after(VISIBLE_MS, done)

    cron.after("150ms", check_mid)


def test_over_starts_from_current(on_success, on_failure):
    """Interpolation starts from current position"""
    setup()
    r = rig()
    r.left_stick.to(-0.5, 0).run()

    def start_transition():
        r.left_stick.to(0.5, 0).over(300)
        cron.after("150ms", check_mid)

    def check_mid():
        try:
            pos = r.state.left_stick
            assert -0.6 < pos.x < 0.6, f"Expected mid-transition, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_end)

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.5) < 0.05, f"Expected ~0.5, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        def done():
            teardown()
            on_success()
        cron.after(VISIBLE_MS, done)

    cron.after(VISIBLE_MS, start_transition)


def test_over_completes_at_target(on_success, on_failure):
    """After .over() duration, value should be at target"""
    setup()
    r = rig()
    r.left_stick.to(0, 0.8).over(200)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.y - 0.8) < 0.05, f"Expected ~0.8, got {pos.y}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        def done():
            teardown()
            on_success()
        cron.after(VISIBLE_MS, done)

    cron.after("400ms", check)


def test_over_right_stick(on_success, on_failure):
    """right_stick.to() with .over()"""
    setup()
    r = rig()
    r.right_stick.to(0, -1).over(200)

    def check():
        try:
            pos = r.state.right_stick
            assert abs(pos.y - (-1.0)) < 0.05, f"Expected ~-1.0, got {pos.y}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        def done():
            teardown()
            on_success()
        cron.after(VISIBLE_MS, done)

    cron.after("400ms", check)


STICK_OVER_TESTS = [
    ("over interpolates", test_over_interpolates),
    ("over starts from current", test_over_starts_from_current),
    ("over completes at target", test_over_completes_at_target),
    ("over right stick", test_over_right_stick),
]
