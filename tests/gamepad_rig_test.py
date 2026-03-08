"""Internal gamepad state for tests.

Stores stick and trigger values received from Windows/hardware
so deadzone tests can read back what the OS actually reports,
without depending on community gamepad_tester actions.
"""

from talon import Context, Module

mod = Module()
ctx = Context()

mod.tag("gamepad_rig_test", desc="Enables gamepad rig test listener")


def enable():
    ctx.tags = ["user.gamepad_rig_test"]


def disable():
    ctx.tags = []
    sticks["left"] = (0.0, 0.0)
    sticks["right"] = (0.0, 0.0)
    triggers["l2"] = 0.0
    triggers["r2"] = 0.0


sticks: dict[str, tuple[float, float]] = {
    "left": (0.0, 0.0),
    "right": (0.0, 0.0),
}

triggers: dict[str, float] = {
    "l2": 0.0,
    "r2": 0.0,
}


@mod.action_class
class Actions:
    def gamepad_rig_test_record(input_type: str, id: str, x: float, y: float):
        """Store raw hardware state for testing (stick or trigger)"""
        if input_type == "stick":
            sticks[id] = (x, y)
        elif input_type == "trigger":
            triggers[id] = x
