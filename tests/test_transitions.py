"""Tests for transitions, direction changes, trigger offsets, and layer reverts"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


# =========================================================================
# Stick direction transitions
# =========================================================================

def test_stick_forward_to_left(on_success, on_failure):
    """Stick going forward, then transitions to left over time"""
    setup()
    r = rig()
    r.left_stick.to(0, 1).run()

    def start_transition():
        try:
            pos = r.state.left_stick
            assert abs(pos.y - 1.0) < 0.05, f"Expected y~1.0 before transition, got {pos.y}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.left_stick.to(-1, 0).over(300)

        def check_mid():
            try:
                pos = r.state.left_stick
                # Mid-transition: should be somewhere between (0,1) and (-1,0)
                assert pos.x < 0.1, f"Expected x moving left, got {pos.x}"
                assert pos.y > -0.1, f"Expected y still positive-ish, got {pos.y}"
            except Exception as e:
                teardown()
                on_failure(str(e))
                return
            cron.after("300ms", check_end)

        def check_end():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - (-1.0)) < 0.1, f"Expected x~-1.0, got {pos.x}"
                assert abs(pos.y) < 0.1, f"Expected y~0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("150ms", check_mid)

    cron.after(VISIBLE_MS, start_transition)


def test_stick_direction_to(on_success, on_failure):
    """direction.to() sets stick direction"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.direction.to(0, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.y - 1.0) < 0.1, f"Expected y~1.0 after direction.to, got {pos.y}"
            assert abs(pos.x) < 0.1, f"Expected x~0 after direction.to, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


# =========================================================================
# Direction rotation (by / 180)
# =========================================================================

def test_direction_by_90_discrete(on_success, on_failure):
    """direction.by(90) rotates instantly"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def rotate():
        r.left_stick.direction.by(90).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x) < 0.15, f"Expected x~0 after 90 deg, got {pos.x}"
                assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0 after 90 deg, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, rotate)


def test_direction_by_180_discrete(on_success, on_failure):
    """direction.by(180) reverses direction instantly"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def reverse():
        r.left_stick.direction.by(180).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - (-1.0)) < 0.15, f"Expected x~-1.0 after 180, got {pos.x}"
                assert abs(pos.y) < 0.15, f"Expected y~0 after 180, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, reverse)


def test_direction_by_180_over_time(on_success, on_failure):
    """direction.by(180).over(300) reverses direction smoothly"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def start_reverse():
        r.left_stick.direction.by(180).over(300)

        def check_mid():
            try:
                pos = r.state.left_stick
                # Mid-rotation at ~90 degrees: should be roughly (0, 1)
                assert pos.x < 0.8, f"Expected x decreasing mid-rotation, got {pos.x}"
            except Exception as e:
                teardown()
                on_failure(str(e))
                return
            cron.after("300ms", check_end)

        def check_end():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - (-1.0)) < 0.15, f"Expected x~-1.0, got {pos.x}"
                assert abs(pos.y) < 0.15, f"Expected y~0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("150ms", check_mid)

    cron.after(VISIBLE_MS, start_reverse)


def test_direction_by_90_over_time(on_success, on_failure):
    """direction.by(90).over(300) rotates smoothly"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def start_rotate():
        r.left_stick.direction.by(90).over(300)

        def check_end():
            try:
                pos = r.state.left_stick
                assert abs(pos.x) < 0.15, f"Expected x~0 after 90 deg, got {pos.x}"
                assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0 after 90 deg, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("500ms", check_end)

    cron.after(VISIBLE_MS, start_rotate)


# =========================================================================
# Trigger offset over time
# =========================================================================

