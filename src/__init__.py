"""Gamepad Rig - Entry point and module exports

Example usage:
    from .gamepad.src import rig

    def my_action():
        gamepad = rig()
        gamepad.left_stick.to(1, 0)  # Full right
        gamepad.left_trigger.to(0.5)  # Half press
"""

from typing import Optional
import os
import time

# Module-level references (set by _build_classes)
GamepadState = None
GamepadBuilder = None
GamepadBuilderConfig = None
LifecyclePhase = None
LayerType = None

_core = None
_global_state = None
_initialized = False


def _on_ready():
    global _core, _initialized
    from talon import actions
    _core = actions.user.rig_core()

    # Build all classes that depend on rig-core
    from . import core as core_module
    from . import contracts
    from . import mode_operations
    from . import layer_group
    from . import state
    from . import builder

    core_module._build_classes(_core)
    contracts._build_classes(_core)
    mode_operations._build_classes(_core)
    layer_group._build_classes(_core)
    state._build_classes(_core)
    builder._build_classes(_core)

    # Update module-level references
    global GamepadState, GamepadBuilder, GamepadBuilderConfig, LifecyclePhase, LayerType
    GamepadState = state.GamepadState
    GamepadBuilder = builder.GamepadBuilder
    GamepadBuilderConfig = contracts.GamepadBuilderConfig
    LifecyclePhase = contracts.LifecyclePhase
    LayerType = contracts.LayerType

    _initialized = True


from talon import app
app.register("ready", _on_ready)


def _get_global_state():
    """Get or create the global gamepad state"""
    global _global_state
    if _global_state is None:
        _global_state = GamepadState()
    return _global_state


class StopHandle:
    """Handle returned by stop() that allows adding callbacks via .then()"""

    def __init__(self, state):
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
    def left_stick(self):
        """Left stick property accessor (base layer)"""
        return GamepadBuilder(self._state).left_stick

    @property
    def right_stick(self):
        """Right stick property accessor (base layer)"""
        return GamepadBuilder(self._state).right_stick

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

    def layer(self, name: str, order: Optional[int] = None):
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

    def reverse(self, ms: Optional[float] = None, easing: str = "linear"):
        """Reverse direction of all stick movement (base + layers)

        Only affects sticks (VECTOR property kind). Triggers are unaffected.

        Args:
            ms: Optional transition duration. If None, reverses instantly.
                If provided, creates smooth transition by emitting decay copies.
            easing: Easing function for gradual reversal

        Examples:
            rig.reverse()         # Instant 180° flip
            rig.reverse(400)      # Smooth turn over 400ms
        """
        from .contracts import validate_timing
        ms = validate_timing(ms, 'ms', method='reverse') if ms is not None else None

        if ms is not None:
            self._emit_reverse_copies(ms, easing)

        self._reverse_all_directions()

    def _emit_reverse_copies(self, ms: float, easing: str = "linear"):
        """Emit decay copies of stick layers for smooth reverse transition.

        Creates 2x copies of each stick layer that fade out over the duration,
        bridging from current velocity to reversed velocity smoothly.
        """
        import time as _time

        emitted_base = {"left_stick": False, "right_stick": False}

        for layer_name in list(self._state._layer_groups.keys()):
            group = self._state._layer_groups.get(layer_name)
            if group is None:
                continue

            # Only emit for stick layers (VECTOR kind)
            if group.property not in ("left_stick", "right_stick"):
                continue

            if group.is_base:
                # Base stick layers with additive operators: emit contribution as offset
                if group.builders and group.builders[0].config.operator in ("by", "add"):
                    current_value = group.get_current_value()
                    prop = group.property
                    base_val = (self._state._base_left_stick if prop == "left_stick"
                                else self._state._base_right_stick)
                    contribution_x = current_value.x - base_val.x if current_value else 0
                    contribution_y = current_value.y - base_val.y if current_value else 0

                    for i in range(2):
                        emit_name = f"emit.base.{prop}.{int(_time.perf_counter() * 1000000)}"
                        b = GamepadBuilder(self._state, layer=emit_name)
                        b.config.mode = "offset"
                        b.config.property = prop
                        b.config.operator = "to"
                        b.config.value = (contribution_x, contribution_y)
                        b.config.revert_ms = ms
                        b.config.revert_easing = easing
                        b._execute()
                        if emit_name in self._state._layer_groups:
                            self._state._layer_groups[emit_name].is_emit_layer = True

                    emitted_base[prop] = True
                continue

            # Non-base stick layers: copy twice as emit layers that decay
            try:
                for i in range(2):
                    copy_name = f"emit.copy.{layer_name}.{int(_time.perf_counter() * 1000000)}"
                    copy_group = group.copy(copy_name)
                    copy_group.is_emit_layer = True
                    for builder in copy_group.builders:
                        builder.group = copy_group
                    self._state._layer_groups[copy_name] = copy_group
                    self._state._layer_orders[copy_name] = (
                        copy_group.order if copy_group.order is not None
                        else self._state._next_auto_order
                    )
                    self._state.trigger_revert(copy_name, ms, easing)
            except Exception:
                pass

        # Emit 2x base stick velocity for sticks that didn't have base layer emissions
        for prop in ("left_stick", "right_stick"):
            if emitted_base[prop]:
                continue
            base_val = (self._state._base_left_stick if prop == "left_stick"
                        else self._state._base_right_stick)
            vel_x = base_val.x * 2
            vel_y = base_val.y * 2
            if abs(vel_x) > 0.001 or abs(vel_y) > 0.001:
                emit_name = f"emit.base.{prop}.{int(_time.perf_counter() * 1000000)}"
                b = GamepadBuilder(self._state, layer=emit_name)
                b.config.mode = "offset"
                b.config.property = prop
                b.config.operator = "to"
                b.config.value = (vel_x, vel_y)
                b.config.revert_ms = ms
                b.config.revert_easing = easing
                b._execute()
                if emit_name in self._state._layer_groups:
                    self._state._layer_groups[emit_name].is_emit_layer = True

    def _reverse_all_directions(self):
        """Reverse base stick vectors and all layer accumulated values/builders"""
        # Core handles layer groups (VECTOR property_kind, skip emit layers)
        self._state.reverse_all_directions()

        # Gamepad-specific: flip base stick vectors
        self._state._base_left_stick = self._state._base_left_stick * -1
        self._state._base_right_stick = self._state._base_right_stick * -1

        # Flush to hardware immediately - unlike mouse-rig, gamepad sticks can be
        # held at a fixed offset with no frame loop running, so reverse needs to
        # push the new state to the virtual controller synchronously.
        self._state._flush_to_hardware()

    def stop(self, ms: Optional[float] = None, easing: str = "linear") -> StopHandle:
        """Stop everything: bake all layers, clear builders, return to neutral

        Args:
            ms: Optional duration to transition over. If None, stops immediately.
            easing: Easing function for gradual deceleration

        Returns:
            StopHandle: Handle that allows chaining .then(callback)
        """
        from .contracts import validate_timing
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
        from .contracts import (
            GamepadRigAttributeError,
            find_closest_match,
            VALID_RIG_METHODS,
            VALID_RIG_PROPERTIES,
        )
        all_valid = VALID_RIG_METHODS + VALID_RIG_PROPERTIES

        suggestion = find_closest_match(name, all_valid)

        msg = f"Rig has no attribute '{name}'"
        if suggestion:
            msg += f"\n\nDid you mean: '{suggestion}'?"
        else:
            msg += f"\n\nAvailable properties: {', '.join(VALID_RIG_PROPERTIES)}"
            msg += f"\nAvailable methods: {', '.join(VALID_RIG_METHODS)}"

        raise GamepadRigAttributeError(msg)


