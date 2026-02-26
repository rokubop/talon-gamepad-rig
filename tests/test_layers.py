"""Tests for layer composition: offset, override, scale"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_offset_layer(on_success, on_failure):
    """Offset layer adds to base"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").offset.left_stick.to(0.3, 0).run()

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


def test_override_layer(on_success, on_failure):
    """Override layer replaces current value"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").override.left_stick.to(0.2, 0).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.2) < 0.05, f"Expected override to 0.2, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_scale_layer(on_success, on_failure):
    """Scale layer multiplies current value"""
    setup()
    r = rig()
    r.left_stick.to(0.8, 0).run()
    r.layer("aim").scale.left_stick.to(0.5, 1).run()

    def check():
        try:
            pos = r.state.left_stick
            assert abs(pos.x - 0.4) < 0.05, f"Expected 0.8*0.5=0.4, got {pos.x}"
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(VISIBLE_MS, check)


def test_layer_revert(on_success, on_failure):
    """Layer revert removes layer effect"""
    setup()
    r = rig()
    r.left_stick.to(0.5, 0).run()
    r.layer("aim").offset.left_stick.to(0.3, 0).run()

    def do_revert():
        r.layer("aim").revert(100).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x - 0.5) < 0.1, f"Expected ~0.5 after revert, got {pos.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_revert)


def test_trigger_offset_layer(on_success, on_failure):
    """Offset layer on trigger"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()
    r.layer("boost").offset.left_trigger.to(0.3).run()

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


LAYER_TESTS = [
    ("offset layer", test_offset_layer),
    ("override layer", test_override_layer),
    ("scale layer", test_scale_layer),
    ("layer revert", test_layer_revert),
    ("trigger offset layer", test_trigger_offset_layer),
]
