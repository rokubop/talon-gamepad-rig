"""Tests for stop and reset functionality"""

from talon import cron
from .helpers import setup, teardown
from ..src import rig

VISIBLE_MS = "300ms"


def test_stop_clears_to_neutral(on_success, on_failure):
    """stop() returns all state values to neutral"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, -1).run()
    r.left_trigger.to(0.5).run()
    r.right_trigger.to(0.8).run()

    def do_stop():
        r.stop()

        def check():
            try:
                pos_l = r.state.left_stick
                pos_r = r.state.right_stick
                assert abs(pos_l.x) < 0.01, f"Expected lt_x=0, got {pos_l.x}"
                assert abs(pos_l.y) < 0.01, f"Expected lt_y=0, got {pos_l.y}"
                assert abs(pos_r.x) < 0.01, f"Expected rt_x=0, got {pos_r.x}"
                assert abs(pos_r.y) < 0.01, f"Expected rt_y=0, got {pos_r.y}"
                assert abs(r.state.left_trigger) < 0.01, f"Expected lt_trig=0, got {r.state.left_trigger}"
                assert abs(r.state.right_trigger) < 0.01, f"Expected rt_trig=0, got {r.state.right_trigger}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_stop_clears_layers(on_success, on_failure):
    """stop() removes all layers"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.layer("aim").offset.left_stick.to(0.2, 0).run()

    def do_stop():
        r.stop()

        def check():
            try:
                assert len(r.state.layers) == 0, f"Expected no layers, got {r.state.layers}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_stop_stops_frame_loop(on_success, on_failure):
    """stop() stops a running frame loop"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).over(1000)

    def do_stop():
        try:
            assert r.state._frame_loop_job is not None, "Frame loop should be running"
        except Exception as e:
            teardown()
            on_failure(str(e))
            return

        r.stop()

        def check():
            try:
                assert r.state._frame_loop_job is None, "Frame loop should be stopped"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after("200ms", do_stop)


def test_reset_clears_everything(on_success, on_failure):
    """reset() clears all state"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.layer("aim").offset.left_stick.to(0.2, 0).run()

    def do_reset():
        r.reset()

        def check():
            try:
                assert len(r.state.layers) == 0
                pos = r.state.left_stick
                assert abs(pos.x) < 0.01 and abs(pos.y) < 0.01
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_reset)


def test_stop_with_transition(on_success, on_failure):
    """stop(ms=200) transitions to neutral over time"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def do_stop():
        r.stop(200)

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.x) < 0.1, f"Expected ~0 after transition, got {pos.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("400ms", check)

    cron.after(VISIBLE_MS, do_stop)


def test_new_operation_after_stop(on_success, on_failure):
    """Can set new values after stop()"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def do_stop_and_set():
        r.stop()
        r.left_stick.to(0, 1).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.y - 1.0) < 0.05, f"Expected y=1.0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop_and_set)


