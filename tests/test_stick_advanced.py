"""Advanced stick tests - magnitude, direction subproperties, easing, callbacks, relative ops"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


# ============================================================================
# MAGNITUDE SUBPROPERTY
# ============================================================================

def test_stick_magnitude_to(on_success, on_failure):
    """magnitude.to(0.5) sets magnitude while preserving direction"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.magnitude.to(0.5).run()

    def check():
        try:
            pos = r.state.left_stick
            mag = (pos.x ** 2 + pos.y ** 2) ** 0.5
            assert abs(mag - 0.5) < 0.05, f"Expected magnitude~0.5, got {mag}"
            assert pos.x > 0, f"Expected direction preserved (x>0), got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stick_magnitude_to_over(on_success, on_failure):
    """magnitude.to(0.5).over(300) animates magnitude change"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.magnitude.to(0.3).over(300)

    def check_mid():
        try:
            pos = r.state.left_stick
            mag = (pos.x ** 2 + pos.y ** 2) ** 0.5
            assert 0.3 < mag < 1.0, f"Expected mid-transition magnitude, got {mag}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_end)

    def check_end():
        try:
            pos = r.state.left_stick
            mag = (pos.x ** 2 + pos.y ** 2) ** 0.5
            assert abs(mag - 0.3) < 0.1, f"Expected magnitude~0.3, got {mag}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("150ms", check_mid)


def test_stick_magnitude_preserves_direction(on_success, on_failure):
    """magnitude.to() preserves diagonal direction"""
    setup()
    r = rig()
    r.left_stick.to(0.7, 0.7).run()
    r.left_stick.magnitude.to(0.5).run()

    def check():
        try:
            pos = r.state.left_stick
            mag = (pos.x ** 2 + pos.y ** 2) ** 0.5
            assert abs(mag - 0.5) < 0.05, f"Expected magnitude~0.5, got {mag}"
            # Direction should still be ~45 degrees (x ≈ y)
            assert abs(pos.x - pos.y) < 0.1, f"Expected x≈y, got x={pos.x}, y={pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# RELATIVE OPERATIONS (add/by/sub)
# ============================================================================

def test_stick_add(on_success, on_failure):
    """left_stick.add(0.3, 0) adds to current position"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.left_stick.add(0.3, 0).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.8) < 0.05, f"Expected 0.5+0.3=0.8, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stick_add_over(on_success, on_failure):
    """left_stick.add(0.5, 0).over(300) animates relative movement"""
    setup()
    r = rig()
    r.left_stick.to(0.3, 0).run()
    r.left_stick.add(0.5, 0).over(300)

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.8) < 0.1, f"Expected 0.3+0.5=0.8, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


def test_stick_add_negative(on_success, on_failure):
    """left_stick.add(-0.3, 0) subtracts from current position"""
    setup()
    r = rig()
    r.left_stick.to(0.8, 0).run()
    r.left_stick.add(-0.3, 0).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.5) < 0.05, f"Expected 0.8-0.3=0.5, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# AXIS SUBPROPERTIES WITH ANIMATION
# ============================================================================

def test_stick_x_to_over(on_success, on_failure):
    """x.to(0.8).over(300) animates X axis only"""
    setup()
    r = rig()
    r.left_stick.to(0, 0.5).run()
    r.left_stick.x.to(0.8).over(300)

    def check_end():
        try:
            pos = r.state.left_stick
            # (0.8, 0.5) magnitude ~0.94, within unit circle
            assert abs(pos.x - 0.8) < 0.1, f"Expected x~0.8, got {pos.x}"
            assert abs(pos.y - 0.5) < 0.1, f"Expected y preserved ~0.5, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


