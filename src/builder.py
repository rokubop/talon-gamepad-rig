"""GamepadBuilder - fluent API for gamepad control

Adapted from mouse-rig's RigBuilder. Execution happens on __del__.
"""

import math
import time
from typing import Optional, Callable, Any, TYPE_CHECKING
from .core import Vec2, is_vec2, clamp_stick_vec2, clamp_trigger_value, clamp_stick_value
from .contracts import (
    BuilderConfig,
    LifecyclePhase,
    LayerType,
    validate_timing,
    validate_has_operation,
    ConfigError,
    GamepadRigAttributeError,
    find_closest_match,
    VALID_BUILDER_METHODS,
    VALID_OPERATORS,
)
from .lifecycle import Lifecycle, PropertyAnimator
from . import rate_utils
from . import mode_operations

if TYPE_CHECKING:
    from .state import GamepadState
    from .layer_group import LayerGroup


class BehaviorProxy:
    """Proxy that allows both .queue and .queue() syntax"""

    def __init__(self, builder: 'GamepadBuilder', behavior_name: str, has_args: bool = False):
        self.builder = builder
        self.behavior_name = behavior_name
        self.has_args = has_args
        self._property_builder = None

    def __call__(self, *args, **kwargs):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method(*args, **kwargs)
        return self._property_builder if self._property_builder else self.builder

    def __getattr__(self, name):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method()
        if self._property_builder:
            return getattr(self._property_builder, name)
        return getattr(self.builder, name)


class ModeProxy:
    """Proxy for mode-based property access (.offset, .override, .scale)"""

    def __init__(self, builder: 'GamepadBuilder', mode: str):
        self.builder = builder
        self.mode = mode

    def _set_implicit_layer(self, property_name: str) -> None:
        """Convert from base layer to auto-named modifier if no explicit layer name was given"""
        if not self.builder.config.is_user_named:
            implicit_name = f"{property_name}.{self.mode}"
            self.builder.config.layer_name = implicit_name
            self.builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER

    @property
    def left_stick(self) -> 'StickPropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("left_stick")
        return StickPropertyBuilder(self.builder, "left_stick")

    @property
    def right_stick(self) -> 'StickPropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("right_stick")
        return StickPropertyBuilder(self.builder, "right_stick")

    @property
    def left_trigger(self) -> 'TriggerPropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("left_trigger")
        return TriggerPropertyBuilder(self.builder, "left_trigger")

    @property
    def right_trigger(self) -> 'TriggerPropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("right_trigger")
        return TriggerPropertyBuilder(self.builder, "right_trigger")


