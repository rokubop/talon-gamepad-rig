"""Tests for basic stick operations - instant .to(), verify state"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_left_stick_to_right(on_success, on_failure):
    """rig.left_stick.to(1, 0) → full right"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.01, f"Expected x=1.0, got {pos.x}"
            assert abs(pos.y) < 0.01, f"Expected y=0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_left_stick_to_up(on_success, on_failure):
    """rig.left_stick.to(0, 1) → full up"""
    setup()
    r = rig()
    r.left_stick.to(0, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.01, f"Expected x=0, got {pos.x}"
            assert abs(pos.y - 1.0) < 0.01, f"Expected y=1.0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_left_stick_diagonal(on_success, on_failure):
    """rig.left_stick.to(0.5, 0.5) → diagonal"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0.5).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.5) < 0.01, f"Expected x=0.5, got {pos.x}"
            assert abs(pos.y - 0.5) < 0.01, f"Expected y=0.5, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_right_stick_to(on_success, on_failure):
    """rig.right_stick.to(-1, 0) → full left"""
    setup()
    r = rig()
    r.right_stick.to(-1, 0).run()

    def check():
        try:
            pos = r.state.right_stick
            assert abs(pos.x - (-1.0)) < 0.01, f"Expected x=-1.0, got {pos.x}"
            assert abs(pos.y) < 0.01, f"Expected y=0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_left_stick_to_neutral(on_success, on_failure):
    """Set stick then return to neutral"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def set_neutral():
        r.left_stick.to(0, 0).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x) < 0.01, f"Expected x=0, got {pos.x}"
                assert abs(pos.y) < 0.01, f"Expected y=0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, set_neutral)


def test_both_sticks_independent(on_success, on_failure):
    """Left and right sticks are independent"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, -1).run()

    def check():
        try:
            assert abs(r.state.left_stick.x - 1.0) < 0.01, \
                f"Left stick x: expected 1.0, got {r.state.left_stick.x}"
            assert abs(r.state.right_stick.y - (-1.0)) < 0.01, \
                f"Right stick y: expected -1.0, got {r.state.right_stick.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stick_x_axis(on_success, on_failure):
    """rig.left_stick.x.to(0.7) → set x only"""
    setup()
    r = rig()
    r.left_stick.to(0, 0.5).run()
    r.left_stick.x.to(0.7).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.7) < 0.01, f"Expected x=0.7, got {pos.x}"
            assert abs(pos.y - 0.5) < 0.01, f"Expected y=0.5 preserved, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stick_y_axis(on_success, on_failure):
    """rig.left_stick.y.to(-0.3) → set y only"""
    setup()
    r = rig()
    r.left_stick.to(0.8, 0).run()
    r.left_stick.y.to(-0.3).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.8) < 0.01, f"Expected x=0.8 preserved, got {pos.x}"
            assert abs(pos.y - (-0.3)) < 0.01, f"Expected y=-0.3, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


STICK_BASIC_TESTS = [
    ("left_stick.to(right)", test_left_stick_to_right),
    ("left_stick.to(up)", test_left_stick_to_up),
    ("left_stick.to(diagonal)", test_left_stick_diagonal),
    ("right_stick.to(left)", test_right_stick_to),
    ("left_stick to neutral", test_left_stick_to_neutral),
    ("both sticks independent", test_both_sticks_independent),
    ("stick x axis", test_stick_x_axis),
    ("stick y axis", test_stick_y_axis),
]
