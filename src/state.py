"""State management for gamepad rig - subclasses BaseRigState from rig-core

Implements the 8 abstract methods for gamepad-specific behavior:
- _get_or_create_group
- _compute_current_state
- _apply_group
- _tick_frame
- _bake_group_to_base
- _bake_property
- stop
- _create_active_builder
"""

from typing import Optional, Any, TYPE_CHECKING

# Module-level reference set by _build_classes
GamepadState = None

# Module-level core reference for use by the class
_core = None


def _build_classes(core):
    global GamepadState, _core
    _core = core

    from .core import (
        Vec2, is_vec2, clamp_stick_vec2, clamp_trigger_value, clamp_stick_value, EPSILON,
    )
    from .layer_group import GamepadLayerGroup
    from . import mode_operations

    class _GamepadState(core.BaseRigState):
        """Core state manager for the gamepad rig"""

        def __init__(self):
            super().__init__()
            # Base state (baked values) - neutral is (0, 0) for sticks, 0 for triggers
            self._base_left_stick = Vec2(0, 0)
            self._base_right_stick = Vec2(0, 0)
            self._base_left_trigger: float = 0.0
            self._base_right_trigger: float = 0.0

        def __repr__(self) -> str:
            lines = [
                "GamepadState:",
                f"  left_stick = ({self.left_stick.x:.2f}, {self.left_stick.y:.2f})",
                f"  right_stick = ({self.right_stick.x:.2f}, {self.right_stick.y:.2f})",
                f"  left_trigger = {self.left_trigger:.2f}",
                f"  right_trigger = {self.right_trigger:.2f}",
                f"  layers = {list(self._layer_groups.keys())}",
                f"  frame_loop_active = {self._frame_loop_job is not None}",
            ]
            return "\n".join(lines)

        def __str__(self) -> str:
            return self.__repr__()

        # ========================================================================
        # PUBLIC STATE ACCESS (computed from base + layers)
        # ========================================================================

        @property
        def left_stick(self):
            """Get current left stick position (base + all layers)"""
            lt, _, _, _ = self._compute_current_state()
            return clamp_stick_vec2(lt)

        @property
        def right_stick(self):
            """Get current right stick position (base + all layers)"""
            _, rt, _, _ = self._compute_current_state()
            return clamp_stick_vec2(rt)

        @property
        def left_trigger(self) -> float:
            """Get current left trigger value (base + all layers)"""
            _, _, lt, _ = self._compute_current_state()
            return clamp_trigger_value(lt)

        @property
        def right_trigger(self) -> float:
            """Get current right trigger value (base + all layers)"""
            _, _, _, rt = self._compute_current_state()
            return clamp_trigger_value(rt)

        # ========================================================================
        # CONFIG FACTORY (override)
        # ========================================================================

        def _create_config(self):
            """Create a GamepadBuilderConfig instance"""
            from .contracts import GamepadBuilderConfig
            return GamepadBuilderConfig()

        # ========================================================================
        # STOP / RESET (abstract impl)
        # ========================================================================

        def stop(self, transition_ms: Optional[float] = None, easing: str = "linear"):
            """Stop all gamepad activity"""
            if transition_ms is not None and transition_ms > 0:
                from .contracts import LayerType
                # Smooth stop: revert all layers and base to neutral
                if (self._base_left_stick.x != 0 or self._base_left_stick.y != 0):
                    from .builder import GamepadBuilder
                    b = GamepadBuilder(self)
                    b.config.layer_name = "base.left_stick"
                    b.config.layer_type = LayerType.BASE
                    b.config.property = "left_stick"
                    b.config.operator = "to"
                    b.config.value = (0, 0)
                    b.config.mode = "override"
                    b.config.over_ms = transition_ms
                    b.config.over_easing = easing
                    b.run()

                if (self._base_right_stick.x != 0 or self._base_right_stick.y != 0):
                    from .builder import GamepadBuilder
                    b = GamepadBuilder(self)
                    b.config.layer_name = "base.right_stick"
                    b.config.layer_type = LayerType.BASE
                    b.config.property = "right_stick"
                    b.config.operator = "to"
                    b.config.value = (0, 0)
                    b.config.mode = "override"
                    b.config.over_ms = transition_ms
                    b.config.over_easing = easing
                    b.run()

                if self._base_left_trigger != 0:
                    from .builder import GamepadBuilder
                    b = GamepadBuilder(self)
                    b.config.layer_name = "base.left_trigger"
                    b.config.layer_type = LayerType.BASE
                    b.config.property = "left_trigger"
                    b.config.operator = "to"
                    b.config.value = 0.0
                    b.config.mode = "override"
                    b.config.over_ms = transition_ms
                    b.config.over_easing = easing
                    b.run()

                if self._base_right_trigger != 0:
                    from .builder import GamepadBuilder
                    b = GamepadBuilder(self)
                    b.config.layer_name = "base.right_trigger"
                    b.config.layer_type = LayerType.BASE
                    b.config.property = "right_trigger"
                    b.config.operator = "to"
                    b.config.value = 0.0
                    b.config.mode = "override"
                    b.config.over_ms = transition_ms
                    b.config.over_easing = easing
                    b.run()

                # Trigger revert on all user layers
                for layer_name in list(self._layer_groups.keys()):
                    group = self._layer_groups[layer_name]
                    if not group.is_base:
                        self.trigger_revert(layer_name, transition_ms, easing)

                return

            # Instant stop
            self._base_left_stick = Vec2(0, 0)
            self._base_right_stick = Vec2(0, 0)
            self._base_left_trigger = 0.0
            self._base_right_trigger = 0.0

            # Cancel debounces
            for key, (_, _, _, cron_job) in self._debounce_pending.items():
                if cron_job is not None:
                    self._cancel_cron(cron_job)
            self._debounce_pending.clear()

            # Clear all layers
            self._layer_groups.clear()
            self._layer_orders.clear()
            self._throttle_times.clear()
            self._rate_builder_cache.clear()

            # Stop frame loop
            self._stop_frame_loop()

            # Apply neutral state to gamepad
            self._apply_to_hardware(Vec2(0, 0), Vec2(0, 0), 0.0, 0.0)

        def reset(self):
            """Reset everything to default state"""
            self.stop()
            self._next_auto_order = 0

        # ========================================================================
        # TRIGGER REVERT (override to add subproperty)
        # ========================================================================

        def trigger_revert(self, layer_name: str, revert_ms: Optional[float] = None, easing: str = "linear"):
            """Trigger revert on a layer - gamepad override adds subproperty to config"""
            if layer_name not in self._layer_groups:
                return

            group = self._layer_groups[layer_name]
            import time as _time
            current_time = _time.perf_counter()

            if group.builders:
                for builder in group.builders:
                    builder.lifecycle.trigger_revert(current_time, revert_ms, easing)
            else:
                # No active builders, but group has accumulated_value.
                # Create a revert builder to transition accumulated_value to zero.
                if not group._is_reverted_to_zero():
                    config = self._create_config()
                    config.layer_name = layer_name
                    config.property = group.property
                    config.subproperty = getattr(group, 'subproperty', None)
                    config.mode = group.mode
                    config.operator = "to"

                    if is_vec2(group.accumulated_value):
                        config.value = (group.accumulated_value.x, group.accumulated_value.y)
                    else:
                        config.value = group.accumulated_value

                    config.over_ms = 0
                    config.revert_ms = revert_ms if revert_ms is not None else 0
                    config.revert_easing = easing

                    saved_accumulated = group.accumulated_value.copy() if is_vec2(group.accumulated_value) else group.accumulated_value

                    if is_vec2(group.accumulated_value):
                        group.accumulated_value = Vec2(0, 0)
                    else:
                        group.accumulated_value = 0.0

                    active = self._create_active_builder(config, False)
                    active.target_value = saved_accumulated

                    active.lifecycle.start(current_time)
                    active.lifecycle.phase = core.LifecyclePhase.REVERT
                    active.lifecycle.phase_start_time = current_time

                    group.add_builder(active)

            self._ensure_frame_loop_running()

        # ========================================================================
        # OVERRIDE: flush to hardware on instant operations
        # ========================================================================

        def _finalize_builder_completion(self, builder, group):
            """Handle builder completion, cleanup, and flush to hardware"""
            super()._finalize_builder_completion(builder, group)

            # Flush to hardware for instant operations (no frame loop runs)
            lt, rt, ltrig, rtrig = self._compute_current_state()
            self._apply_to_hardware(
                clamp_stick_vec2(lt), clamp_stick_vec2(rt),
                clamp_trigger_value(ltrig), clamp_trigger_value(rtrig),
            )

        # ========================================================================
        # ABSTRACT IMPLEMENTATIONS
        # ========================================================================

        def _create_active_builder(self, config, is_base):
            """Factory for gamepad ActiveBuilder instances"""
            from .builder import GamepadActiveBuilder
            return GamepadActiveBuilder(config, self, is_base)

        def _get_or_create_group(self, builder):
            """Get existing group or create new one for this builder"""
            layer = builder.config.layer_name

            if layer in self._layer_groups:
                return self._layer_groups[layer]

            # Determine property kind
            prop = builder.config.property
            subprop = getattr(builder.config, 'subproperty', None)
            property_kind = self._get_property_kind_for(prop, subprop, builder.config.mode)

            group = GamepadLayerGroup(
                layer_name=layer,
                property=prop,
                property_kind=property_kind,
                mode=builder.config.mode,
                layer_type=builder.config.layer_type,
                order=builder.config.order,
                subproperty=subprop,
            )

            # Initialize base layer accumulated_value from actual base state
            if group.is_base:
                if prop == "left_stick":
                    if subprop is None:
                        group.accumulated_value = self._base_left_stick.copy()
                    elif subprop == "magnitude":
                        group.accumulated_value = self._base_left_stick.magnitude()
                    elif subprop == "direction":
                        group.accumulated_value = self._base_left_stick.normalized() if self._base_left_stick.magnitude() > EPSILON else Vec2(1, 0)
                    elif subprop == "x":
                        group.accumulated_value = self._base_left_stick.x
                    elif subprop == "y":
                        group.accumulated_value = self._base_left_stick.y
                elif prop == "right_stick":
                    if subprop is None:
                        group.accumulated_value = self._base_right_stick.copy()
                    elif subprop == "magnitude":
                        group.accumulated_value = self._base_right_stick.magnitude()
                    elif subprop == "direction":
                        group.accumulated_value = self._base_right_stick.normalized() if self._base_right_stick.magnitude() > EPSILON else Vec2(1, 0)
                    elif subprop == "x":
                        group.accumulated_value = self._base_right_stick.x
                    elif subprop == "y":
                        group.accumulated_value = self._base_right_stick.y
                elif prop == "left_trigger":
                    group.accumulated_value = self._base_left_trigger
                elif prop == "right_trigger":
                    group.accumulated_value = self._base_right_trigger

            # Initialize override mode with current computed value
            elif builder.config.mode == "override":
                lt, rt, ltrig, rtrig = self._compute_current_state()

                if prop == "left_stick":
                    if subprop is None:
                        group.accumulated_value = lt.copy()
                    elif subprop == "magnitude":
                        group.accumulated_value = lt.magnitude()
                    elif subprop == "direction":
                        group.accumulated_value = lt.normalized() if lt.magnitude() > EPSILON else Vec2(1, 0)
                    elif subprop == "x":
                        group.accumulated_value = lt.x
                    elif subprop == "y":
                        group.accumulated_value = lt.y
                elif prop == "right_stick":
                    if subprop is None:
                        group.accumulated_value = rt.copy()
                    elif subprop == "magnitude":
                        group.accumulated_value = rt.magnitude()
                    elif subprop == "direction":
                        group.accumulated_value = rt.normalized() if rt.magnitude() > EPSILON else Vec2(1, 0)
                    elif subprop == "x":
                        group.accumulated_value = rt.x
                    elif subprop == "y":
                        group.accumulated_value = rt.y
                elif prop == "left_trigger":
                    group.accumulated_value = ltrig
                elif prop == "right_trigger":
                    group.accumulated_value = rtrig

            # Track order
            if builder.config.order is not None:
                self._layer_orders[layer] = builder.config.order
            elif not builder.config.is_base_layer():
                if layer not in self._layer_orders:
                    self._layer_orders[layer] = self._next_auto_order
                    self._next_auto_order += 1
                    group.order = self._layer_orders[layer]

            self._layer_groups[layer] = group
            return group

        def _compute_current_state(self):
            """Compute current state by applying all active layers to base.

            Returns:
                (left_stick, right_stick, left_trigger, right_trigger)
            """
            lt = self._base_left_stick.copy()
            rt = self._base_right_stick.copy()
            ltrig = self._base_left_trigger
            rtrig = self._base_right_trigger

            # Separate groups by layer type
            base_groups = []
            user_groups = []

            for layer_name, group in self._layer_groups.items():
                if group.is_base:
                    base_groups.append(group)
                else:
                    user_groups.append(group)

            # Sort user layers by order
            user_groups = sorted(user_groups, key=lambda g: g.order if g.order is not None else 999999)

            # Process base groups first, then user groups
            for group in base_groups + user_groups:
                lt, rt, ltrig, rtrig = self._apply_group(group, lt, rt, ltrig, rtrig)

            return (lt, rt, ltrig, rtrig)

        def _apply_group(self, group, lt, rt, ltrig, rtrig):
            """Apply a layer group's value to the accumulated state"""
            prop = group.property
            subprop = getattr(group, 'subproperty', None)
            mode = group.mode
            current_value = group.get_current_value()

            if prop == "left_stick":
                lt = self._apply_stick_group(lt, current_value, mode, subprop)
            elif prop == "right_stick":
                rt = self._apply_stick_group(rt, current_value, mode, subprop)
            elif prop == "left_trigger":
                ltrig = mode_operations.apply_trigger_mode(mode, current_value, ltrig)
            elif prop == "right_trigger":
                rtrig = mode_operations.apply_trigger_mode(mode, current_value, rtrig)

            return lt, rt, ltrig, rtrig

        def _apply_stick_group(self, stick, value: Any, mode: str, subprop: Optional[str]):
            """Apply a stick group's value, handling subproperties"""
            if subprop is None:
                # Full stick Vec2
                return mode_operations.apply_stick_mode(mode, value, stick)
            elif subprop == "magnitude":
                # Apply scalar to magnitude, preserve direction
                current_mag = stick.magnitude()
                new_mag = mode_operations.apply_scalar_mode(mode, value, current_mag)
                new_mag = max(0.0, min(1.0, new_mag))
                direction = stick.normalized() if current_mag > EPSILON else Vec2(1, 0)
                return direction * new_mag
            elif subprop == "direction":
                # Apply direction, preserve magnitude
                current_mag = stick.magnitude()
                new_dir = mode_operations.apply_direction_mode(mode, value, stick.normalized() if current_mag > EPSILON else Vec2(1, 0))
                return new_dir.normalized() * current_mag
            elif subprop == "x":
                # Apply scalar to x, preserve y
                new_x = mode_operations.apply_scalar_mode(mode, value, stick.x)
                return Vec2(clamp_stick_value(new_x), stick.y)
            elif subprop == "y":
                # Apply scalar to y, preserve x
                new_y = mode_operations.apply_scalar_mode(mode, value, stick.y)
                return Vec2(stick.x, clamp_stick_value(new_y))

            return stick

        def _tick_frame(self):
            """Main frame loop tick"""
            import time as _time
            current_time = _time.perf_counter()

            # Check debounce
            self._check_debounce_pending(current_time)

            # Advance all builders (handles phase transitions, completions, baking, cleanup)
            self._advance_all_builders(current_time)

            # Compute current state
            lt, rt, ltrig, rtrig = self._compute_current_state()

            # Clamp outputs
            lt = clamp_stick_vec2(lt)
            rt = clamp_stick_vec2(rt)
            ltrig = clamp_trigger_value(ltrig)
            rtrig = clamp_trigger_value(rtrig)

            # Apply to hardware (single batch update)
            self._apply_to_hardware(lt, rt, ltrig, rtrig)

            # Stop if nothing active
            self._stop_frame_loop_if_done()

        def _bake_group_to_base(self, group):
            """Bake base layer group's value into base state"""
            if not group.is_base:
                return

            current_value = group.get_current_value()
            prop = group.property
            subprop = getattr(group, 'subproperty', None)

            if prop == "left_stick":
                if subprop is None:
                    if is_vec2(current_value):
                        self._base_left_stick = clamp_stick_vec2(current_value)
                    elif isinstance(current_value, tuple):
                        self._base_left_stick = clamp_stick_vec2(Vec2.from_tuple(current_value))
                elif subprop == "magnitude":
                    direction = self._base_left_stick.normalized() if self._base_left_stick.magnitude() > EPSILON else Vec2(1, 0)
                    self._base_left_stick = direction * max(0.0, min(1.0, float(current_value)))
                elif subprop == "direction":
                    mag = self._base_left_stick.magnitude()
                    if is_vec2(current_value):
                        self._base_left_stick = current_value.normalized() * mag
                elif subprop == "x":
                    self._base_left_stick = Vec2(clamp_stick_value(float(current_value)), self._base_left_stick.y)
                elif subprop == "y":
                    self._base_left_stick = Vec2(self._base_left_stick.x, clamp_stick_value(float(current_value)))

            elif prop == "right_stick":
                if subprop is None:
                    if is_vec2(current_value):
                        self._base_right_stick = clamp_stick_vec2(current_value)
                    elif isinstance(current_value, tuple):
                        self._base_right_stick = clamp_stick_vec2(Vec2.from_tuple(current_value))
                elif subprop == "magnitude":
                    direction = self._base_right_stick.normalized() if self._base_right_stick.magnitude() > EPSILON else Vec2(1, 0)
                    self._base_right_stick = direction * max(0.0, min(1.0, float(current_value)))
                elif subprop == "direction":
                    mag = self._base_right_stick.magnitude()
                    if is_vec2(current_value):
                        self._base_right_stick = current_value.normalized() * mag
                elif subprop == "x":
                    self._base_right_stick = Vec2(clamp_stick_value(float(current_value)), self._base_right_stick.y)
                elif subprop == "y":
                    self._base_right_stick = Vec2(self._base_right_stick.x, clamp_stick_value(float(current_value)))

            elif prop == "left_trigger":
                self._base_left_trigger = clamp_trigger_value(float(current_value))

            elif prop == "right_trigger":
                self._base_right_trigger = clamp_trigger_value(float(current_value))

        def bake_all(self):
            """Flatten all layers into base state, then clear all layers"""
            lt, rt, ltrig, rtrig = self._compute_current_state()
            self._base_left_stick = clamp_stick_vec2(lt)
            self._base_right_stick = clamp_stick_vec2(rt)
            self._base_left_trigger = clamp_trigger_value(ltrig)
            self._base_right_trigger = clamp_trigger_value(rtrig)

            self._layer_groups.clear()
            self._layer_orders.clear()

        def _bake_property(self, property_name: str, layer: Optional[str] = None):
            """Bake current computed value of a property into base state"""
            lt, rt, ltrig, rtrig = self._compute_current_state()

            if property_name == "left_stick":
                self._base_left_stick = clamp_stick_vec2(lt)
            elif property_name == "right_stick":
                self._base_right_stick = clamp_stick_vec2(rt)
            elif property_name == "left_trigger":
                self._base_left_trigger = clamp_trigger_value(ltrig)
            elif property_name == "right_trigger":
                self._base_right_trigger = clamp_trigger_value(rtrig)

            # Remove the specified layer or all layers for this property
            if layer:
                if layer in self._layer_groups:
                    del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]
            else:
                layers_to_remove = [
                    l for l, g in self._layer_groups.items()
                    if g.property == property_name
                ]
                for l in layers_to_remove:
                    if l in self._layer_groups:
                        del self._layer_groups[l]
                    if l in self._layer_orders:
                        del self._layer_orders[l]

        # ========================================================================
        # HARDWARE
        # ========================================================================

        def _apply_to_hardware(self, lt, rt, ltrig: float, rtrig: float):
            """Apply state to vgamepad hardware using single batch update"""
            from . import gamepad_api

            if not gamepad_api.is_available():
                return

            gamepad_api.update_all(lt.x, lt.y, rt.x, rt.y, ltrig, rtrig)

        # ========================================================================
        # HELPERS
        # ========================================================================

        def _get_property_kind_for(self, prop, subprop, mode=None):
            """Map gamepad property/subproperty to PropertyKind"""
            PropertyKind = core.PropertyKind
            if prop in ("left_trigger", "right_trigger") or subprop in ("magnitude", "x", "y"):
                return PropertyKind.SCALAR
            elif subprop == "direction":
                return PropertyKind.DIRECTION
            elif prop in ("left_stick", "right_stick") and subprop is None:
                return PropertyKind.VECTOR
            return PropertyKind.SCALAR

    GamepadState = _GamepadState