class GamepadBuilder:
    """Main builder for gamepad operations"""

    def __init__(self, gamepad_state: 'GamepadState', layer: Optional[str] = None, order: Optional[int] = None):
        self.gamepad_state = gamepad_state
        self.config = BuilderConfig()
        self._is_valid = True
        self._executed = False
        self._lifecycle_stage = None

        if layer is None:
            self.config.layer_name = "__base_pending__"
            self.config.layer_type = LayerType.BASE
            self.config.is_user_named = False
        else:
            if not layer or not layer.strip():
                self._mark_invalid()
                raise ValueError("Empty layer name not allowed")
            self.config.layer_name = layer
            self.config.layer_type = None  # Set when mode is known
            self.config.is_user_named = True

        if order is not None:
            self.config.order = order

    def _mark_invalid(self):
        """Mark this builder as invalid"""
        self._is_valid = False

    @property
    def is_base_layer(self) -> bool:
        return self.config.is_base_layer()

    # ========================================================================
    # PROPERTY ACCESSORS
    # ========================================================================

    @property
    def left_stick(self) -> 'StickPropertyBuilder':
        """Access left stick"""
        return StickPropertyBuilder(self, "left_stick")

    @property
    def right_stick(self) -> 'StickPropertyBuilder':
        """Access right stick"""
        return StickPropertyBuilder(self, "right_stick")

    @property
    def left_trigger(self) -> 'TriggerPropertyBuilder':
        """Access left trigger"""
        return TriggerPropertyBuilder(self, "left_trigger")

    @property
    def right_trigger(self) -> 'TriggerPropertyBuilder':
        """Access right trigger"""
        return TriggerPropertyBuilder(self, "right_trigger")

    def layer(self, name: str, order: Optional[int] = None) -> 'GamepadBuilder':
        """Create a named layer"""
        return GamepadBuilder(self.gamepad_state, layer=name, order=order)

    def stop(self, transition_ms: Optional[float] = None, easing: str = "linear"):
        """Stop all gamepad activity"""
        self.gamepad_state.stop(transition_ms, easing)

    @property
    def state(self) -> 'GamepadState':
        """Access the current gamepad state"""
        return self.gamepad_state

    # ========================================================================
    # MODE ACCESSORS
    # ========================================================================

    @property
    def offset(self) -> 'ModeProxy':
        return ModeProxy(self, "offset")

    @property
    def override(self) -> 'ModeProxy':
        return ModeProxy(self, "override")

    @property
    def scale(self) -> 'ModeProxy':
        return ModeProxy(self, "scale")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    def over(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp",
        **kwargs
    ) -> 'GamepadBuilder':
        """Set transition duration"""
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('over', self._mark_invalid, **all_kwargs)
        validate_has_operation(self.config, 'over', self._mark_invalid)

        if rate is not None:
            self.config.over_rate = validate_timing(rate, 'rate', method='over', mark_invalid=self._mark_invalid)
            self.config.over_easing = easing
        else:
            self.config.over_ms = validate_timing(ms, 'ms', method='over', mark_invalid=self._mark_invalid) if ms is not None else 0
            self.config.over_easing = easing

        self.config.over_interpolation = interpolation
        self._lifecycle_stage = LifecyclePhase.OVER
        return self

    def hold(self, ms: float) -> 'GamepadBuilder':
        """Hold the value for duration"""
        validate_has_operation(self.config, 'hold', self._mark_invalid)
        self.config.hold_ms = validate_timing(ms, 'ms', method='hold', mark_invalid=self._mark_invalid)
        if self.config.revert_ms is None:
            self.config.revert_ms = 0
        self._lifecycle_stage = LifecyclePhase.HOLD
        return self

    def then(self, callback: Callable) -> 'GamepadBuilder':
        """Add callback after current phase"""
        validate_has_operation(self.config, 'then', self._mark_invalid)
        stage = self._lifecycle_stage or LifecyclePhase.OVER
        self.config.then_callbacks.append((stage, callback))
        return self

    def revert(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp",
        **kwargs
    ) -> 'GamepadBuilder':
        """Revert to base value"""
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('revert', self._mark_invalid, **all_kwargs)

        if rate is not None:
            self.config.revert_rate = validate_timing(rate, 'rate', method='revert', mark_invalid=self._mark_invalid)
            self.config.revert_easing = easing
        else:
            self.config.revert_ms = validate_timing(ms, 'ms', method='revert', mark_invalid=self._mark_invalid) if ms is not None else 0
            self.config.revert_easing = easing

        self.config.revert_interpolation = interpolation
        self._lifecycle_stage = LifecyclePhase.REVERT
        return self

    # ========================================================================
    # BEHAVIOR METHODS
    # ========================================================================

    @property
    def stack(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'stack', has_args=True)

    def _set_stack(self, max: Optional[int] = None) -> 'GamepadBuilder':
        self.config.behavior = "stack"
        self.config.behavior_args = (max,) if max is not None else ()
        return self

    @property
    def replace(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'replace')

    def _set_replace(self) -> 'GamepadBuilder':
        self.config.behavior = "replace"
        return self

    @property
    def queue(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'queue', has_args=True)

    def _set_queue(self, max: Optional[int] = None) -> 'GamepadBuilder':
        self.config.behavior = "queue"
        self.config.behavior_args = (max,) if max is not None else ()
        return self

    @property
    def throttle(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'throttle', has_args=True)

    def _set_throttle(self, ms: Optional[float] = None) -> 'GamepadBuilder':
        self.config.behavior = "throttle"
        if ms is not None:
            self.config.behavior_args = (ms,)
        return self

    @property
    def debounce(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'debounce', has_args=True)

    def _set_debounce(self, ms: float) -> 'GamepadBuilder':
        self.config.behavior = "debounce"
        self.config.behavior_args = (ms,)
        return self

    # ========================================================================
    # BAKE CONTROL
    # ========================================================================

    def bake(self, value: bool = True) -> 'GamepadBuilder':
        self.config.bake_value = value
        return self

    # ========================================================================
    # EXECUTION
    # ========================================================================

    def run(self) -> 'GamepadBuilder':
        """Explicitly execute this builder immediately."""
        if self._is_valid and not self._executed:
            self._execute()
        return self

    def __del__(self):
        if self._is_valid and not self._executed:
            self._execute()

    def _execute(self):
        """Validate and execute the builder"""
        self._executed = True

        # Special case: revert-only call (e.g. gamepad.layer("name").revert(ms))
        if self.config.operator is None:
            if self.config.revert_ms is not None:
                self.gamepad_state.trigger_revert(self.config.layer_name, self.config.revert_ms, self.config.revert_easing)
                return
            return

        # Normal execution: validate, calculate, and add builder
        self.config.validate_mode(self._mark_invalid)
        self._calculate_rate_durations()

        active = ActiveBuilder(self.config, self.gamepad_state, self.is_base_layer)
        self.gamepad_state.add_builder(active)

    def _calculate_rate_durations(self):
        """Calculate durations from rate parameters"""
        if self.config.property is None or self.config.operator is None:
            return

        if self.config.over_rate is not None or self.config.revert_rate is not None:
            current_value = self._get_base_value()
            target_value = self._calculate_target_value(current_value)

            if self.config.over_rate is not None:
                prop = self.config.property
                subprop = self.config.subproperty

                if prop in ("left_trigger", "right_trigger") or subprop in ("magnitude", "x", "y"):
                    # Scalar rate
                    self.config.over_ms = rate_utils.calculate_speed_duration(
                        current_value if isinstance(current_value, (int, float)) else 0,
                        target_value if isinstance(target_value, (int, float)) else 0,
                        self.config.over_rate
                    )
                elif subprop == "direction":
                    if self.config.operator == "to" and is_vec2(target_value):
                        self.config.over_ms = rate_utils.calculate_direction_duration(
                            current_value if is_vec2(current_value) else Vec2(1, 0),
                            target_value,
                            self.config.over_rate
                        )
                    elif self.config.operator in ("by", "add"):
                        angle = self.config.value if isinstance(self.config.value, (int, float)) else 0
                        self.config.over_ms = rate_utils.calculate_direction_by_duration(
                            angle, self.config.over_rate
                        )
                elif prop in ("left_stick", "right_stick") and subprop is None:
                    # Vec2 stick rate
                    cur = current_value if is_vec2(current_value) else Vec2(0, 0)
                    tgt = target_value if is_vec2(target_value) else Vec2(0, 0)
                    self.config.over_ms = rate_utils.calculate_position_duration(
                        cur, tgt, self.config.over_rate
                    )

            if self.config.revert_rate is not None:
                # Mirror logic for revert (swap current/target)
                prop = self.config.property
                subprop = self.config.subproperty

                if prop in ("left_trigger", "right_trigger") or subprop in ("magnitude", "x", "y"):
                    self.config.revert_ms = rate_utils.calculate_speed_duration(
                        target_value if isinstance(target_value, (int, float)) else 0,
                        current_value if isinstance(current_value, (int, float)) else 0,
                        self.config.revert_rate
                    )
                elif subprop == "direction":
                    if self.config.operator == "to" and is_vec2(target_value) and is_vec2(current_value):
                        self.config.revert_ms = rate_utils.calculate_direction_duration(
                            target_value, current_value, self.config.revert_rate
                        )
                elif prop in ("left_stick", "right_stick") and subprop is None:
                    cur = current_value if is_vec2(current_value) else Vec2(0, 0)
                    tgt = target_value if is_vec2(target_value) else Vec2(0, 0)
                    self.config.revert_ms = rate_utils.calculate_position_duration(
                        tgt, cur, self.config.revert_rate
                    )

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        prop = self.config.property
        subprop = self.config.subproperty

        if prop == "left_stick":
            base = self.gamepad_state._base_left_stick
            if subprop == "magnitude":
                return base.magnitude()
            elif subprop == "direction":
                return base.normalized() if base.magnitude() > 1e-10 else Vec2(1, 0)
            elif subprop == "x":
                return base.x
            elif subprop == "y":
                return base.y
            return base.copy()
        elif prop == "right_stick":
            base = self.gamepad_state._base_right_stick
            if subprop == "magnitude":
                return base.magnitude()
            elif subprop == "direction":
                return base.normalized() if base.magnitude() > 1e-10 else Vec2(1, 0)
            elif subprop == "x":
                return base.x
            elif subprop == "y":
                return base.y
            return base.copy()
        elif prop == "left_trigger":
            return self.gamepad_state._base_left_trigger
        elif prop == "right_trigger":
            return self.gamepad_state._base_right_trigger
        return 0

    def _calculate_target_value(self, current: Any = None) -> Any:
        """Calculate target value after operator is applied"""
        if current is None:
            current = self._get_base_value()

        operator = self.config.operator
        value = self.config.value
        prop = self.config.property
        subprop = self.config.subproperty

        if prop in ("left_trigger", "right_trigger") or subprop in ("magnitude", "x", "y"):
            # Scalar target
            if operator == "to":
                return value
            elif operator in ("by", "add"):
                return current + value if isinstance(current, (int, float)) else value
        elif subprop == "direction":
            if operator == "to":
                return Vec2.from_tuple(value).normalized() if isinstance(value, tuple) else value
            elif operator in ("by", "add"):
                # Rotation by degrees
                angle_deg = value
                if is_vec2(current):
                    angle_rad = math.radians(angle_deg)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    new_x = current.x * cos_a - current.y * sin_a
                    new_y = current.x * sin_a + current.y * cos_a
                    return Vec2(new_x, new_y).normalized()
                return current
        elif prop in ("left_stick", "right_stick") and subprop is None:
            # Vec2 stick target
            if operator == "to":
                return Vec2.from_tuple(value) if isinstance(value, tuple) else value
            elif operator in ("by", "add"):
                delta = Vec2.from_tuple(value) if isinstance(value, tuple) else value
                if is_vec2(current) and is_vec2(delta):
                    return current + delta
                return delta

        return current

    def __repr__(self) -> str:
        if not self.is_base_layer:
            return f"GamepadBuilder(layer='{self.config.layer_name}')"
        return "GamepadBuilder()"


