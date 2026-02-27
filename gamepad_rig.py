"""Gamepad Rig - Talon Actions

Provides Talon actions for gamepad control using fluent API.
"""

from talon import Module, actions
from typing import Any
from .src import rig as get_rig, reload_rig
from .src import gamepad_api

mod = Module()

STICK_DIRECTION_MAP = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, 1),
    "down": (0, -1),
    "up_left": (-1, 1),
    "up_right": (1, 1),
    "down_left": (-1, -1),
    "down_right": (1, -1),
}


def _parse_direction(direction: str) -> tuple:
    """Parse a cardinal direction string to (x, y) tuple"""
    direction = direction.lower().replace(" ", "_")
    if direction not in STICK_DIRECTION_MAP:
        raise ValueError(
            f"Unknown direction '{direction}'. "
            f"Valid: {sorted(STICK_DIRECTION_MAP.keys())}"
        )
    return STICK_DIRECTION_MAP[direction]


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

    def gamepad_rig_reload() -> None:
        """Reload the gamepad rig (reset state)"""
        reload_rig()

    def gamepad_rig_tests():
        """Toggle gamepad rig test runner UI"""
        from .tests.main import toggle_test_ui
        toggle_test_ui()

    def gamepad_rig_stop(transition_ms: int = None) -> None:
        """Stop all gamepad activity
        
        Args:
            transition_ms: Duration to transition to neutral (None = instant)
        """
        gamepad = actions.user.gamepad_rig()
        gamepad.stop(ms=transition_ms)

    # Convenience actions for common operations
    def gamepad_rig_left_stick_to(
        x: float,
        y: float,
        over_ms: int = None,
        easing: str = None
    ) -> None:
        """Move left stick to position
        
        Args:
            x: Target x position [-1, 1]
            y: Target y position [-1, 1]
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.to(x, y)
        
        if over_ms is not None:
            builder = builder.over(over_ms, easing or "linear")

    def gamepad_rig_right_stick_to(
        x: float,
        y: float,
        over_ms: int = None,
        easing: str = None
    ) -> None:
        """Move right stick to position
        
        Args:
            x: Target x position [-1, 1]
            y: Target y position [-1, 1]
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.to(x, y)
        
        if over_ms is not None:
            builder = builder.over(over_ms, easing or "linear")

    def gamepad_rig_left_trigger_to(
        value: float,
        over_ms: int = None,
        easing: str = None
    ) -> None:
        """Set left trigger value
        
        Args:
            value: Target trigger value [0, 1]
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_trigger.to(value)
        
        if over_ms is not None:
            builder = builder.over(over_ms, easing or "linear")

    def gamepad_rig_right_trigger_to(
        value: float,
        over_ms: int = None,
        easing: str = None
    ) -> None:
        """Set right trigger value

        Args:
            value: Target trigger value [0, 1]
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_trigger.to(value)

        if over_ms is not None:
            builder = builder.over(over_ms, easing or "linear")

    def gamepad_rig_reset() -> None:
        """Reset the gamepad rig to default state (all neutral)"""
        actions.user.gamepad_rig().reset()

    # =====================================================================
    # Left Thumb - Direction & Rotation
    # =====================================================================

    def gamepad_rig_left_stick(
        direction: str,
        magnitude: float = None,
        force: bool = False,
        over_ms: int = None,
        easing: str = None,
    ) -> None:
        """Push left stick in cardinal direction

        Keeps current magnitude unless force=True or starting from idle.

        Args:
            direction: "left", "right", "up", "down", "up_left", etc.
            magnitude: Target magnitude 0-1 (None = keep current, or 1 if idle)
            force: If True, override current magnitude with magnitude param
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        dx, dy = _parse_direction(direction)
        gamepad = actions.user.gamepad_rig()
        if magnitude is not None or force:
            mag = magnitude if magnitude is not None else 1
            builder = gamepad.left_stick.to(dx * mag, dy * mag)
        else:
            builder = gamepad.left_stick.direction.to(dx, dy)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    def gamepad_rig_left_stick_reverse(
        over_ms: int = None, easing: str = None
    ) -> None:
        """Reverse left stick direction (180° rotation)

        Args:
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.direction.by(180)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    def gamepad_rig_left_stick_rotate(
        degrees: float, over_ms: int = None, easing: str = None
    ) -> None:
        """Rotate left stick direction by degrees

        Args:
            degrees: Degrees to rotate (positive = counter-clockwise)
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.direction.by(degrees)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    # =====================================================================
    # Left Thumb - Magnitude
    # =====================================================================

    def gamepad_rig_left_stick_magnitude_to(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Set left stick magnitude to absolute value

        Args:
            value: Target magnitude [0, 1]
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.magnitude.to(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    def gamepad_rig_left_stick_magnitude_add(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Add to left stick magnitude

        Args:
            value: Amount to add
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.magnitude.by(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    def gamepad_rig_left_stick_magnitude_mul(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Multiply left stick magnitude

        Args:
            value: Multiplier
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.left_stick.magnitude.scale.to(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    # =====================================================================
    # Right Thumb - Direction & Rotation
    # =====================================================================

    def gamepad_rig_right_stick(
        direction: str,
        magnitude: float = None,
        force: bool = False,
        over_ms: int = None,
        easing: str = None,
    ) -> None:
        """Push right stick in cardinal direction

        Keeps current magnitude unless force=True or starting from idle.

        Args:
            direction: "left", "right", "up", "down", "up_left", etc.
            magnitude: Target magnitude 0-1 (None = keep current, or 1 if idle)
            force: If True, override current magnitude with magnitude param
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        dx, dy = _parse_direction(direction)
        gamepad = actions.user.gamepad_rig()
        if magnitude is not None or force:
            mag = magnitude if magnitude is not None else 1
            builder = gamepad.right_stick.to(dx * mag, dy * mag)
        else:
            builder = gamepad.right_stick.direction.to(dx, dy)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    def gamepad_rig_right_stick_reverse(
        over_ms: int = None, easing: str = None
    ) -> None:
        """Reverse right stick direction (180° rotation)

        Args:
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.direction.by(180)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    def gamepad_rig_right_stick_rotate(
        degrees: float, over_ms: int = None, easing: str = None
    ) -> None:
        """Rotate right stick direction by degrees

        Args:
            degrees: Degrees to rotate (positive = counter-clockwise)
            over_ms: Duration in ms (optional)
            easing: Easing function (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.direction.by(degrees)
        if over_ms is not None:
            builder.over(over_ms, easing or "linear")

    # =====================================================================
    # Right Stick - Magnitude
    # =====================================================================

    def gamepad_rig_right_stick_magnitude_to(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Set right stick magnitude to absolute value

        Args:
            value: Target magnitude [0, 1]
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.magnitude.to(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    def gamepad_rig_right_stick_magnitude_add(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Add to right stick magnitude

        Args:
            value: Amount to add
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.magnitude.by(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    def gamepad_rig_right_stick_magnitude_mul(
        value: float, over_ms: int = None, hold_ms: int = None, revert_ms: int = None
    ) -> None:
        """Multiply right stick magnitude

        Args:
            value: Multiplier
            over_ms: Duration in ms (optional)
            hold_ms: Hold duration before revert (optional)
            revert_ms: Revert duration (optional)
        """
        gamepad = actions.user.gamepad_rig()
        builder = gamepad.right_stick.magnitude.scale.to(value)
        if over_ms is not None:
            builder = builder.over(over_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder.revert(revert_ms)

    # =====================================================================
    # State Queries
    # =====================================================================

    def gamepad_rig_state() -> Any:
        """Get full gamepad rig state object"""
        return actions.user.gamepad_rig().state

    def gamepad_rig_state_left_stick() -> Any:
        """Get current left stick position as (x, y)"""
        state = actions.user.gamepad_rig().state
        lt = state.left_stick
        return (lt.x, lt.y)

    def gamepad_rig_state_right_stick() -> Any:
        """Get current right stick position as (x, y)"""
        state = actions.user.gamepad_rig().state
        rt = state.right_stick
        return (rt.x, rt.y)

    def gamepad_rig_state_left_trigger() -> float:
        """Get current left trigger value"""
        return actions.user.gamepad_rig().state.left_trigger

    def gamepad_rig_state_right_trigger() -> float:
        """Get current right trigger value"""
        return actions.user.gamepad_rig().state.right_trigger

    def gamepad_rig_state_left_stick_magnitude() -> float:
        """Get current left stick magnitude"""
        return actions.user.gamepad_rig().state.left_stick.magnitude()

    def gamepad_rig_state_left_stick_direction() -> Any:
        """Get current left stick direction as (x, y) unit vector"""
        d = actions.user.gamepad_rig().state.left_stick.normalized()
        return (d.x, d.y)

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

    # =====================================================================
    # Button Actions
    # =====================================================================

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

    def gamepad_rig_button_valid() -> list:
        """Get list of valid gamepad button names"""
        return gamepad_api.get_valid_buttons()

    # =====================================================================
    # Device Lifecycle
    # =====================================================================

    def gamepad_rig_connect() -> None:
        """Connect the virtual gamepad device (plugs in to Windows)"""
        gamepad_api.connect_gamepad()

    def gamepad_rig_disconnect() -> None:
        """Disconnect the virtual gamepad device (unplugs from Windows).
        Also reloads the rig state."""
        reload_rig()
        gamepad_api.disconnect_gamepad()

    def gamepad_rig_is_connected() -> bool:
        """Check if the virtual gamepad device is currently connected"""
        return gamepad_api.is_connected()
