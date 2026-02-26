"""Tests for gamepad button press/release — real hardware output."""

from talon import cron
from .helpers import setup, teardown
from ..src import gamepad_api

HOLD_MS = "200ms"

ALL_BUTTONS = [
    "a", "b", "x", "y",
    "dpad_up", "dpad_down", "dpad_left", "dpad_right",
    "lb", "rb", "l3", "r3",
    "start", "select",
]


def test_all_buttons(on_success, on_failure):
    """Press and release every button"""
    setup()
    buttons = list(ALL_BUTTONS)
    idx = {"value": 0}

    def press_next():
        if idx["value"] >= len(buttons):
            teardown()
            on_success()
            return

        btn = buttons[idx["value"]]
        try:
            gamepad_api.press_button(btn)
        except Exception as e:
            teardown()
            on_failure(f"{btn}: {e}")
            return

        def release():
            try:
                gamepad_api.release_button(btn)
            except Exception as e:
                teardown()
                on_failure(f"{btn} release: {e}")
                return
            idx["value"] += 1
            cron.after("50ms", press_next)

        cron.after(HOLD_MS, release)

    press_next()


def test_multiple_buttons(on_success, on_failure):
    """Multiple buttons pressed simultaneously"""
    setup()
    try:
        gamepad_api.press_button("a")
        gamepad_api.press_button("b")
        gamepad_api.press_button("x")
    except Exception as e:
        teardown()
        on_failure(str(e))
        return

    def release():
        try:
            gamepad_api.release_button("a")
            gamepad_api.release_button("b")
            gamepad_api.release_button("x")
            on_success()
        except Exception as e:
            on_failure(str(e))
        finally:
            teardown()

    cron.after(HOLD_MS, release)


BUTTON_TESTS = [
    ("all buttons", test_all_buttons),
    ("multiple buttons", test_multiple_buttons),
]