class StickPropertyBuilder:
    """Builder for stick (Vec2) properties"""

    def __init__(self, gamepad_builder: GamepadBuilder, property_name: str):
        self.gamepad_builder = gamepad_builder
        self.property_name = property_name
        self.gamepad_builder.config.property = property_name

        # Set base layer name if this is a base operation
        if self.gamepad_builder.config.layer_name == "__base_pending__":
            self.gamepad_builder.config.layer_name = f"base.{property_name}"
            self.gamepad_builder.config.layer_type = LayerType.BASE

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        """Convert from base layer to auto-named modifier if mode is added without explicit layer name"""
        if not self.gamepad_builder.config.is_user_named:
            implicit_name = f"{self.property_name}.{mode}"
            self.gamepad_builder.config.layer_name = implicit_name
            self.gamepad_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
            self.gamepad_builder.config.layer_type = LayerType.USER_NAMED_MODIFIER

    @property
    def offset(self) -> 'StickPropertyBuilder':
        self.gamepad_builder.config.mode = "offset"
        self._set_implicit_layer_if_needed("offset")
        return self

    @property
    def override(self) -> 'StickPropertyBuilder':
        self.gamepad_builder.config.mode = "override"
        self._set_implicit_layer_if_needed("override")
        return self

    @property
    def scale(self) -> 'StickPropertyBuilder':
        self.gamepad_builder.config.mode = "scale"
        self._set_implicit_layer_if_needed("scale")
        return self

    def to(self, x: float, y: float) -> GamepadBuilder:
        """Set stick to absolute position"""
        self.gamepad_builder.config.operator = "to"
        self.gamepad_builder.config.value = (x, y)
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def by(self, dx: float, dy: float) -> GamepadBuilder:
        """Move stick by relative offset"""
        self.gamepad_builder.config.operator = "by"
        self.gamepad_builder.config.value = (dx, dy)
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def add(self, dx: float, dy: float) -> GamepadBuilder:
        """Add to stick position (alias for by)"""
        return self.by(dx, dy)

    def bake(self) -> GamepadBuilder:
        """Bake current computed value into base state"""
        self.gamepad_builder.config.operator = "bake"
        self.gamepad_builder.config.value = None
        return self.gamepad_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> GamepadBuilder:
        """Revert this property/layer"""
        return self.gamepad_builder.revert(ms, easing, **kwargs)

    def __call__(self, x: float, y: float) -> GamepadBuilder:
        """Shorthand for .to(x, y)"""
        return self.to(x, y)

    # Subproperties
    @property
    def magnitude(self) -> 'ScalarPropertyBuilder':
        """Access stick magnitude (0 to 1)"""
        self.gamepad_builder.config.subproperty = "magnitude"
        return ScalarPropertyBuilder(self.gamepad_builder, self.property_name, "magnitude")

    @property
    def direction(self) -> 'DirectionPropertyBuilder':
        """Access stick direction (normalized Vec2)"""
        self.gamepad_builder.config.subproperty = "direction"
        return DirectionPropertyBuilder(self.gamepad_builder, self.property_name)

    @property
    def x(self) -> 'ScalarPropertyBuilder':
        """Access stick x component"""
        self.gamepad_builder.config.subproperty = "x"
        return ScalarPropertyBuilder(self.gamepad_builder, self.property_name, "x")

    @property
    def y(self) -> 'ScalarPropertyBuilder':
        """Access stick y component"""
        self.gamepad_builder.config.subproperty = "y"
        return ScalarPropertyBuilder(self.gamepad_builder, self.property_name, "y")

    def __getattr__(self, name: str):
        """Forward behavior access"""
        if name in ('queue', 'stack', 'replace', 'throttle', 'debounce'):
            result = getattr(self.gamepad_builder, name)
            if isinstance(result, BehaviorProxy):
                result._property_builder = self
            return result
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class TriggerPropertyBuilder:
    """Builder for trigger (scalar) properties"""

    def __init__(self, gamepad_builder: GamepadBuilder, property_name: str):
        self.gamepad_builder = gamepad_builder
        self.property_name = property_name
        self.gamepad_builder.config.property = property_name

        # Set base layer name if this is a base operation
        if self.gamepad_builder.config.layer_name == "__base_pending__":
            self.gamepad_builder.config.layer_name = f"base.{property_name}"
            self.gamepad_builder.config.layer_type = LayerType.BASE

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        """Convert from base layer to auto-named modifier if mode is added without explicit layer name"""
        if not self.gamepad_builder.config.is_user_named:
            implicit_name = f"{self.property_name}.{mode}"
            self.gamepad_builder.config.layer_name = implicit_name
            self.gamepad_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
            self.gamepad_builder.config.layer_type = LayerType.USER_NAMED_MODIFIER

    @property
    def offset(self) -> 'TriggerPropertyBuilder':
        self.gamepad_builder.config.mode = "offset"
        self._set_implicit_layer_if_needed("offset")
        return self

    @property
    def override(self) -> 'TriggerPropertyBuilder':
        self.gamepad_builder.config.mode = "override"
        self._set_implicit_layer_if_needed("override")
        return self

    @property
    def scale(self) -> 'TriggerPropertyBuilder':
        self.gamepad_builder.config.mode = "scale"
        self._set_implicit_layer_if_needed("scale")
        return self

    def to(self, value: float) -> GamepadBuilder:
        """Set trigger to absolute value"""
        self.gamepad_builder.config.operator = "to"
        self.gamepad_builder.config.value = value
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def by(self, delta: float) -> GamepadBuilder:
        """Change trigger by relative amount"""
        self.gamepad_builder.config.operator = "by"
        self.gamepad_builder.config.value = delta
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def add(self, delta: float) -> GamepadBuilder:
        """Add to trigger value (alias for by)"""
        return self.by(delta)

    def bake(self) -> GamepadBuilder:
        """Bake current computed value into base state"""
        self.gamepad_builder.config.operator = "bake"
        self.gamepad_builder.config.value = None
        return self.gamepad_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> GamepadBuilder:
        """Revert this property/layer"""
        return self.gamepad_builder.revert(ms, easing, **kwargs)

    def __call__(self, value: float) -> GamepadBuilder:
        """Shorthand for .to(value)"""
        return self.to(value)

    def __getattr__(self, name: str):
        """Forward behavior access"""
        if name in ('queue', 'stack', 'replace', 'throttle', 'debounce'):
            result = getattr(self.gamepad_builder, name)
            if isinstance(result, BehaviorProxy):
                result._property_builder = self
            return result
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class ScalarPropertyBuilder:
    """Builder for scalar subproperties (magnitude, x, y)"""

    def __init__(self, gamepad_builder: GamepadBuilder, parent_property: str, subproperty: str):
        self.gamepad_builder = gamepad_builder
        self.parent_property = parent_property
        self.subproperty = subproperty

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        """Convert from base layer to auto-named modifier if mode is added without explicit layer name"""
        if not self.gamepad_builder.config.is_user_named:
            implicit_name = f"{self.parent_property}.{self.subproperty}.{mode}"
            self.gamepad_builder.config.layer_name = implicit_name
            self.gamepad_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
            self.gamepad_builder.config.layer_type = LayerType.USER_NAMED_MODIFIER

    @property
    def offset(self) -> 'ScalarPropertyBuilder':
        self.gamepad_builder.config.mode = "offset"
        self._set_implicit_layer_if_needed("offset")
        return self

    @property
    def override(self) -> 'ScalarPropertyBuilder':
        self.gamepad_builder.config.mode = "override"
        self._set_implicit_layer_if_needed("override")
        return self

    @property
    def scale(self) -> 'ScalarPropertyBuilder':
        self.gamepad_builder.config.mode = "scale"
        self._set_implicit_layer_if_needed("scale")
        return self

    def to(self, value: float) -> GamepadBuilder:
        """Set to absolute value"""
        self.gamepad_builder.config.operator = "to"
        self.gamepad_builder.config.value = value
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def by(self, delta: float) -> GamepadBuilder:
        """Change by relative amount"""
        self.gamepad_builder.config.operator = "by"
        self.gamepad_builder.config.value = delta
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def add(self, delta: float) -> GamepadBuilder:
        """Add to value (alias for by)"""
        return self.by(delta)

    def bake(self) -> GamepadBuilder:
        """Bake current computed value into base state"""
        self.gamepad_builder.config.operator = "bake"
        self.gamepad_builder.config.value = None
        return self.gamepad_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> GamepadBuilder:
        """Revert this property/layer"""
        return self.gamepad_builder.revert(ms, easing, **kwargs)

    def __getattr__(self, name: str):
        """Forward behavior access"""
        if name in ('queue', 'stack', 'replace', 'throttle', 'debounce'):
            result = getattr(self.gamepad_builder, name)
            if isinstance(result, BehaviorProxy):
                result._property_builder = self
            return result
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