def test_trigger_offset_over_time(on_success, on_failure):
    """Trigger offset layer with .over() interpolates"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()

    def start_offset():
        r.layer("boost").offset.left_trigger.to(0.3).over(300)

        def check_end():
            try:
                val = r.state.left_trigger
                assert abs(val - 0.8) < 0.1, f"Expected ~0.8 (0.5+0.3), got {val}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("500ms", check_end)

    cron.after(VISIBLE_MS, start_offset)


def test_trigger_offset_revert(on_success, on_failure):
    """Trigger offset layer reverts smoothly"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()
    r.layer("boost").offset.left_trigger.to(0.3).run()

    def do_revert():
        try:
            val = r.state.left_trigger
            assert abs(val - 0.8) < 0.1, f"Expected ~0.8 before revert, got {val}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.layer("boost").revert(200).run()

        def check():
            try:
                val = r.state.left_trigger
                assert abs(val - 0.5) < 0.1, f"Expected ~0.5 after revert, got {val}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("400ms", check)

    cron.after(VISIBLE_MS, do_revert)


# =========================================================================
# Layer revert (stick offset) — regression test for revert bug
# =========================================================================

def test_stick_offset_revert_animated(on_success, on_failure):
    """Stick offset layer reverts smoothly (regression test)"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").offset.left_stick.to(0.3, 0).run()

    def do_revert():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.8) < 0.1, f"Expected ~0.8 before revert, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.layer("aim").revert(200).run()

        def check_mid():
            try:
                pos = r.state.left_stick
                # Should be between 0.5 and 0.8 during revert
                assert 0.4 < pos.x < 0.85, f"Expected mid-revert value, got {pos.x}"
            except Exception as e:
                teardown()
                on_failure(str(e))
                return
            cron.after("250ms", check_end)

        def check_end():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - 0.5) < 0.1, f"Expected ~0.5 after revert, got {pos.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("100ms", check_mid)

    cron.after(VISIBLE_MS, do_revert)


def test_stick_offset_revert_never_exceeds(on_success, on_failure):
    """Offset revert should never exceed original combined value (regression)"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").offset.left_stick.to(0.3, 0).run()
    max_seen = {"value": 0.0}

    def do_revert():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.8) < 0.1, f"Expected ~0.8, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.layer("aim").revert(300).run()
        sample_count = {"n": 0}

        def sample():
            pos = r.state.left_stick
            if pos.x > max_seen["value"]:
                max_seen["value"] = pos.x
            sample_count["n"] += 1
            if sample_count["n"] < 10:
                cron.after("40ms", sample)
            else:
                check_result()

        def check_result():
            try:
                assert max_seen["value"] < 0.9, \
                    f"Value exceeded 0.9 during revert: max={max_seen['value']}"
                pos = r.state.left_stick
                assert abs(pos.x - 0.5) < 0.1, f"Expected ~0.5 after revert, got {pos.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("30ms", sample)

    cron.after(VISIBLE_MS, do_revert)


# =========================================================================
# Multiple sequential transitions
# =========================================================================

def test_stick_chain_transitions(on_success, on_failure):
    """Stick moves right then up in sequence"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(200)

    def start_second():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 1.0) < 0.15, f"Expected x~1.0 after first, got {pos.x}"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.left_stick.to(0, 1).over(200)

        def check_end():
            try:
                pos = r.state.left_stick
                assert abs(pos.x) < 0.15, f"Expected x~0, got {pos.x}"
                assert abs(pos.y - 1.0) < 0.15, f"Expected y~1.0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("400ms", check_end)

    cron.after("400ms", start_second)


TRANSITION_TESTS = [
    ("stick forward to left", test_stick_forward_to_left),
    ("stick direction.to", test_stick_direction_to),
    ("direction by 90 discrete", test_direction_by_90_discrete),
    ("direction by 180 discrete", test_direction_by_180_discrete),
    ("direction by 180 over time", test_direction_by_180_over_time),
    ("direction by 90 over time", test_direction_by_90_over_time),
    ("trigger offset over time", test_trigger_offset_over_time),
    ("trigger offset revert", test_trigger_offset_revert),
    ("stick offset revert animated", test_stick_offset_revert_animated),
    ("stick offset revert never exceeds", test_stick_offset_revert_never_exceeds),
    ("stick chain transitions", test_stick_chain_transitions),
]