def test_left_stick_stop_clears_only_left(on_success, on_failure):
    """left_stick.stop() clears left stick but leaves right stick and triggers"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, -1).run()
    r.left_trigger.to(0.5).run()

    def do_stop():
        r.left_stick.stop()

        def check():
            try:
                pos_l = r.state.left_stick
                pos_r = r.state.right_stick
                assert abs(pos_l.x) < 0.01, f"Expected left x=0, got {pos_l.x}"
                assert abs(pos_l.y) < 0.01, f"Expected left y=0, got {pos_l.y}"
                assert abs(pos_r.y - (-1.0)) < 0.05, f"Expected right y=-1, got {pos_r.y}"
                assert abs(r.state.left_trigger - 0.5) < 0.05, f"Expected lt_trig=0.5, got {r.state.left_trigger}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_left_stick_stop_clears_layers(on_success, on_failure):
    """left_stick.stop() removes left stick layers but not right stick layers"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.left_stick.magnitude.offset.add(0.3).run()
    r.right_stick.to(0, 1).run()
    r.layer("aim").offset.right_stick.to(0.2, 0).run()

    def do_stop():
        r.left_stick.stop()

        def check():
            try:
                left_layers = [
                    name for name, g in r.state._layer_groups.items()
                    if g.property == "left_stick"
                ]
                right_layers = [
                    name for name, g in r.state._layer_groups.items()
                    if g.property == "right_stick"
                ]
                assert len(left_layers) == 0, f"Expected no left stick layers, got {left_layers}"
                assert len(right_layers) > 0, f"Expected right stick layers to remain"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_left_stick_stop_with_transition(on_success, on_failure):
    """left_stick.stop(200) transitions to neutral over time"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, -1).run()

    def do_stop():
        r.left_stick.stop(200)

        def check():
            try:
                pos_l = r.state.left_stick
                pos_r = r.state.right_stick
                assert abs(pos_l.x) < 0.1, f"Expected left ~0 after transition, got {pos_l.x}"
                assert abs(pos_r.y - (-1.0)) < 0.05, f"Expected right y=-1 unchanged, got {pos_r.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after("400ms", check)

    cron.after(VISIBLE_MS, do_stop)


def test_right_stick_stop_clears_only_right(on_success, on_failure):
    """right_stick.stop() clears right stick but leaves left stick"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()
    r.right_stick.to(0, -1).run()

    def do_stop():
        r.right_stick.stop()

        def check():
            try:
                pos_l = r.state.left_stick
                pos_r = r.state.right_stick
                assert abs(pos_l.x - 1.0) < 0.05, f"Expected left x=1, got {pos_l.x}"
                assert abs(pos_r.x) < 0.01, f"Expected right x=0, got {pos_r.x}"
                assert abs(pos_r.y) < 0.01, f"Expected right y=0, got {pos_r.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_new_operation_after_stick_stop(on_success, on_failure):
    """Can set new values after left_stick.stop()"""
    setup()
    r = rig()
    r.left_stick.to(1, 0).run()

    def do_stop_and_set():
        r.left_stick.stop()
        r.left_stick.to(0, 1).run()

        def check():
            try:
                pos = r.state.left_stick
                assert abs(pos.y - 1.0) < 0.05, f"Expected y=1.0, got {pos.y}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop_and_set)


def test_left_trigger_stop_clears_only_left(on_success, on_failure):
    """left_trigger.stop() clears left trigger but leaves right trigger and sticks"""
    setup()
    r = rig()
    r.left_trigger.to(0.8).run()
    r.right_trigger.to(0.5).run()
    r.left_stick.to(1, 0).run()

    def do_stop():
        r.left_trigger.stop()

        def check():
            try:
                assert abs(r.state.left_trigger) < 0.01, f"Expected lt=0, got {r.state.left_trigger}"
                assert abs(r.state.right_trigger - 0.5) < 0.05, f"Expected rt=0.5, got {r.state.right_trigger}"
                pos_l = r.state.left_stick
                assert abs(pos_l.x - 1.0) < 0.05, f"Expected left stick x=1, got {pos_l.x}"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


def test_left_trigger_stop_clears_layers(on_success, on_failure):
    """left_trigger.stop() removes left trigger layers but not others"""
    setup()
    r = rig()
    r.left_trigger.to(0.5).run()
    r.left_trigger.offset.add(0.2).run()
    r.right_trigger.to(0.3).run()

    def do_stop():
        r.left_trigger.stop()

        def check():
            try:
                lt_layers = [
                    name for name, g in r.state._layer_groups.items()
                    if g.property == "left_trigger"
                ]
                rt_layers = [
                    name for name, g in r.state._layer_groups.items()
                    if g.property == "right_trigger"
                ]
                assert len(lt_layers) == 0, f"Expected no left trigger layers, got {lt_layers}"
                assert len(rt_layers) > 0, f"Expected right trigger layers to remain"
                on_success()
            except Exception as e:
                on_failure(str(e))
            finally:
                teardown()

        cron.after(VISIBLE_MS, check)

    cron.after(VISIBLE_MS, do_stop)


STOP_RESET_TESTS = [
    ("stop clears to neutral", test_stop_clears_to_neutral),
    ("stop clears layers", test_stop_clears_layers),
    ("stop stops frame loop", test_stop_stops_frame_loop),
    ("reset clears everything", test_reset_clears_everything),
    ("stop with transition", test_stop_with_transition),
    ("new operation after stop", test_new_operation_after_stop),
    ("left_stick.stop clears only left", test_left_stick_stop_clears_only_left),
    ("left_stick.stop clears layers", test_left_stick_stop_clears_layers),
    ("left_stick.stop with transition", test_left_stick_stop_with_transition),
    ("right_stick.stop clears only right", test_right_stick_stop_clears_only_right),
    ("new op after stick stop", test_new_operation_after_stick_stop),
    ("left_trigger.stop clears only left", test_left_trigger_stop_clears_only_left),
    ("left_trigger.stop clears layers", test_left_trigger_stop_clears_layers),
]
