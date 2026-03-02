"""Gamepad Rig - Talon Actions

Provides Talon actions for gamepad control using fluent API.
"""

from talon import Module, actions
from typing import Any
from .src import rig as get_rig, reload_rig, reset_rig
from .src import gamepad_api

mod = Module()

mod.setting(
    "gamepad_rig_stick_deadzone",
    type=float,
    default=0.24,
    desc="Stick deadzone compensation. Values sent to vgamepad are scaled to bypass "
         "the Windows/XInput deadzone so that rig values map 1:1 to game input. "
         "Set to 0 to disable compensation. Default 0.24 matches Xbox XInput deadzone.",
)

mod.setting(
    "gamepad_rig_trigger_deadzone",
    type=float,
    default=0.25,
    desc="Trigger deadzone compensation. Values sent to vgamepad are scaled to bypass "
         "the Windows/XInput trigger deadzone. "
         "Set to 0 to disable compensation. Default 0.25 matches Xbox XInput trigger threshold.",
)


@mod.action_class
class Actions:
    def gamepad_rig() -> Any:
        """
        Get gamepad rig directly for advanced usage.

        ```python
        gamepad = actions.user.gamepad_rig()

        # Basic stick control
        gamepad.left_stick.to(1, 0)  # Full right
        gamepad.left_stick.to(1, 0).over(1000)  # Smooth transition

        # Magnitude/direction decomposition
        gamepad.left_stick.magnitude.to(0.5)
        gamepad.left_stick.direction.to(1, 0)
        gamepad.left_stick.direction.by(90).over(1000)  # Rotate 90° over 1s

        # Trigger control
        gamepad.left_trigger.to(1).over(100).revert(100)
        gamepad.right_trigger.to(0.5)  # Half press for aiming

        # Layer system
        gamepad.layer("aim").left_stick.magnitude.override.to(0.3)
        gamepad.layer("aim").revert(200)

        # Stop everything
        gamepad.stop()
        gamepad.stop(500)  # Smooth stop over 500ms
        ```
        """
        return get_rig()

    def gamepad_rig_button_press(button: str) -> None:
        """Press a gamepad button

        Args:
            button: Button name (e.g. "a", "b", "x", "y", "dpad_up", "left_shoulder")
        """
        gamepad_api.press_button(button)

    def gamepad_rig_button_release(button: str) -> None:
        """Release a gamepad button

        Args:
            button: Button name (e.g. "a", "b", "x", "y", "dpad_up", "left_shoulder")
        """
        gamepad_api.release_button(button)

    def gamepad_rig_connect() -> None:
        """Connect the virtual gamepad device (plugs in to Windows)"""
        gamepad_api.connect_gamepad()

    def gamepad_rig_disconnect() -> None:
        """Disconnect the virtual gamepad device (unplugs from Windows)."""
        reset_rig()
        gamepad_api.disconnect_gamepad()

    def gamepad_rig_is_connected() -> bool:
        """Check if the virtual gamepad device is currently connected"""
        return gamepad_api.is_connected()

    def gamepad_rig_state() -> Any:
        """Get full gamepad rig state object"""
        return actions.user.gamepad_rig().state

    def gamepad_rig_is_active() -> bool:
        """Check if gamepad rig has any active builders or non-neutral state"""
        state = actions.user.gamepad_rig().state
        if state._frame_loop_job is not None:
            return True
        lt = state.left_stick
        rt = state.right_stick
        if lt.x != 0 or lt.y != 0:
            return True
        if rt.x != 0 or rt.y != 0:
            return True
        if state.left_trigger != 0:
            return True
        if state.right_trigger != 0:
            return True
        return False

    def gamepad_rig_stop(transition_ms: int = None) -> None:
        """Stop all gamepad activity

        Args:
            transition_ms: Duration to transition to neutral (None = instant)
        """
        gamepad = actions.user.gamepad_rig()
        gamepad.stop(ms=transition_ms)

    def gamepad_rig_reset() -> None:
        """Reset the gamepad rig to default state (all neutral)"""
        actions.user.gamepad_rig().reset()

    def gamepad_rig_reload() -> None:
        """Reload the gamepad rig (reset state)"""
        reload_rig()

    def gamepad_rig_tests():
        """Toggle gamepad rig test runner UI"""
        from .tests.main import toggle_test_ui
        toggle_test_ui()
