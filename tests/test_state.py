"""Tests for state queries returning correct values"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_state_left_stick(on_success, on_failure):
    """state.left_stick returns current computed position"""
    setup()
    r = rig()
    r.left_stick.to(0.7, -0.3).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.7) < 0.01, f"Expected x=0.7, got {pos.x}"
            assert abs(pos.y - (-0.3)) < 0.01, f"Expected y=-0.3, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_state_right_stick(on_success, on_failure):
    """state.right_stick returns current computed position"""
    setup()
    r = rig()
    r.right_stick.to(-0.5, 0.5).run()

    def check():
        try:
            pos = r.state.right_stick
            assert abs(pos.x - (-0.5)) < 0.01, f"Expected x=-0.5, got {pos.x}"
            assert abs(pos.y - 0.5) < 0.01, f"Expected y=0.5, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_state_triggers(on_success, on_failure):
    """state.left_trigger and right_trigger return correct values"""
    setup()
    r = rig()
    r.left_trigger.to(0.4).run()
    r.right_trigger.to(0.8).run()

    def check():
        try:
            assert abs(r.state.left_trigger - 0.4) < 0.01
            assert abs(r.state.right_trigger - 0.8) < 0.01
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_state_with_user_layer(on_success, on_failure):
    """User layers appear in state.layers"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").offset.left_stick.to(0.2, 0).run()

    def check():
        try:
            layers = r.state.layers
            assert "aim" in layers, f"Expected 'aim' in {layers}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_frame_loop_stops_when_idle(on_success, on_failure):
    """Frame loop stops when no builders are active (instant op)"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def check():
        try:
            assert r.state._frame_loop_job is None, \
                "Frame loop should not start for instant builder"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


STATE_TESTS = [
    ("state left stick", test_state_left_stick),
    ("state right stick", test_state_right_stick),
    ("state triggers", test_state_triggers),
    ("state with user layer", test_state_with_user_layer),
    ("frame loop stops when idle", test_frame_loop_stops_when_idle),
]