def test_stick_y_to_over(on_success, on_failure):
    """y.to(-0.8).over(300) animates Y axis only"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.left_stick.y.to(-0.8).over(300)

    def check_end():
        try:
            pos = r.state.left_stick
            # (0.5, -0.8) magnitude ~0.94, within unit circle
            assert abs(pos.x - 0.5) < 0.1, f"Expected x preserved ~0.5, got {pos.x}"
            assert abs(pos.y - (-0.8)) < 0.1, f"Expected y~-0.8, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


# ============================================================================
# CALLBACKS / THEN
# ============================================================================

def test_stick_over_then_callback(on_success, on_failure):
    """Callback fires when .over() transition completes"""
    setup()
    r = rig()
    callback_fired = {"value": False}

    def on_done():
        callback_fired["value"] = True

    r.left_stick.to(1, 0).over(200).then(on_done)

    def check():
        try:
            assert callback_fired["value"], "Callback was not fired"
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.1, f"Expected x~1.0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_stick_lifecycle_callbacks(on_success, on_failure):
    """Callbacks fire in order: over.then() → hold.then() → revert.then()"""
    setup()
    r = rig()
    callback_order = []

    def after_over():
        callback_order.append("over")

    def after_hold():
        callback_order.append("hold")

    def after_revert():
        callback_order.append("revert")

    r.left_stick.to(1, 0).over(150).then(after_over).hold(150).then(after_hold).revert(150).then(after_revert)

    def check():
        try:
            expected = ["over", "hold", "revert"]
            assert callback_order == expected, f"Expected {expected}, got {callback_order}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("800ms", check)


# ============================================================================
# EASING FUNCTIONS
# ============================================================================

def test_stick_over_with_easing(on_success, on_failure):
    """over(300, 'ease_in2') applies easing to transition"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(300, "ease_in2")

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.1, f"Expected x~1.0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


def test_stick_revert_with_easing(on_success, on_failure):
    """revert(300, 'ease_out2') applies easing to revert"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).hold(200).revert(300, "ease_out2")

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.1, f"Expected x~0 after revert, got {pos.x}"
            assert abs(pos.y) < 0.1, f"Expected y~0 after revert, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("800ms", check_end)


# ============================================================================
# CLAMPING
# ============================================================================

def test_stick_clamps_to_unit_circle(on_success, on_failure):
    """Values beyond unit circle are normalized to magnitude 1"""
    setup()
    r = rig()
    r.left_stick.to(1, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            mag = (pos.x ** 2 + pos.y ** 2) ** 0.5
            assert abs(mag - 1.0) < 0.05, f"Expected magnitude ~1.0, got {mag}"
            # Direction preserved: x ≈ y ≈ 0.707
            assert abs(pos.x - 0.707) < 0.05, f"Expected x ~0.707, got {pos.x}"
            assert abs(pos.y - 0.707) < 0.05, f"Expected y ~0.707, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_clamps_0_to_1(on_success, on_failure):
    """Trigger values clamped to [0, 1]"""
    setup()
    r = rig()
    r.left_trigger.to(1.5).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 1.0) < 0.01, f"Expected clamped to 1.0, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# STATE CLEANUP AFTER LIFECYCLE
# ============================================================================

def test_state_cleanup_after_lifecycle(on_success, on_failure):
    """Frame loop stops and builders cleared after full lifecycle completes"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(100).hold(100).revert(100)

    def check():
        try:
            assert r.state._frame_loop_job is None, "Frame loop should be stopped"
            pos = r.state.left_stick
            assert abs(pos.x) < 0.1, f"Expected x~0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("600ms", check)


# ============================================================================
# TEST REGISTRY
# ============================================================================

STICK_ADVANCED_TESTS = [
    ("magnitude.to()", test_stick_magnitude_to),
    ("magnitude.to().over()", test_stick_magnitude_to_over),
    ("magnitude preserves direction", test_stick_magnitude_preserves_direction),
    ("stick.add()", test_stick_add),
    ("stick.add().over()", test_stick_add_over),
    ("stick.add() negative", test_stick_add_negative),
    ("x.to().over()", test_stick_x_to_over),
    ("y.to().over()", test_stick_y_to_over),
    ("over().then() callback", test_stick_over_then_callback),
    ("lifecycle callbacks order", test_stick_lifecycle_callbacks),
    ("over() with easing", test_stick_over_with_easing),
    ("revert() with easing", test_stick_revert_with_easing),
    ("stick clamps to unit circle", test_stick_clamps_to_unit_circle),
    ("trigger clamps 0-1", test_trigger_clamps_0_to_1),
    ("state cleanup after lifecycle", test_state_cleanup_after_lifecycle),
]
