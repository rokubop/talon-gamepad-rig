"""Gamepad API implementation using vgamepad

Provides abstraction layer for virtual Xbox controller via vgamepad library.
Supports analog sticks and triggers with float values.
"""

from typing import Optional
from talon import settings

# Try to import vgamepad, but allow the module to load even if not available
# This allows the code to be parsed/tested without vgamepad installed
try:
    import vgamepad as vg
    _vgamepad_available = True
except ImportError:
    _vgamepad_available = False
    print("Warning: vgamepad library not found. Gamepad rig will not function.")
    print("Install with: pip install vgamepad")


# Global gamepad instance (only created via connect_gamepad)
_gamepad: Optional['vg.VX360Gamepad'] = None


def _require_connected():
    """Raise if gamepad is not connected. Call connect_gamepad() first."""
    if _gamepad is None:
        raise RuntimeError(
            "Virtual gamepad is not connected. "
            "Call connect_gamepad() first."
        )


def update_left_stick(x: float, y: float) -> None:
    """Update left analog stick position
    
    Args:
        x: Horizontal axis, range [-1, 1] (left to right)
        y: Vertical axis, range [-1, 1] (down to up)
    """
    _require_connected()
    # Clamp values to valid range
    x = max(-1.0, min(1.0, x))
    y = max(-1.0, min(1.0, y))
    _gamepad.left_joystick_float(x_value_float=x, y_value_float=y)
    _gamepad.update()


def update_right_stick(x: float, y: float) -> None:
    """Update right analog stick position
    
    Args:
        x: Horizontal axis, range [-1, 1] (left to right)
        y: Vertical axis, range [-1, 1] (down to up)
    """
    _require_connected()
    # Clamp values to valid range
    x = max(-1.0, min(1.0, x))
    y = max(-1.0, min(1.0, y))
    _gamepad.right_joystick_float(x_value_float=x, y_value_float=y)
    _gamepad.update()


def update_left_trigger(value: float) -> None:
    """Update left trigger value
    
    Args:
        value: Trigger value, range [0, 1] (released to fully pressed)
    """
    _require_connected()
    # Clamp value to valid range
    value = max(0.0, min(1.0, value))
    _gamepad.left_trigger_float(value_float=value)
    _gamepad.update()


def update_right_trigger(value: float) -> None:
    """Update right trigger value
    
    Args:
        value: Trigger value, range [0, 1] (released to fully pressed)
    """
    _require_connected()
    # Clamp value to valid range
    value = max(0.0, min(1.0, value))
    _gamepad.right_trigger_float(value_float=value)
    _gamepad.update()


def _compensate_stick_deadzone(value: float) -> float:
    """Compensate for Windows/XInput stick deadzone on a single axis.

    Maps logical [-1, 1] to hardware values that arrive as [-1, 1]
    after Windows applies its deadzone. Values near zero stay zero.
    """
    deadzone = settings.get("user.gamepad_rig_stick_deadzone", 0.24)
    if deadzone <= 0:
        return value
    if abs(value) < 0.001:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) * (1.0 - deadzone) + deadzone)


def _compensate_trigger_deadzone(value: float) -> float:
    """Compensate for Windows/XInput trigger deadzone.

    Maps logical [0, 1] to hardware values that arrive as [0, 1]
    after Windows applies its trigger threshold.
    """
    deadzone = settings.get("user.gamepad_rig_trigger_deadzone", 0.25)
    if deadzone <= 0:
        return value
    if value < 0.001:
        return 0.0
    return value * (1.0 - deadzone) + deadzone


def update_all(
    lt_x: float, lt_y: float,
    rt_x: float, rt_y: float,
    lt_val: float, rt_val: float
) -> None:
    """Update all gamepad values in a single batch (one update() call per frame)

    Args:
        lt_x, lt_y: Left stick axes [-1, 1]
        rt_x, rt_y: Right stick axes [-1, 1]
        lt_val: Left trigger [0, 1]
        rt_val: Right trigger [0, 1]
    """
    if _gamepad is None:
        return
    _gamepad.left_joystick_float(
        x_value_float=max(-1.0, min(1.0, _compensate_stick_deadzone(lt_x))),
        y_value_float=max(-1.0, min(1.0, _compensate_stick_deadzone(lt_y)))
    )
    _gamepad.right_joystick_float(
        x_value_float=max(-1.0, min(1.0, _compensate_stick_deadzone(rt_x))),
        y_value_float=max(-1.0, min(1.0, _compensate_stick_deadzone(rt_y)))
    )
    _gamepad.left_trigger_float(value_float=max(0.0, min(1.0, _compensate_trigger_deadzone(lt_val))))
    _gamepad.right_trigger_float(value_float=max(0.0, min(1.0, _compensate_trigger_deadzone(rt_val))))
    _gamepad.update()


def reset_gamepad() -> None:
    """Reset gamepad to neutral state (all sticks centered, all triggers released)"""
    if _gamepad is None:
        return
    _gamepad.reset()
    _gamepad.update()


def connect_gamepad() -> None:
    """Connect the virtual gamepad device (plugs in to Windows)"""
    global _gamepad
    if not _vgamepad_available:
        raise RuntimeError(
            "vgamepad library is not installed. "
            "Install with: pip install vgamepad"
        )
    if _gamepad is None:
        _gamepad = vg.VX360Gamepad()


def disconnect_gamepad() -> None:
    """Disconnect the virtual gamepad device (unplugs from Windows)"""
    global _gamepad
    if _gamepad is not None:
        _gamepad.reset()
        _gamepad.update()
        _gamepad = None


def is_connected() -> bool:
    """Check if the virtual gamepad device is currently connected"""
    return _gamepad is not None


def is_available() -> bool:
    """Check if vgamepad is available"""
    return _vgamepad_available


# =============================================================================
# Button Support
# =============================================================================

BUTTON_MAP = {}

if _vgamepad_available:
    BUTTON_MAP = {
        "a": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
        "b": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
        "x": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
        "y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
        "dpad_up": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
        "dpad_down": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
        "dpad_left": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
        "dpad_right": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
        "lb": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
        "rb": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
        "l3": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
        "r3": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
        "start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
        "select": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
        "home": vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    }


def _resolve_button(button: str):
    """Resolve button name to vgamepad constant"""
    button = button.lower()
    if button not in BUTTON_MAP:
        raise ValueError(
            f"Unknown button '{button}'. "
            f"Valid buttons: {sorted(BUTTON_MAP.keys())}"
        )
    return BUTTON_MAP[button]


def press_button(button: str) -> None:
    """Press a gamepad button

    Args:
        button: Button name (e.g. "a", "b", "x", "y", "dpad_up", "left_shoulder")
    """
    _require_connected()
    _gamepad.press_button(button=_resolve_button(button))
    _gamepad.update()


def release_button(button: str) -> None:
    """Release a gamepad button

    Args:
        button: Button name (e.g. "a", "b", "x", "y", "dpad_up", "left_shoulder")
    """
    _require_connected()
    _gamepad.release_button(button=_resolve_button(button))
    _gamepad.update()


def get_valid_buttons() -> list[str]:
    """Get list of valid button names"""
    return sorted(BUTTON_MAP.keys())
