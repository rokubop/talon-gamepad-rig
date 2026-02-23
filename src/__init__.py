"""Gamepad Rig - Entry point and module exports

Example usage:
    from .gamepad.src import rig

    def my_action():
        gamepad = rig()
        gamepad.left_thumb.to(1, 0)  # Full right
        gamepad.left_trigger.to(0.5)  # Half press
"""

from typing import Optional
import time
from .state import GamepadState
from .builder import GamepadBuilder
from .contracts import (
    validate_timing,
    RigAttributeError,
    find_closest_match,
    VALID_RIG_METHODS,
    VALID_RIG_PROPERTIES,
)

_global_state: Optional[GamepadState] = None


def _get_global_state() -> GamepadState:
    """Get or create the global gamepad state"""
    global _global_state
    if _global_state is None:
        _global_state = GamepadState()
    return _global_state


class StopHandle:
    """Handle returned by stop() that allows adding callbacks via .then()"""

    def __init__(self, state: GamepadState):
        self._state = state

    def then(self, callback):
        """Add a callback to be executed when the system fully stops

        The callback will only fire when:
        - The deceleration completes (if a transition time was specified)
        - The frame loop stops naturally
        - No other operations interrupt the stop

        Args:
            callback: Function to call when stopped
        """
        self._state.add_stop_callback(callback)
        return self


class Rig:
    """Main entry point for gamepad rig operations

    All property accesses and methods return GamepadBuilder for fluent chaining.
    """

    def __init__(self):
        self._state = _get_global_state()

    # ========================================================================
    # PROPERTY ACCESSORS (base layer)
    # ========================================================================

    @property
    def left_thumb(self):
        """Left thumbstick property accessor (base layer)"""
        return GamepadBuilder(self._state).left_thumb

    @property
    def right_thumb(self):
        """Right thumbstick property accessor (base layer)"""
        return GamepadBuilder(self._state).right_thumb

    @property
    def left_trigger(self):
        """Left trigger property accessor (base layer)"""
        return GamepadBuilder(self._state).left_trigger

    @property
    def right_trigger(self):
        """Right trigger property accessor (base layer)"""
        return GamepadBuilder(self._state).right_trigger

    # ========================================================================
    # LAYER METHOD
    # ========================================================================

    def layer(self, name: str, order: Optional[int] = None) -> GamepadBuilder:
        """Create a user layer

        Args:
            name: Layer name
            order: Optional execution order (lower numbers execute first)
        """
        return GamepadBuilder(self._state, layer=name, order=order)

    # ========================================================================
    # BEHAVIOR SUGAR (returns builder with behavior pre-set)
    # ========================================================================

    @property
    def stack(self):
        """Stack behavior accessor"""
        return _BehaviorAccessor(self._state, "stack")

    @property
    def replace(self):
        """Replace behavior accessor"""
        return _BehaviorAccessor(self._state, "replace")

    @property
    def queue(self):
        """Queue behavior accessor"""
        return _BehaviorAccessor(self._state, "queue")

    @property
    def throttle(self):
        """Throttle behavior accessor"""
        return _BehaviorAccessor(self._state, "throttle")

    @property
    def debounce(self):
        """Debounce behavior accessor"""
        return _BehaviorAccessor(self._state, "debounce")

    # ========================================================================
    # SPECIAL OPERATIONS
    # ========================================================================

    def stop(self, ms: Optional[float] = None, easing: str = "linear") -> StopHandle:
        """Stop everything: bake all layers, clear builders, return to neutral

        Args:
            ms: Optional duration to transition over. If None, stops immediately.
            easing: Easing function for gradual deceleration

        Returns:
            StopHandle: Handle that allows chaining .then(callback)
        """
        ms = validate_timing(ms, 'ms', method='stop')
        self._state.stop(transition_ms=ms, easing=easing)
        return StopHandle(self._state)

    def reset(self):
        """Reset everything to default state

        Clears all layers, resets sticks to (0, 0), triggers to 0,
        and clears all tracking.

        Example:
            rig.reset()  # Clean slate
        """
        self._state.reset()

    def bake(self):
        """Bake all active builders to base state"""
        self._state.bake_all()

    # ========================================================================
    # STATE ACCESS
    # ========================================================================

    @property
    def state(self):
        """Access to current computed state"""
        return self._state

    def __getattr__(self, name: str):
        """Handle unknown attributes with helpful error messages"""
        all_valid = VALID_RIG_METHODS + VALID_RIG_PROPERTIES

        suggestion = find_closest_match(name, all_valid)

        msg = f"Rig has no attribute '{name}'"
        if suggestion:
            msg += f"\n\nDid you mean: '{suggestion}'?"
        else:
            msg += f"\n\nAvailable properties: {', '.join(VALID_RIG_PROPERTIES)}"
            msg += f"\nAvailable methods: {', '.join(VALID_RIG_METHODS)}"

        raise RigAttributeError(msg)


class _BehaviorAccessor:
    """Helper to allow behavior to be used as property or method"""

    def __init__(self, state: GamepadState, behavior: str):
        self._state = state
        self._behavior = behavior

    def __call__(self, *args) -> GamepadBuilder:
        """Called when used as method: rig.stack(3)"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        builder.config.behavior_args = args
        return builder

    @property
    def left_thumb(self):
        """Property access: rig.stack.left_thumb"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.left_thumb

    @property
    def right_thumb(self):
        """Property access: rig.stack.right_thumb"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.right_thumb

    @property
    def left_trigger(self):
        """Property access: rig.stack.left_trigger"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.left_trigger

    @property
    def right_trigger(self):
        """Property access: rig.stack.right_trigger"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.right_trigger


def rig() -> Rig:
    """Get a new Rig instance

    Returns:
        Rig instance for fluent API calls

    Example:
        gamepad = rig()
        gamepad.left_thumb.to(1, 0).over(1000)
        gamepad.left_trigger.to(1).over(100).revert(100)
    """
    return Rig()


def reload_rig():
    """Clear the rig state

    Stops all active movements and resets state.
    """
    global _global_state

    if _global_state is not None:
        try:
            _global_state.stop(transition_ms=0)
            _global_state._stop_frame_loop()
        except Exception as e:
            print(f"Error stopping gamepad rig: {e}")
        _global_state = None


def get_version() -> str:
    """Get gamepad rig version"""
    return "0.1.0-alpha"


__all__ = ['rig', 'Rig', 'StopHandle', 'GamepadBuilder', 'GamepadState', 'reload_rig', 'get_version']