class DirectionPropertyBuilder:
    """Builder for direction subproperty (normalized Vec2 with rotation support)"""

    def __init__(self, gamepad_builder: GamepadBuilder, parent_property: str):
        self.gamepad_builder = gamepad_builder
        self.parent_property = parent_property

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        """Convert from base layer to auto-named modifier if mode is added without explicit layer name"""
        if not self.gamepad_builder.config.is_user_named:
            implicit_name = f"{self.parent_property}.direction.{mode}"
            self.gamepad_builder.config.layer_name = implicit_name
            self.gamepad_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
            self.gamepad_builder.config.layer_type = LayerType.USER_NAMED_MODIFIER

    @property
    def offset(self) -> 'DirectionPropertyBuilder':
        self.gamepad_builder.config.mode = "offset"
        self._set_implicit_layer_if_needed("offset")
        return self

    @property
    def override(self) -> 'DirectionPropertyBuilder':
        self.gamepad_builder.config.mode = "override"
        self._set_implicit_layer_if_needed("override")
        return self

    @property
    def scale(self) -> 'DirectionPropertyBuilder':
        self.gamepad_builder.config.mode = "scale"
        self._set_implicit_layer_if_needed("scale")
        return self

    def to(self, x: float, y: float) -> GamepadBuilder:
        """Set direction to absolute vector"""
        self.gamepad_builder.config.operator = "to"
        self.gamepad_builder.config.value = (x, y)
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def by(self, degrees: float) -> GamepadBuilder:
        """Rotate direction by degrees"""
        self.gamepad_builder.config.operator = "by"
        self.gamepad_builder.config.value = degrees
        self.gamepad_builder.config.validate_property_operator(self.gamepad_builder._mark_invalid)
        return self.gamepad_builder

    def add(self, degrees: float) -> GamepadBuilder:
        """Rotate direction by degrees (alias for by)"""
        return self.by(degrees)

    def bake(self) -> GamepadBuilder:
        """Bake current computed value into base state"""
        self.gamepad_builder.config.operator = "bake"
        self.gamepad_builder.config.value = None
        return self.gamepad_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> GamepadBuilder:
        """Revert this property/layer"""
        return self.gamepad_builder.revert(ms, easing, **kwargs)

    def __getattr__(self, name: str):
        """Forward behavior access"""
        if name in ('queue', 'stack', 'replace', 'throttle', 'debounce'):
            result = getattr(self.gamepad_builder, name)
            if isinstance(result, BehaviorProxy):
                result._property_builder = self
            return result
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


