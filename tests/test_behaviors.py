"""Behavior tests - stack, replace, queue, throttle, debounce for sticks and triggers"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


# ============================================================================
# STACK BEHAVIOR
# ============================================================================

def test_stack_stick_offset(on_success, on_failure):
    """stack() on stick offset accumulates multiple operations"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()

    r.layer("a").offset.left_stick.to(0.3, 0).stack().run()
    r.layer("a").offset.left_stick.to(0.2, 0).stack().run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.5) < 0.1, f"Expected stacked 0.3+0.2=0.5, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stack_max(on_success, on_failure):
    """stack(max=2) limits accumulation count"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()

    r.layer("a").offset.left_stick.to(0.2, 0).stack(max=2).run()
    r.layer("a").offset.left_stick.to(0.2, 0).stack(max=2).run()
    r.layer("a").offset.left_stick.to(0.2, 0).stack(max=2).run()

    def check():
        try:
            pos = r.state.left_stick
            # max=2 means only 2 stacks: 0.4, not 0.6
            assert abs(pos.x - 0.4) < 0.1, f"Expected capped at 0.4, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stack_trigger_offset(on_success, on_failure):
    """stack() on trigger offset accumulates"""
    setup()
    r = rig()
    r.left_trigger.to(0.2).run()

    r.layer("boost").offset.left_trigger.to(0.2).stack().run()
    r.layer("boost").offset.left_trigger.to(0.2).stack().run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.6) < 0.1, f"Expected 0.2+0.2+0.2=0.6, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stack_1_no_stacking(on_success, on_failure):
    """stack(1) prevents stacking on rapid calls without revert"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()

    offset = 0.3
    r.layer("test").offset.left_stick.to(offset, 0).stack(1).run()
    r.layer("test").offset.left_stick.to(offset, 0).stack(1).run()
    r.layer("test").offset.left_stick.to(offset, 0).stack(1).run()

    def check():
        try:
            pos = r.state.left_stick
            # stack(1) means no accumulation
            assert abs(pos.x - offset) < 0.1, f"Expected {offset} (no stacking), got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_stack_1_revert_then_reapply(on_success, on_failure):
    """stack(1): after full revert, can reapply"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()
    offset = 0.4

    r.layer("test2").offset.left_stick.to(offset, 0).stack(1).run()

    def do_revert():
        r.layer("test2").revert(100).run()

    def reapply():
        r.layer("test2").offset.left_stick.to(offset, 0).stack(1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - offset) < 0.1, f"Expected {offset} after reapply, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("100ms", do_revert)
    cron.after("400ms", reapply)
    cron.after("600ms", check)


# ============================================================================
# REPLACE BEHAVIOR
# ============================================================================

def test_replace_stick_offset(on_success, on_failure):
    """replace() replaces previous offset with new one"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()

    r.layer("aim").offset.left_stick.to(0.5, 0).run()

    def do_replace():
        r.layer("aim").offset.left_stick.to(0.2, 0).replace().run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.2) < 0.1, f"Expected replaced to 0.2, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("100ms", do_replace)
    cron.after("400ms", check)


def test_replace_during_animation(on_success, on_failure):
    """replace() during in-flight animation replaces smoothly"""
    setup()
    r = rig()
    r.left_stick.to(0, 0).run()

    r.layer("aim").offset.left_stick.to(0.8, 0).over(500)

    def do_replace():
        r.layer("aim").offset.left_stick.to(0.3, 0).replace().over(200)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.3) < 0.1, f"Expected replaced to 0.3, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("200ms", do_replace)
    cron.after("600ms", check)


def test_replace_trigger(on_success, on_failure):
    """replace() on trigger offset"""
    setup()
    r = rig()
    r.left_trigger.to(0.2).run()
    r.layer("boost").offset.left_trigger.to(0.5).run()

    def do_replace():
        r.layer("boost").offset.left_trigger.to(0.2).replace().run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.4) < 0.1, f"Expected 0.2+0.2=0.4, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("100ms", do_replace)
    cron.after("400ms", check)


# ============================================================================
# QUEUE BEHAVIOR
# ============================================================================

def test_queue_stick_operations(on_success, on_failure):
    """queue() executes operations sequentially"""
    setup()
    r = rig()

    r.left_stick.to(1, 0).over(200).queue()
    r.left_stick.to(0, 1).over(200).queue()

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.15, f"Expected x~0 (second op), got {pos.x}"
            assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0 (second op), got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("700ms", check_end)


def test_queue_max(on_success, on_failure):
    """queue(max=2) limits queue length"""
    setup()
    r = rig()

    r.left_stick.to(1, 0).over(200).queue(max=2)
    r.left_stick.to(0, 1).over(200).queue(max=2)
    r.left_stick.to(-1, 0).over(200).queue(max=2)  # Should be dropped

    def check_end():
        try:
            pos = r.state.left_stick
            # Third op dropped, should end at (0, 1)
            assert abs(pos.x) < 0.15, f"Expected x~0, got {pos.x}"
            assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("700ms", check_end)


