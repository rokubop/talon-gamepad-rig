"""Validation tests - error cases, boundary conditions, edge cases"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig


# ============================================================================
# ERROR CASES
# ============================================================================

def test_duplicate_operator_calls(on_success, on_failure):
    """Calling .to().to() should error"""
    setup()
    try:
        r = rig()
        r.left_stick.to(1, 0).to(0, 1)
        on_failure("Expected error for duplicate .to() calls")
    except Exception as e:
        error_msg = str(e).lower()
        if "operator" in error_msg or "already" in error_msg or "duplicate" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


def test_mixed_operators(on_success, on_failure):
    """Calling .to().add() should error"""
    setup()
    try:
        r = rig()
        r.left_stick.to(1, 0).add(0.5, 0)
        on_failure("Expected error for mixed operators")
    except Exception as e:
        error_msg = str(e).lower()
        if "operator" in error_msg or "already" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


def test_negative_duration(on_success, on_failure):
    """Negative duration should error"""
    setup()
    try:
        r = rig()
        r.left_stick.to(1, 0).over(-500)
        on_failure("Expected error for negative duration")
    except Exception as e:
        error_msg = str(e).lower()
        if "negative" in error_msg or "duration" in error_msg or "must be" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


def test_direction_zero_vector(on_success, on_failure):
    """direction.to(0, 0) should error"""
    setup()
    try:
        r = rig()
        r.left_stick.to(1, 0).run()
        r.left_stick.direction.to(0, 0).run()
        on_failure("Expected error for zero direction vector")
    except Exception as e:
        error_msg = str(e).lower()
        if "zero" in error_msg or "invalid" in error_msg or "direction" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


def test_empty_layer_name(on_success, on_failure):
    """layer('') with empty name should error or handle gracefully"""
    setup()
    try:
        r = rig()
        r.layer("").offset.left_stick.to(0.5, 0).run()
        # If it succeeds, check state
        cron.after("100ms", lambda: _check_empty_layer(r, on_success, on_failure))
    except Exception as e:
        error_msg = str(e).lower()
        if "empty" in error_msg or "name" in error_msg or "invalid" in error_msg:
            teardown()
            on_success()
        else:
            teardown()
            on_failure(f"Error occurred but message unclear: {e}")


def _check_empty_layer(r, on_success, on_failure):
    try:
        if "" in r.state.layers:
            on_failure("Empty layer name was allowed")
        else:
            on_success()
    except Exception as e:
        on_failure(str(e))
    finally:
        teardown()


def test_layer_without_mode(on_success, on_failure):
    """layer('name').left_stick.to() without .offset/.override/.scale should error"""
    setup()
    try:
        r = rig()
        builder = r.layer("test").left_stick.to(1, 0)
        builder._execute()
        on_failure("Expected error for layer without mode")
    except Exception as e:
        error_msg = str(e).lower()
        if "mode" in error_msg or "offset" in error_msg or "override" in error_msg or "scale" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


def test_duplicate_mode_specification(on_success, on_failure):
    """layer().offset.override should error - can't specify both"""
    setup()
    try:
        r = rig()
        r.layer("test").offset.override.left_stick.to(1, 0)
        on_failure("Expected error for duplicate mode")
    except Exception as e:
        error_msg = str(e).lower()
        if "mode" in error_msg or "already" in error_msg or "duplicate" in error_msg or "only one" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")
    finally:
        teardown()


# ============================================================================
# BOUNDARY / EDGE CASES
# ============================================================================

def test_very_small_duration(on_success, on_failure):
    """over(1) - 1ms duration should complete without error"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(1)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.15, f"Expected x~1.0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("200ms", check)


def test_zero_duration_over(on_success, on_failure):
    """over(0) should apply instantly"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(0)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.15, f"Expected x~1.0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("200ms", check)


def test_stick_to_neutral_then_operate(on_success, on_failure):
    """Set to (0,0) then operate again - should work normally"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.to(0, 0).run()
    r.left_stick.to(0, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x) < 0.05, f"Expected x~0, got {pos.x}"
            assert abs(pos.y - 1.0) < 0.05, f"Expected y~1.0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


VISIBLE_MS = "300ms"


def test_trigger_full_press_release_press(on_success, on_failure):
    """Full press → release → press should work"""
    setup()
    r = rig()
    r.left_trigger.to(1).run()
    r.left_trigger.to(0).run()
    r.left_trigger.to(0.7).run()

    def check():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.7) < 0.05, f"Expected 0.7, got {val}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_invalid_attribute_helpful_error(on_success, on_failure):
    """Accessing invalid attribute gives helpful error message"""
    setup()
    try:
        r = rig()
        _ = r.leftstick  # typo
        on_failure("Expected AttributeError")
    except AttributeError as e:
        error_msg = str(e)
        if "left_stick" in error_msg or "Did you mean" in error_msg:
            on_success()
        else:
            on_failure(f"Error not helpful: {e}")
    except Exception as e:
        on_failure(f"Wrong exception type: {type(e).__name__}: {e}")
    finally:
        teardown()


def test_multiple_layers_ordered(on_success, on_failure):
    """Multiple layers with order compose correctly"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("first", order=0).offset.left_stick.to(0.1, 0).run()
    r.layer("second", order=1).offset.left_stick.to(0.1, 0).run()

    def check():
        try:
            pos = r.state.left_stick
            # Both offsets should apply: 0.5 + 0.1 + 0.1 = 0.7
            assert abs(pos.x - 0.7) < 0.1, f"Expected 0.7, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_new_operation_after_stop(on_success, on_failure):
    """Can set values after stop()"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.stop()
    r.left_stick.to(0, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.y - 1.0) < 0.1, f"Expected y~1.0, got {pos.y}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# ============================================================================
# TEST REGISTRY
# ============================================================================

VALIDATION_TESTS = [
    ("duplicate .to().to()", test_duplicate_operator_calls),
    ("mixed .to().add()", test_mixed_operators),
    ("negative duration", test_negative_duration),
    ("zero direction vector", test_direction_zero_vector),
    ("empty layer name", test_empty_layer_name),
    ("layer without mode", test_layer_without_mode),
    ("duplicate mode specification", test_duplicate_mode_specification),
    ("very small duration (1ms)", test_very_small_duration),
    ("zero duration over(0)", test_zero_duration_over),
    ("stick neutral then operate", test_stick_to_neutral_then_operate),
    ("trigger press release press", test_trigger_full_press_release_press),
    ("invalid attribute helpful error", test_invalid_attribute_helpful_error),
    ("multiple layers ordered", test_multiple_layers_ordered),
    ("new operation after stop", test_new_operation_after_stop),
]