# ============================================================================
# ACTIVE BUILDER (executing in the state manager)
# ============================================================================

class ActiveBuilder:
    """An active builder being executed in the state manager"""

    def __init__(self, config: BuilderConfig, gamepad_state: 'GamepadState', is_base_layer: bool):
        self.config = config
        self.gamepad_state = gamepad_state
        self.is_base_layer = is_base_layer
        self.layer = config.layer_name
        self.creation_time = time.perf_counter()

        # Back-reference to containing group (set by LayerGroup.add_builder)
        self.group: Optional['LayerGroup'] = None

        # For base layers, always use override mode to store absolute result values
        if config.mode is None:
            config.mode = "override"

        self.group_lifecycle: Optional[Lifecycle] = None
        self.group_base_value: Optional[Any] = None
        self.group_target_value: Optional[Any] = None

        self._marked_for_removal: bool = False

        self.lifecycle = Lifecycle(is_modifier_layer=not is_base_layer)
        self.lifecycle.over_ms = config.over_ms
        self.lifecycle.over_easing = config.over_easing
        self.lifecycle.hold_ms = config.hold_ms
        self.lifecycle.revert_ms = config.revert_ms
        self.lifecycle.revert_easing = config.revert_easing

        for stage, callback in config.then_callbacks:
            self.lifecycle.add_callback(stage, callback)

        # Calculate base and target values
        if config.operator == "to":
            self.base_value = self._get_current_or_base_value()
        elif config.operator in ("by", "add"):
            if is_base_layer:
                self.base_value = self._get_current_or_base_value()
            else:
                self.base_value = self._get_base_value()
        else:
            if is_base_layer:
                self.base_value = self._get_current_or_base_value()
            else:
                self.base_value = self._get_base_value()

        self.target_value = self._calculate_target_value()

    def __repr__(self) -> str:
        phase = self.lifecycle.phase if self.lifecycle and self.lifecycle.phase else "instant"
        return f"<ActiveBuilder '{self.layer}' {self.config.property}.{self.config.operator}({self.target_value}) mode={self.config.mode} phase={phase}>"

    @property
    def time_alive(self) -> float:
        return time.perf_counter() - self.creation_time

    def _get_current_or_base_value(self) -> Any:
        """Get current animated value if mid-transition, otherwise base value."""
        layer = self.config.layer_name
        if layer in self.gamepad_state._layer_groups:
            group = self.gamepad_state._layer_groups[layer]
            if group.is_base and group.builders:
                value = group.get_current_value()
                if value is not None:
                    return value
        return self._get_base_value()

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        prop = self.config.property
        subprop = self.config.subproperty

        if prop == "left_stick":
            base = self.gamepad_state._base_left_stick
        elif prop == "right_stick":
            base = self.gamepad_state._base_right_stick
        elif prop == "left_trigger":
            return self.gamepad_state._base_left_trigger
        elif prop == "right_trigger":
            return self.gamepad_state._base_right_trigger
        else:
            return 0

        # Stick subproperties
        if subprop == "magnitude":
            return base.magnitude()
        elif subprop == "direction":
            return base.normalized() if base.magnitude() > 1e-10 else Vec2(1, 0)
        elif subprop == "x":
            return base.x
        elif subprop == "y":
            return base.y

        return base.copy()

    def _calculate_target_value(self) -> Any:
        """Calculate target value after operator is applied"""
        operator = self.config.operator
        value = self.config.value
        current = self.base_value
        mode = self.config.mode
        prop = self.config.property
        subprop = self.config.subproperty

        if operator == "bake":
            return None

        # Route to appropriate calculator
        if prop in ("left_trigger", "right_trigger"):
            return mode_operations.calculate_scalar_target(operator, value, current, mode)
        elif subprop in ("magnitude", "x", "y"):
            return mode_operations.calculate_scalar_target(operator, value, current, mode)
        elif subprop == "direction":
            return mode_operations.calculate_direction_target(operator, value, current, mode)
        elif prop in ("left_stick", "right_stick") and subprop is None:
            return mode_operations.calculate_position_target(operator, value, current, mode)

        return current

    def advance(self, current_time: float) -> tuple[str, list]:
        """Advance this builder forward in time."""
        phase_transitions = []

        if self.group_lifecycle:
            self.group_lifecycle.advance(current_time)
            if self.group_lifecycle.is_complete():
                if self.group_lifecycle.has_reverted():
                    self._marked_for_removal = True
                self.group_lifecycle = None
                return (None, [])

        old_phase = self.lifecycle.phase
        self.lifecycle.advance(current_time)
        new_phase = self.lifecycle.phase

        if old_phase != new_phase and old_phase is not None:
            phase_transitions.append((self, old_phase))

        return (old_phase if old_phase != new_phase else None, phase_transitions)

    def _get_own_value(self) -> Any:
        """Get just this builder's own value

        The returned value depends on mode:
        - offset: returns contribution value to add
        - override: returns absolute value to use
        - scale: returns multiplier to apply
        """
        current_time = time.perf_counter()
        phase, progress = self.lifecycle.advance(current_time)
        mode = self.config.mode
        prop = self.config.property
        subprop = self.config.subproperty

        # Scalar properties (triggers, magnitude, x, y)
        if prop in ("left_trigger", "right_trigger") or subprop in ("magnitude", "x", "y"):
            if mode == "scale":
                neutral = 1.0
            elif mode == "offset":
                neutral = 0.0
            else:
                neutral = self.base_value

            return PropertyAnimator.animate_scalar(
                neutral, self.target_value, phase, progress, self.lifecycle.has_reverted()
            )

        # Direction subproperty
        elif subprop == "direction":
            interpolation = self.config.over_interpolation
            if phase == LifecyclePhase.REVERT:
                interpolation = self.config.revert_interpolation

            if mode == "offset":
                if isinstance(self.target_value, (int, float)):
                    return PropertyAnimator.animate_scalar(
                        0.0, self.target_value, phase, progress, self.lifecycle.has_reverted()
                    )
                else:
                    return PropertyAnimator.animate_direction(
                        self.base_value, self.target_value, phase, progress,
                        self.lifecycle.has_reverted(), interpolation
                    )
            elif mode == "scale":
                return PropertyAnimator.animate_scalar(
                    1.0, self.target_value, phase, progress, self.lifecycle.has_reverted()
                )
            else:  # override
                return PropertyAnimator.animate_direction(
                    self.base_value, self.target_value, phase, progress,
                    self.lifecycle.has_reverted(), interpolation
                )

        # Vec2 stick properties (left_stick, right_stick without subproperty)
        elif prop in ("left_stick", "right_stick") and subprop is None:
            if mode == "scale":
                return PropertyAnimator.animate_scalar(
                    1.0, self.target_value, phase, progress, self.lifecycle.has_reverted()
                )
            elif mode == "offset":
                neutral = Vec2(0, 0)
                if phase is None:
                    if self.lifecycle.has_reverted():
                        return neutral
                    return self.target_value
                elif phase == LifecyclePhase.OVER:
                    return self.target_value * progress
                elif phase == LifecyclePhase.HOLD:
                    return self.target_value
                elif phase == LifecyclePhase.REVERT:
                    return self.target_value * (1.0 - progress)
            else:  # override
                if phase is None:
                    if self.lifecycle.has_reverted():
                        return self.base_value
                    return self.target_value
                elif phase == LifecyclePhase.OVER:
                    return Vec2(
                        self.base_value.x + (self.target_value.x - self.base_value.x) * progress,
                        self.base_value.y + (self.target_value.y - self.base_value.y) * progress
                    )
                elif phase == LifecyclePhase.HOLD:
                    return self.target_value
                elif phase == LifecyclePhase.REVERT:
                    return Vec2(
                        self.target_value.x + (self.base_value.x - self.target_value.x) * progress,
                        self.target_value.y + (self.base_value.y - self.target_value.y) * progress
                    )

        return self.target_value

    def get_interpolated_value(self) -> Any:
        """Get current interpolated value for this builder"""
        if self.group_lifecycle and not self.group_lifecycle.is_complete():
            current_time = time.perf_counter()
            phase, progress = self.group_lifecycle.advance(current_time)

            # Animate between group_base_value and group_target_value
            if is_vec2(self.group_base_value) and is_vec2(self.group_target_value):
                return PropertyAnimator.animate_direction(
                    self.group_base_value, self.group_target_value,
                    phase, progress, self.group_lifecycle.has_reverted(),
                    self.config.revert_interpolation
                )
            elif isinstance(self.group_base_value, (int, float)) and isinstance(self.group_target_value, (int, float)):
                return PropertyAnimator.animate_scalar(
                    self.group_base_value, self.group_target_value,
                    phase, progress, self.group_lifecycle.has_reverted()
                )

        return self._get_own_value()
