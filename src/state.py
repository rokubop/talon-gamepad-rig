"""State management for gamepad rig

Manages gamepad state with:
- Base state (baked stick/trigger values)
- Layer groups (containers for builders)
- Frame loop for continuous updates
- Integration with vgamepad backend
"""

import time
from typing import Optional, Any, Union, TYPE_CHECKING
from talon import cron
from .core import Vec2, is_vec2, clamp_stick_vec2, clamp_trigger_value, clamp_stick_value, EPSILON
from .layer_group import LayerGroup
from .lifecycle import Lifecycle, LifecyclePhase
from .contracts import BuilderConfig, ConfigError, LayerType, validate_timing
from . import mode_operations

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class GamepadState:
    """Core state manager for the gamepad rig"""

    def __init__(self):
        # Base state (baked values) - neutral is (0, 0) for sticks, 0 for triggers
        self._base_left_thumb: Vec2 = Vec2(0, 0)
        self._base_right_thumb: Vec2 = Vec2(0, 0)
        self._base_left_trigger: float = 0.0
        self._base_right_trigger: float = 0.0

        # Layer groups (layer_name -> LayerGroup)
        self._layer_groups: dict[str, LayerGroup] = {}

        # Layer order tracking
        self._layer_orders: dict[str, int] = {}

        # Frame loop
        self._frame_loop_job: Optional[cron.CronJob] = None
        self._last_frame_time: Optional[float] = None

        # Throttle tracking
        self._throttle_times: dict[str, float] = {}

        # Auto-order counter
        self._next_auto_order: int = 0

        # Rate-based builder cache
        self._rate_builder_cache: dict[tuple, tuple['ActiveBuilder', Any]] = {}

        # Debounce pending builders
        self._debounce_pending: dict[str, tuple[float, 'BuilderConfig', bool, Optional[cron.CronJob]]] = {}

        # Stop callbacks
        self._stop_callbacks: list = []

    def __repr__(self) -> str:
        lines = [
            "GamepadState:",
            f"  left_thumb = ({self.left_thumb.x:.2f}, {self.left_thumb.y:.2f})",
            f"  right_thumb = ({self.right_thumb.x:.2f}, {self.right_thumb.y:.2f})",
            f"  left_trigger = {self.left_trigger:.2f}",
            f"  right_trigger = {self.right_trigger:.2f}",
            f"  layers = {list(self._layer_groups.keys())}",
            f"  frame_loop_active = {self._frame_loop_job is not None}",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.__repr__()

    # ========================================================================
    # KEY HELPERS
    # ========================================================================

    def _get_queue_key(self, layer: str, builder: 'ActiveBuilder') -> str:
        return f"{layer}_{builder.config.property}_{builder.config.operator}"

    def _get_throttle_key(self, layer: str, builder_or_config: Union['ActiveBuilder', 'BuilderConfig']) -> str:
        config = builder_or_config if isinstance(builder_or_config, BuilderConfig) else builder_or_config.config
        return f"{layer}_{config.property}_{config.operator}"

    def _get_rate_cache_key(self, layer: str, config: 'BuilderConfig') -> Optional[tuple]:
        if config.over_rate is None and config.revert_rate is None:
            return None
        target = config.value
        if isinstance(target, tuple):
            normalized = tuple(round(v, 3) for v in target)
        elif isinstance(target, (int, float)):
            normalized = round(target, 3)
        else:
            normalized = target
        return (layer, config.property, config.operator, config.mode, normalized)

    def _get_debounce_key(self, layer: str, config: 'BuilderConfig') -> str:
        return f"{layer}_{config.property}_{config.operator}"

    # ========================================================================
    # PUBLIC STATE ACCESS (computed from base + layers)
    # ========================================================================

    @property
    def left_thumb(self) -> Vec2:
        """Get current left stick position (base + all layers)"""
        lt, _, _, _ = self._compute_current_state()
        return clamp_stick_vec2(lt)

    @property
    def right_thumb(self) -> Vec2:
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

    @property
    def layers(self) -> list[str]:
        """Get list of active layer names"""
        return list(self._layer_groups.keys())

    # ========================================================================
    # STOP / RESET
    # ========================================================================

    def stop(self, transition_ms: Optional[float] = None, easing: str = "linear"):
        """Stop all gamepad activity"""
        if transition_ms is not None and transition_ms > 0:
            # Smooth stop: revert all layers and base to neutral
            # Create revert builders for any non-neutral base values
            if (self._base_left_thumb.x != 0 or self._base_left_thumb.y != 0):
                from .builder import GamepadBuilder
                b = GamepadBuilder(self)
                b.config.layer_name = "base.left_thumb"
                b.config.layer_type = LayerType.BASE
                b.config.property = "left_thumb"
                b.config.operator = "to"
                b.config.value = (0, 0)
                b.config.mode = "override"
                b.config.over_ms = transition_ms
                b.config.over_easing = easing
                b.run()

            if (self._base_right_thumb.x != 0 or self._base_right_thumb.y != 0):
                from .builder import GamepadBuilder
                b = GamepadBuilder(self)
                b.config.layer_name = "base.right_thumb"
                b.config.layer_type = LayerType.BASE
                b.config.property = "right_thumb"
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
        self._base_left_thumb = Vec2(0, 0)
        self._base_right_thumb = Vec2(0, 0)
        self._base_left_trigger = 0.0
        self._base_right_trigger = 0.0

        # Cancel debounces
        for key, (_, _, _, cron_job) in self._debounce_pending.items():
            if cron_job is not None:
                cron.cancel(cron_job)
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

    def add_stop_callback(self, callback):
        """Add a callback to be executed when the frame loop stops"""
        self._stop_callbacks.append(callback)

    # ========================================================================
    # TRIGGER REVERT
    # ========================================================================

    def trigger_revert(self, layer_name: str, revert_ms: Optional[float] = None, easing: str = "linear"):
        """Trigger revert on a layer or property

        Args:
            layer_name: Layer to revert
            revert_ms: Duration in ms
            easing: Easing function
        """
        if layer_name not in self._layer_groups:
            return

        group = self._layer_groups[layer_name]
        current_time = time.perf_counter()

        for builder in group.builders:
            builder.lifecycle.trigger_revert(current_time, revert_ms, easing)

        # If no builders but layer has accumulated value, create a group lifecycle
        if not group.builders and not group._is_reverted_to_zero():
            lifecycle = Lifecycle(is_modifier_layer=True)
            lifecycle.revert_ms = revert_ms or 0
            lifecycle.revert_easing = easing
            lifecycle.start(current_time)

            # Create a dummy builder to animate the revert
            from .builder import ActiveBuilder
            config = BuilderConfig()
            config.layer_name = layer_name
            config.property = group.property
            config.subproperty = group.subproperty
            config.mode = group.mode
            config.operator = "to"
            config.revert_ms = revert_ms or 0
            config.revert_easing = easing

            # Set value to zero/neutral for revert target
            if isinstance(group.accumulated_value, Vec2):
                config.value = (0, 0)
            else:
                config.value = 0.0

            active = ActiveBuilder(config, self, False)
            active.group_lifecycle = lifecycle
            active.group_base_value = group.accumulated_value
            if isinstance(group.accumulated_value, Vec2):
                active.group_target_value = Vec2(0, 0)
            else:
                active.group_target_value = 0.0

            group.add_builder(active)
            self._ensure_frame_loop_running()

    # ========================================================================
    # ADD BUILDER (the main pipeline)
    # ========================================================================

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add a builder to its layer group"""
        layer = builder.config.layer_name

        # Handle bake operation
        if builder.config.operator == "bake":
            self._bake_property(builder.config.property, layer if not builder.config.is_base_layer() else None)
            return

        # Handle debounce
        if builder.config.behavior == "debounce":
            self._apply_debounce_behavior(builder, layer)
            return

        # Rate cache check
        should_skip = self._check_and_update_rate_cache(builder, layer)
        if should_skip:
            return

        # Get or create group
        group = self._get_or_create_group(builder)

        # Apply behavior
        behavior = builder.config.get_effective_behavior()

        if behavior == "throttle":
            if self._apply_throttle_behavior(builder, layer):
                return

        if behavior == "replace":
            self._apply_replace_behavior(builder, group)
        elif behavior == "stack":
            if self._apply_stack_behavior(builder, group):
                return
        elif behavior == "queue":
            if self._apply_queue_behavior(builder, group):
                return

        group.add_builder(builder)

        if not builder.lifecycle.is_complete():
            self._ensure_frame_loop_running()
        else:
            self._finalize_builder_completion(builder, group)

    def _get_or_create_group(self, builder: 'ActiveBuilder') -> 'LayerGroup':
        """Get existing group or create new one for this builder"""
        layer = builder.config.layer_name

        if layer in self._layer_groups:
            return self._layer_groups[layer]

        group = LayerGroup(
            layer_name=layer,
            property=builder.config.property,
            mode=builder.config.mode,
            layer_type=builder.config.layer_type,
            order=builder.config.order,
            subproperty=builder.config.subproperty,
        )

        # Initialize base layer accumulated_value from actual base state
        if group.is_base:
            prop = builder.config.property
            subprop = builder.config.subproperty

            if prop == "left_thumb":
                if subprop is None:
                    group.accumulated_value = self._base_left_thumb.copy()
                elif subprop == "magnitude":
                    group.accumulated_value = self._base_left_thumb.magnitude()
                elif subprop == "direction":
                    group.accumulated_value = self._base_left_thumb.normalized() if self._base_left_thumb.magnitude() > EPSILON else Vec2(1, 0)
                elif subprop == "x":
                    group.accumulated_value = self._base_left_thumb.x
                elif subprop == "y":
                    group.accumulated_value = self._base_left_thumb.y
            elif prop == "right_thumb":
                if subprop is None:
                    group.accumulated_value = self._base_right_thumb.copy()
                elif subprop == "magnitude":
                    group.accumulated_value = self._base_right_thumb.magnitude()
                elif subprop == "direction":
                    group.accumulated_value = self._base_right_thumb.normalized() if self._base_right_thumb.magnitude() > EPSILON else Vec2(1, 0)
                elif subprop == "x":
                    group.accumulated_value = self._base_right_thumb.x
                elif subprop == "y":
                    group.accumulated_value = self._base_right_thumb.y
            elif prop == "left_trigger":
                group.accumulated_value = self._base_left_trigger
            elif prop == "right_trigger":
                group.accumulated_value = self._base_right_trigger

        # Initialize override mode with current computed value
        elif builder.config.mode == "override":
            lt, rt, ltrig, rtrig = self._compute_current_state()
            prop = builder.config.property
            subprop = builder.config.subproperty

            if prop == "left_thumb":
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
            elif prop == "right_thumb":
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

    def _finalize_builder_completion(self, builder: 'ActiveBuilder', group: 'LayerGroup'):
        """Handle builder completion and cleanup"""
        layer = builder.config.layer_name

        bake_result = group.on_builder_complete(builder)
        if bake_result == "bake_to_base":
            self._bake_group_to_base(group)

        group.remove_builder(builder)

        if not group.should_persist():
            if layer in self._layer_groups:
                del self._layer_groups[layer]
            if layer in self._layer_orders:
                del self._layer_orders[layer]

    # ========================================================================
    # BEHAVIOR METHODS
    # ========================================================================

    def _apply_throttle_behavior(self, builder: 'ActiveBuilder', layer: str) -> bool:
        """Returns True if throttled (should skip)"""
        throttle_key = self._get_throttle_key(layer, builder)
        has_time_arg = bool(builder.config.behavior_args)

        if has_time_arg:
            throttle_ms = builder.config.behavior_args[0]
            if throttle_key in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[throttle_key]) * 1000
                if elapsed < throttle_ms:
                    return True
            self._throttle_times[throttle_key] = time.perf_counter()
            return False
        else:
            if layer in self._layer_groups:
                group = self._layer_groups[layer]
                active_throttled = sum(1 for b in group.builders if b.config.behavior == "throttle")
                if active_throttled > 0:
                    return True
            return False

    def _apply_debounce_behavior(self, builder: 'ActiveBuilder', layer: str):
        """Schedule builder for delayed execution"""
        if not builder.config.behavior_args:
            raise ConfigError("debounce() requires a delay in milliseconds")

        delay_ms = builder.config.behavior_args[0]
        debounce_key = self._get_debounce_key(layer, builder.config)

        if debounce_key in self._debounce_pending:
            _, _, _, old_cron_job = self._debounce_pending[debounce_key]
            if old_cron_job is not None:
                cron.cancel(old_cron_job)

        target_time = time.perf_counter() + (delay_ms / 1000.0)

        cron_job = None
        if self._frame_loop_job is None:
            def execute_debounced():
                if debounce_key in self._debounce_pending:
                    _, config, is_base, _ = self._debounce_pending[debounce_key]
                    del self._debounce_pending[debounce_key]
                    config.behavior = None
                    config.behavior_args = ()
                    from .builder import ActiveBuilder
                    actual_builder = ActiveBuilder(config, self, is_base)
                    self.add_builder(actual_builder)

            cron_job = cron.after(f"{delay_ms}ms", execute_debounced)

        self._debounce_pending[debounce_key] = (target_time, builder.config, builder.config.is_base_layer(), cron_job)

    def _check_and_update_rate_cache(self, builder: 'ActiveBuilder', layer: str) -> bool:
        """Returns True if builder should be skipped"""
        rate_cache_key = self._get_rate_cache_key(layer, builder.config)
        if rate_cache_key is None:
            return False

        if rate_cache_key in self._rate_builder_cache:
            cached_builder, cached_target = self._rate_builder_cache[rate_cache_key]
            targets_match = self._targets_match(builder.target_value, cached_target)

            if targets_match and layer in self._layer_groups:
                return True
            else:
                if layer in self._layer_groups:
                    group = self._layer_groups[layer]
                    old_current_value = group.get_current_value()
                    if is_vec2(old_current_value):
                        builder.base_value = Vec2(old_current_value.x, old_current_value.y)
                    else:
                        builder.base_value = old_current_value
                    builder.target_value = builder._calculate_target_value()

        self._rate_builder_cache[rate_cache_key] = (builder, builder.target_value)
        return False

    def _apply_replace_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup'):
        """Apply replace behavior"""
        current_value = group.get_current_value()
        group.clear_builders()

        if not group.is_base:
            group.accumulated_value = current_value

        if is_vec2(current_value):
            builder.base_value = current_value
        elif isinstance(current_value, (int, float)):
            builder.base_value = current_value
        else:
            builder.base_value = current_value

        builder.target_value = builder._calculate_target_value()

    def _apply_stack_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup') -> bool:
        """Returns True if at stack limit"""
        if builder.config.behavior_args:
            max_count = builder.config.behavior_args[0]
            if max_count > 0:
                non_revert_builders = sum(
                    1 for b in group.builders
                    if not (b.lifecycle.phase == LifecyclePhase.REVERT or
                            (b.group_lifecycle and b.group_lifecycle.phase == LifecyclePhase.REVERT))
                )
                accumulated_slots = 0
                if not group.is_base and not group._is_reverted_to_zero():
                    accumulated_slots = 1
                if non_revert_builders + accumulated_slots >= max_count:
                    return True
                reverting_builders = [
                    b for b in group.builders
                    if (b.lifecycle.phase == LifecyclePhase.REVERT or
                        (b.group_lifecycle and b.group_lifecycle.phase == LifecyclePhase.REVERT))
                ]
                for b in reverting_builders:
                    group.remove_builder(b)
        return False

    def _apply_queue_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup') -> bool:
        """Returns True if enqueued"""
        if builder.config.behavior_args:
            max_count = builder.config.behavior_args[0]
            total = len(group.builders) + len(group.pending_queue)
            if total >= max_count:
                return True

        if group.is_queue_active or len(group.pending_queue) > 0:
            def execute_callback():
                builder.creation_time = time.perf_counter()
                builder.lifecycle.started = False
                if group.is_base:
                    builder.base_value = builder._get_current_or_base_value()
                    builder.target_value = builder._calculate_target_value()
                group.add_builder(builder)
                if not builder.lifecycle.is_complete():
                    self._ensure_frame_loop_running()

            group.enqueue_builder(execute_callback)
            return True
        else:
            group.is_queue_active = True
            return False

    def _targets_match(self, target1: Any, target2: Any) -> bool:
        if isinstance(target1, (int, float)) and isinstance(target2, (int, float)):
            return abs(target1 - target2) < EPSILON
        elif is_vec2(target1) and is_vec2(target2):
            return abs(target1.x - target2.x) < EPSILON and abs(target1.y - target2.y) < EPSILON
        else:
            return target1 == target2

    # ========================================================================
    # COMPUTE CURRENT STATE
    # ========================================================================

    def _compute_current_state(self) -> tuple[Vec2, Vec2, float, float]:
        """Compute current state by applying all active layers to base.

        Returns:
            (left_thumb, right_thumb, left_trigger, right_trigger)
        """
        lt = self._base_left_thumb.copy()
        rt = self._base_right_thumb.copy()
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

    def _apply_group(
        self,
        group: 'LayerGroup',
        lt: Vec2,
        rt: Vec2,
        ltrig: float,
        rtrig: float
    ) -> tuple[Vec2, Vec2, float, float]:
        """Apply a layer group's value to the accumulated state"""
        prop = group.property
        subprop = group.subproperty
        mode = group.mode
        current_value = group.get_current_value()

        if prop == "left_thumb":
            lt = self._apply_stick_group(lt, current_value, mode, subprop)
        elif prop == "right_thumb":
            rt = self._apply_stick_group(rt, current_value, mode, subprop)
        elif prop == "left_trigger":
            ltrig = mode_operations.apply_trigger_mode(mode, current_value, ltrig)
        elif prop == "right_trigger":
            rtrig = mode_operations.apply_trigger_mode(mode, current_value, rtrig)

        return lt, rt, ltrig, rtrig

    def _apply_stick_group(self, stick: Vec2, value: Any, mode: str, subprop: Optional[str]) -> Vec2:
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

    # ========================================================================
    # BAKE
    # ========================================================================

    def _bake_group_to_base(self, group: 'LayerGroup'):
        """Bake base layer group's value into base state"""
        if not group.is_base:
            return

        current_value = group.get_current_value()
        prop = group.property
        subprop = group.subproperty

        if prop == "left_thumb":
            if subprop is None:
                if is_vec2(current_value):
                    self._base_left_thumb = clamp_stick_vec2(current_value)
                elif isinstance(current_value, tuple):
                    self._base_left_thumb = clamp_stick_vec2(Vec2.from_tuple(current_value))
            elif subprop == "magnitude":
                direction = self._base_left_thumb.normalized() if self._base_left_thumb.magnitude() > EPSILON else Vec2(1, 0)
                self._base_left_thumb = direction * max(0.0, min(1.0, float(current_value)))
            elif subprop == "direction":
                mag = self._base_left_thumb.magnitude()
                if is_vec2(current_value):
                    self._base_left_thumb = current_value.normalized() * mag
            elif subprop == "x":
                self._base_left_thumb = Vec2(clamp_stick_value(float(current_value)), self._base_left_thumb.y)
            elif subprop == "y":
                self._base_left_thumb = Vec2(self._base_left_thumb.x, clamp_stick_value(float(current_value)))

        elif prop == "right_thumb":
            if subprop is None:
                if is_vec2(current_value):
                    self._base_right_thumb = clamp_stick_vec2(current_value)
                elif isinstance(current_value, tuple):
                    self._base_right_thumb = clamp_stick_vec2(Vec2.from_tuple(current_value))
            elif subprop == "magnitude":
                direction = self._base_right_thumb.normalized() if self._base_right_thumb.magnitude() > EPSILON else Vec2(1, 0)
                self._base_right_thumb = direction * max(0.0, min(1.0, float(current_value)))
            elif subprop == "direction":
                mag = self._base_right_thumb.magnitude()
                if is_vec2(current_value):
                    self._base_right_thumb = current_value.normalized() * mag
            elif subprop == "x":
                self._base_right_thumb = Vec2(clamp_stick_value(float(current_value)), self._base_right_thumb.y)
            elif subprop == "y":
                self._base_right_thumb = Vec2(self._base_right_thumb.x, clamp_stick_value(float(current_value)))

        elif prop == "left_trigger":
            self._base_left_trigger = clamp_trigger_value(float(current_value))

        elif prop == "right_trigger":
            self._base_right_trigger = clamp_trigger_value(float(current_value))

    def bake_all(self):
        """Bake all layers: compute current state, set as base, remove all layers"""
        lt, rt, ltrig, rtrig = self._compute_current_state()
        self._base_left_thumb = clamp_stick_vec2(lt)
        self._base_right_thumb = clamp_stick_vec2(rt)
        self._base_left_trigger = clamp_trigger_value(ltrig)
        self._base_right_trigger = clamp_trigger_value(rtrig)

        # Clear all layers and builders
        self._layer_groups.clear()
        self._layer_orders.clear()

    def _bake_property(self, property_name: str, layer: Optional[str] = None):
        """Bake current computed value of a property into base state"""
        lt, rt, ltrig, rtrig = self._compute_current_state()

        if property_name == "left_thumb":
            self._base_left_thumb = clamp_stick_vec2(lt)
        elif property_name == "right_thumb":
            self._base_right_thumb = clamp_stick_vec2(rt)
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
    # FRAME LOOP
    # ========================================================================

    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
        if self._frame_loop_job is None:
            self._frame_loop_job = cron.interval("16ms", self._tick_frame)
            self._last_frame_time = None

    def _stop_frame_loop(self):
        """Stop the frame loop"""
        if self._frame_loop_job is not None:
            cron.cancel(self._frame_loop_job)
            self._frame_loop_job = None
            self._last_frame_time = None

            for callback in self._stop_callbacks:
                try:
                    callback()
                except Exception:
                    pass
            self._stop_callbacks.clear()

    def _tick_frame(self):
        """Main frame loop tick"""
        current_time, dt = self._calculate_delta_time()
        if dt is None:
            return

        # Check debounce
        self._check_debounce_pending(current_time)

        # Advance all builders
        phase_transitions = self._advance_all_builders(current_time)

        # Compute current state
        lt, rt, ltrig, rtrig = self._compute_current_state()

        # Clamp outputs
        lt = clamp_stick_vec2(lt)
        rt = clamp_stick_vec2(rt)
        ltrig = clamp_trigger_value(ltrig)
        rtrig = clamp_trigger_value(rtrig)

        # Apply to hardware (single batch update)
        self._apply_to_hardware(lt, rt, ltrig, rtrig)

        # Remove completed builders
        self._remove_completed_builders(current_time)

        # Execute callbacks
        self._execute_phase_callbacks(phase_transitions)

        # Stop if nothing active
        self._stop_frame_loop_if_done()

    def _calculate_delta_time(self) -> tuple[float, Optional[float]]:
        now = time.perf_counter()
        if self._last_frame_time is None:
            self._last_frame_time = now
            return (now, None)
        dt = now - self._last_frame_time
        self._last_frame_time = now
        return (now, dt)

    def _advance_all_builders(self, current_time: float) -> list[tuple['ActiveBuilder', str]]:
        """Advance all groups and track phase transitions"""
        phase_transitions = []

        for layer, group in list(self._layer_groups.items()):
            group_transitions, builders_to_remove = group.advance(current_time)
            phase_transitions.extend(group_transitions)

            if not hasattr(group, '_pending_bake_results'):
                group._pending_bake_results = []
            group._pending_bake_results.extend(builders_to_remove)

        return phase_transitions

    def _remove_completed_builders(self, current_time: float) -> set[str]:
        """Remove completed builders from groups"""
        completed_layers = set()

        for layer, group in list(self._layer_groups.items()):
            builders_to_remove = []

            for builder in group.builders:
                if builder._marked_for_removal:
                    builders_to_remove.append(builder)
                    continue

                completed_phase, _ = builder.advance(current_time)
                if completed_phase is not None:
                    builders_to_remove.append(builder)
                elif builder.lifecycle.should_be_garbage_collected():
                    builders_to_remove.append(builder)

            # Process pending bake results
            if hasattr(group, '_pending_bake_results'):
                for builder, bake_result in group._pending_bake_results:
                    if builder in group.builders:
                        if bake_result == "bake_to_base":
                            self._bake_group_to_base(group)
                group._pending_bake_results = []

            for builder in builders_to_remove:
                group.remove_builder(builder)

            if not group.should_persist():
                if layer in self._layer_groups:
                    del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]
                completed_layers.add(layer)

        return completed_layers

    def _execute_phase_callbacks(self, phase_transitions: list[tuple['ActiveBuilder', str]]):
        for builder, completed_phase in phase_transitions:
            builder.lifecycle.execute_callbacks(completed_phase)

    def _check_debounce_pending(self, current_time: float):
        ready_keys = []
        for key, (target_time, config, is_base, cron_job) in list(self._debounce_pending.items()):
            if current_time >= target_time:
                ready_keys.append(key)

        for key in ready_keys:
            target_time, config, is_base, cron_job = self._debounce_pending[key]
            del self._debounce_pending[key]
            if cron_job is not None:
                cron.cancel(cron_job)
            config.behavior = None
            config.behavior_args = ()
            from .builder import ActiveBuilder
            actual_builder = ActiveBuilder(config, self, is_base)
            self.add_builder(actual_builder)

    def _stop_frame_loop_if_done(self):
        if not self._should_frame_loop_be_active():
            self._stop_frame_loop()

    def _should_frame_loop_be_active(self) -> bool:
        """Check if frame loop should be running"""
        # Any builder with incomplete lifecycle
        for group in self._layer_groups.values():
            for builder in group.builders:
                if not builder.lifecycle.is_complete():
                    return True

        # Any pending debounce
        if self._debounce_pending:
            return True

        return False

    # ========================================================================
    # HARDWARE
    # ========================================================================

    def _apply_to_hardware(self, lt: Vec2, rt: Vec2, ltrig: float, rtrig: float):
        """Apply state to vgamepad hardware using single batch update"""
        from . import gamepad_api

        if not gamepad_api.is_available():
            return

        gamepad_api.update_all(lt.x, lt.y, rt.x, rt.y, ltrig, rtrig)