class _BehaviorAccessor:
    """Helper to allow behavior to be used as property or method"""

    def __init__(self, state, behavior: str):
        self._state = state
        self._behavior = behavior

    def __call__(self, *args):
        """Called when used as method: rig.stack(3)"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        builder.config.behavior_args = args
        return builder

    @property
    def left_stick(self):
        """Property access: rig.stack.left_stick"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.left_stick

    @property
    def right_stick(self):
        """Property access: rig.stack.right_stick"""
        builder = GamepadBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.right_stick

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
        gamepad.left_stick.to(1, 0).over(1000)
        gamepad.left_trigger.to(1).over(100).revert(100)
    """
    return Rig()


def reset_rig():
    """Reset rig state without reloading files.

    Stops all active movements and clears state.
    Does NOT disconnect the virtual device.
    """
    global _global_state

    if _global_state is not None:
        try:
            _global_state.stop(transition_ms=0)
            _global_state._stop_frame_loop()
        except Exception:
            pass
        _global_state = None


def reload_rig():
    """Clear the rig state and touch all Python files to force Talon reload

    Manually triggers reload by:
    1. Stopping active movements and clearing state
    2. Touching all Python files in src/ and tests/ to trigger Talon's file watcher
    """
    from .ui import show_reloading_notification

    reset_rig()

    # Show brief notification before reload
    show_reloading_notification()
    # Small delay to ensure notification is visible before reload
    time.sleep(0.1)

    # Touch all Python files in src/ and tests/ to trigger Talon's file watcher
    # Touch src/__init__.py FIRST so module reinitializes properly
    src_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(src_dir)

    # Touch src/__init__.py first (order matters for Talon's reload)
    init_file = os.path.join(src_dir, '__init__.py')
    if os.path.exists(init_file):
        try:
            os.utime(init_file, None)
        except Exception:
            pass

    # Then touch other src/ files (skip ui.py so notification cron job can execute)
    for filename in os.listdir(src_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'ui.py'):
            filepath = os.path.join(src_dir, filename)
            try:
                os.utime(filepath, None)
            except Exception:
                pass

    # Then touch tests/ files
    tests_dir = os.path.join(parent_dir, 'tests')
    if os.path.exists(tests_dir):
        for filename in os.listdir(tests_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(tests_dir, filename)
                try:
                    os.utime(filepath, None)
                except Exception:
                    pass


__all__ = ['rig', 'Rig', 'StopHandle', 'GamepadBuilder', 'GamepadState', 'reset_rig', 'reload_rig']
