"""Reverse tests - instant and gradual stick direction reversal"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


# ============================================================================
# INSTANT REVERSE
# ============================================================================

def test_reverse_instant_stick(on_success, on_failure):
    """reverse() instantly flips stick direction"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def do_reverse():
        r.reverse()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - (-1.0)) < 0.1, f"Expected x~-1.0, got {pos.x}"
                assert abs(pos.y) < 0.1, f"Expected y~0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_reverse)


def test_reverse_instant_diagonal(on_success, on_failure):
    """reverse() flips diagonal stick position"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0.5).run()

    def do_reverse():
        r.reverse()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - (-0.5)) < 0.1, f"Expected x~-0.5, got {pos.x}"
                assert abs(pos.y - (-0.5)) < 0.1, f"Expected y~-0.5, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_reverse)


def test_reverse_instant_preserves_triggers(on_success, on_failure):
    """reverse() does not affect trigger values"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_trigger.to(0.7).run()

    def do_reverse():
        r.reverse()

        def check():
            try:
                val = r.state.left_trigger
                assert abs(val - 0.7) < 0.05, f"Expected trigger 0.7 preserved, got {val}"
                pos = r.state.left_stick
                assert abs(pos.x - (-1.0)) < 0.1, f"Expected stick reversed, got {pos.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_reverse)


def test_reverse_instant_both_sticks(on_success, on_failure):
    """reverse() flips both sticks"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, 1).run()

    def do_reverse():
        r.reverse()

        def check():
            try:
                left = r.state.left_stick
                right = r.state.right_stick
                assert abs(left.x - (-1.0)) < 0.1, f"Expected left x~-1.0, got {left.x}"
                assert abs(right.y - (-1.0)) < 0.1, f"Expected right y~-1.0, got {right.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_reverse)


def test_reverse_double_returns_to_original(on_success, on_failure):
    """reverse() twice returns to original position"""
    setup()
    r = rig()
    r.left_stick.to(0.7, 0.3).run()

    def do_first_reverse():
        r.reverse()

        def do_second_reverse():
            r.reverse()

            def check():
                try:
                    pos = r.state.left_stick
                    assert abs(pos.x - 0.7) < 0.1, f"Expected x~0.7, got {pos.x}"
                    assert abs(pos.y - 0.3) < 0.1, f"Expected y~0.3, got {pos.y}"
                    on_success()
                except Exception as e:
                    on_failure(str(e))
                finally:
                    teardown()

            cron.after(VISIBLE_MS, check)

        cron.after(VISIBLE_MS, do_second_reverse)

    cron.after(VISIBLE_MS, do_first_reverse)


# ============================================================================
# GRADUAL REVERSE
# ============================================================================

def test_reverse_gradual(on_success, on_failure):
    """reverse(400) smoothly transitions to reversed direction"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.reverse(400)

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - (-1.0)) < 0.15, f"Expected x~-1.0 after gradual reverse, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("800ms", check)


def test_reverse_gradual_preserves_layers(on_success, on_failure):
    """reverse(400) preserves offset layers (reversed)"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("boost").offset.left_stick.to(0.3, 0).run()
    r.reverse(400)

    def check():
        try:
            pos = r.state.left_stick
            # Base: 0.5 → -0.5, offset: 0.3 → -0.3, total: -0.8
            assert pos.x < -0.3, f"Expected negative x after reverse, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("800ms", check)


# ============================================================================
# AUTO-DETECT SAME-AXIS REVERSAL (linear interpolation)
# ============================================================================

def test_stick_to_reverse_uses_linear(on_success, on_failure):
    """left_stick.to(-1, 0) from (1, 0) should go through zero (linear)"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.to(-1, 0).over(400)

    def check_mid():
        try:
            pos = r.state.left_stick
            # At midpoint, should be near zero (linear through center)
            assert abs(pos.x) < 0.5, f"Expected near zero at midpoint, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return
        cron.after("300ms", check_end)

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - (-1.0)) < 0.15, f"Expected x~-1.0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("200ms", check_mid)


def test_stick_to_reverse_y_axis(on_success, on_failure):
    """left_stick.to(0, -1) from (0, 1) uses linear interpolation"""
    setup()
    r = rig()
    r.left_stick.to(0, 1).run()
    r.left_stick.to(0, -1).over(400)

    def check_end():
        try:
            pos = r.state.left_stick
            assert abs(pos.y - (-1.0)) < 0.15, f"Expected y~-1.0, got {pos.y}"
            assert abs(pos.x) < 0.1, f"Expected x~0, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("600ms", check_end)


def test_direction_to_reverse_uses_linear(on_success, on_failure):
    """direction.to(-1, 0) from (1, 0) uses linear interpolation"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.direction.to(-1, 0).over(400)

    def check_end():
        try:
            pos = r.state.left_stick
            # Direction reversed, magnitude preserved
            assert pos.x < -0.5, f"Expected negative x after direction reverse, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after("600ms", check_end)


# ============================================================================
# TEST REGISTRY
# ============================================================================

REVERSE_TESTS = [
    ("reverse instant stick", test_reverse_instant_stick),
    ("reverse instant diagonal", test_reverse_instant_diagonal),
    ("reverse preserves triggers", test_reverse_instant_preserves_triggers),
    ("reverse both sticks", test_reverse_instant_both_sticks),
    ("reverse double returns original", test_reverse_double_returns_to_original),
    ("reverse gradual", test_reverse_gradual),
    ("reverse gradual preserves layers", test_reverse_gradual_preserves_layers),
    ("stick .to() reverse uses linear", test_stick_to_reverse_uses_linear),
    ("stick .to() reverse y axis", test_stick_to_reverse_y_axis),
    ("direction .to() reverse uses linear", test_direction_to_reverse_uses_linear),
]