def test_queue_trigger(on_success, on_failure):
    """queue() on trigger operations"""
    setup()
    r = rig()

    r.left_trigger.to(0.5).over(150).queue()
    r.left_trigger.to(1.0).over(150).queue()

    def check_end():
        try:
            val = r.state.left_trigger
            assert abs(val - 1.0) < 0.1, f"Expected 1.0 after queue, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("600ms", check_end)


# ============================================================================
# THROTTLE BEHAVIOR
# ============================================================================

def test_throttle_stick(on_success, on_failure):
    """throttle() ignores rapid calls while active"""
    setup()
    r = rig()

    r.left_stick.to(1, 0).over(300).throttle()
    # This should be ignored since first is still active
    r.left_stick.to(0, 1).over(300).throttle()

    def check():
        try:
            pos = r.state.left_stick
            # Should have completed first operation, second was throttled
            assert abs(pos.x - 1.0) < 0.15, f"Expected x~1.0 (first op), got {pos.x}"
            assert abs(pos.y) < 0.15, f"Expected y~0 (second throttled), got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_throttle_trigger(on_success, on_failure):
    """throttle() on trigger ignores rapid calls"""
    setup()
    r = rig()

    r.left_trigger.to(0.5).over(200).throttle()
    r.left_trigger.to(1.0).over(200).throttle()  # Should be ignored

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.5) < 0.1, f"Expected 0.5 (throttled), got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("400ms", check)


# ============================================================================
# DEBOUNCE BEHAVIOR
# ============================================================================

def test_debounce_stick(on_success, on_failure):
    """debounce(200) delays and cancels previous pending"""
    setup()
    r = rig()

    r.left_stick.to(1, 0).debounce(200)
    # Rapid second call should cancel first and start new debounce
    cron.after("50ms", lambda: r.left_stick.to(0, 1).debounce(200))

    def check():
        try:
            pos = r.state.left_stick
            # Only last debounced operation should fire
            assert abs(pos.x) < 0.15, f"Expected x~0 (last debounce), got {pos.x}"
            assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0 (last debounce), got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_debounce_trigger(on_success, on_failure):
    """debounce(200) on trigger cancels previous pending"""
    setup()
    r = rig()

    r.left_trigger.to(0.3).debounce(200)
    cron.after("50ms", lambda: r.left_trigger.to(0.8).debounce(200))

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.8) < 0.1, f"Expected 0.8 (last debounce), got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


# ============================================================================
# STOP WITH CALLBACK
# ============================================================================

def test_stop_then_callback(on_success, on_failure):
    """stop(ms).then(callback) fires after deceleration"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    callback_fired = {"value": False}

    def on_stopped():
        callback_fired["value"] = True

    r.stop(200).then(on_stopped)

    def check():
        try:
            assert callback_fired["value"], "Stop callback was not fired"
            pos = r.state.left_stick
            assert abs(pos.x) < 0.1, f"Expected x~0 after stop, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("500ms", check)


def test_stop_callback_not_fired_on_interrupt(on_success, on_failure):
    """Stop callback should not fire if interrupted by new operation"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    callback_fired = {"value": False}

    def on_stopped():
        callback_fired["value"] = True

    r.stop(400).then(on_stopped)

    def interrupt():
        r.left_stick.to(0, 1).run()

    def check():
        try:
            assert not callback_fired["value"], "Stop callback should not fire when interrupted"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("100ms", interrupt)
    cron.after("600ms", check)


# ============================================================================
# LAYER WITH BEHAVIOR AND LIFECYCLE
# ============================================================================

def test_layer_offset_over_revert_with_stack(on_success, on_failure):
    """layer offset with stack, over, and revert lifecycle"""
    setup()
    r = rig()
    r.left_stick.to(0.3, 0).run()
    r.layer("boost").offset.left_stick.to(0.3, 0).stack().over(150).hold(200).revert(150)

    def check_during_hold():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.6) < 0.15, f"Expected ~0.6 during hold, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("400ms", check_after_revert)

    def check_after_revert():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.3) < 0.1, f"Expected ~0.3 after revert, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("250ms", check_during_hold)


# ============================================================================
# TEST REGISTRY
# ============================================================================

BEHAVIOR_TESTS = [
    ("stack stick offset", test_stack_stick_offset),
    ("stack(max=2)", test_stack_max),
    ("stack trigger offset", test_stack_trigger_offset),
    ("stack(1) no stacking", test_stack_1_no_stacking),
    ("stack(1) revert then reapply", test_stack_1_revert_then_reapply),
    ("replace stick offset", test_replace_stick_offset),
    ("replace during animation", test_replace_during_animation),
    ("replace trigger", test_replace_trigger),
    ("queue stick operations", test_queue_stick_operations),
    ("queue(max=2)", test_queue_max),
    ("queue trigger", test_queue_trigger),
    ("throttle stick", test_throttle_stick),
    ("throttle trigger", test_throttle_trigger),
    ("debounce stick", test_debounce_stick),
    ("debounce trigger", test_debounce_trigger),
    ("stop().then() callback", test_stop_then_callback),
    ("stop callback not fired on interrupt", test_stop_callback_not_fired_on_interrupt),
    ("layer offset over revert with stack", test_layer_offset_over_revert_with_stack),
]
