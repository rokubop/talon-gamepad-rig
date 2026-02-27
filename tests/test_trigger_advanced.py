"""Advanced trigger tests - relative ops, layers, callbacks, easing, lifecycle"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


# ============================================================================
# RELATIVE OPERATIONS
# ============================================================================

def test_trigger_add(on_success, on_failure):
    """left_trigger.add(0.3) adds to current value"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()
    r.left_trigger.add(0.3).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.8) < 0.05, f"Expected 0.5+0.3=0.8, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_add_over(on_success, on_failure):
    """left_trigger.add(0.4).over(300) animates relative change"""
    setup()
    r = rig()
    r.left_trigger.to(0.3).run()
    r.left_trigger.add(0.4).over(300)

    def check_end():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.7) < 0.1, f"Expected 0.3+0.4=0.7, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


def test_trigger_add_negative(on_success, on_failure):
    """left_trigger.add(-0.3) subtracts from current"""
    setup()
    r = rig()
    r.left_trigger.to(0.8).run()
    r.left_trigger.add(-0.3).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.5) < 0.05, f"Expected 0.8-0.3=0.5, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_mul(on_success, on_failure):
    """left_trigger.mul(0.5) multiplies current value"""
    setup()
    r = rig()
    r.left_trigger.to(0.8).run()
    r.left_trigger.mul(0.5).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.4) < 0.05, f"Expected 0.8*0.5=0.4, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# TRIGGER EASING
# ============================================================================

def test_trigger_over_with_easing(on_success, on_failure):
    """left_trigger.to(1).over(300, 'ease_in_quad') applies easing"""
    setup()
    r = rig()
    r.left_trigger.to(1).over(300, "ease_in_quad")

    def check_end():
        try:
            val = r.state.left_trigger
            assert abs(val - 1.0) < 0.1, f"Expected ~1.0, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check_end)


# ============================================================================
# TRIGGER CALLBACKS
# ============================================================================

def test_trigger_over_then_callback(on_success, on_failure):
    """Callback fires when trigger .over() completes"""
    setup()
    r = rig()
    callback_fired = {"value": False}

    def on_done():
        callback_fired["value"] = True

    r.left_trigger.to(1).over(200).then(on_done)

    def check():
        try:
            assert callback_fired["value"], "Callback was not fired"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_trigger_lifecycle_callbacks(on_success, on_failure):
    """Trigger lifecycle callbacks fire in order"""
    setup()
    r = rig()
    callback_order = []

    r.left_trigger.to(1).over(100).then(lambda: callback_order.append("over")).hold(100).then(lambda: callback_order.append("hold")).revert(100).then(lambda: callback_order.append("revert"))

    def check():
        try:
            expected = ["over", "hold", "revert"]
            assert callback_order == expected, f"Expected {expected}, got {callback_order}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("600ms", check)


# ============================================================================
# TRIGGER LAYERS
# ============================================================================

def test_trigger_override_layer(on_success, on_failure):
    """Override layer replaces trigger value"""
    setup()
    r = rig()
    r.left_trigger.to(0.8).run()
    r.layer("aim").override.left_trigger.to(0.2).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.2) < 0.05, f"Expected override to 0.2, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_scale_layer(on_success, on_failure):
    """Scale layer multiplies trigger value"""
    setup()
    r = rig()
    r.left_trigger.to(0.8).run()
    r.layer("aim").scale.left_trigger.to(0.5).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.4) < 0.05, f"Expected 0.8*0.5=0.4, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_trigger_offset_hold_revert(on_success, on_failure):
    """Trigger offset layer with full lifecycle: over → hold → revert"""
    setup()
    r = rig()
    r.left_trigger.to(0.3).run()
    r.layer("boost").offset.left_trigger.to(0.5).over(150).hold(200).revert(150)

    def check_during_hold():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.8) < 0.1, f"Expected ~0.8 during hold, got {val}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("400ms", check_after_revert)

    def check_after_revert():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.3) < 0.1, f"Expected ~0.3 after revert, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("250ms", check_during_hold)


def test_right_trigger_over(on_success, on_failure):
    """Right trigger animates independently from left"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()
    r.right_trigger.to(0.8).over(200)

    def check():
        try:
            assert abs(r.state.left_trigger - 0.5) < 0.05, \
                f"Left trigger should stay at 0.5, got {r.state.left_trigger}"
            assert abs(r.state.right_trigger - 0.8) < 0.1, \
                f"Right trigger should be ~0.8, got {r.state.right_trigger}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_trigger_clamp_negative(on_success, on_failure):
    """Trigger add below 0 clamps to 0"""
    setup()
    r = rig()
    r.left_trigger.to(0.2).run()
    r.left_trigger.add(-0.5).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val) < 0.01, f"Expected clamped to 0, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# TEST REGISTRY
# ============================================================================

TRIGGER_ADVANCED_TESTS = [
    ("trigger.add()", test_trigger_add),
    ("trigger.add().over()", test_trigger_add_over),
    ("trigger.add() negative", test_trigger_add_negative),
    ("trigger.mul()", test_trigger_mul),
    ("trigger.over() with easing", test_trigger_over_with_easing),
    ("trigger.over().then()", test_trigger_over_then_callback),
    ("trigger lifecycle callbacks", test_trigger_lifecycle_callbacks),
    ("trigger override layer", test_trigger_override_layer),
    ("trigger scale layer", test_trigger_scale_layer),
    ("trigger offset hold revert", test_trigger_offset_hold_revert),
    ("right trigger over", test_right_trigger_over),
    ("trigger clamp negative", test_trigger_clamp_negative),
]
