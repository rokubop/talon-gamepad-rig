"""Layer Group - Container for builders on a single layer

Each layer (base.left_thumb, left_thumb.offset, or user-named) gets a LayerGroup.
Groups manage:
- Active builders (operations in progress)
- Accumulated state (for modifier layers)
- Queue system (sequential execution)
- Lifecycle (for group-level operations like revert)
"""

import time
from typing import Optional, Any, Callable, TYPE_CHECKING
from collections import deque
from .core import Vec2, is_vec2, EPSILON
from .lifecycle import Lifecycle

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class LayerGroup:
    """Container for all builders on a single layer

    Scope examples:
    - Base: base.left_thumb, base.left_trigger
    - Auto-modifier: left_thumb.offset, left_trigger.override
    - User-named: "aim", "boost", etc.
    """

    def __init__(
        self,
        layer_name: str,
        property: str,
        mode: Optional[str],
        layer_type: str,
        order: Optional[int] = None,
        subproperty: Optional[str] = None,
    ):
        from .contracts import LayerType

        self.layer_name = layer_name
        self.property = property
        self.subproperty = subproperty
        self.mode = mode
        self.layer_type = layer_type
        self.is_base = (layer_type == LayerType.BASE)
        self.order = order
        self.creation_time = time.perf_counter()
        self.builders: list['ActiveBuilder'] = []

        # Accumulated state (for modifier layers - persists after builders complete)
        if property == "direction" and mode == "offset":
            self.accumulated_value: Any = None
        else:
            self.accumulated_value: Any = self._zero_value()

        # Cached final target value (what accumulated_value will be after all builders complete)
        self.final_target: Optional[Any] = None

        # Queue system (sequential execution within this layer)
        self.pending_queue: deque[Callable] = deque()
        self.is_queue_active: bool = False

        # Group-level lifecycle (for rig.layer("name").revert() operations)
        self.group_lifecycle: Optional[Lifecycle] = None

        # Constraints
        self.max_value: Optional[float] = None
        self.min_value: Optional[float] = None

    def _zero_value(self) -> Any:
        """Get zero/identity value for this property"""
        if self.property in ("left_thumb", "right_thumb"):
            if self.subproperty is None:
                return Vec2(0, 0)
            elif self.subproperty == "direction":
                return Vec2(1, 0)
            elif self.subproperty in ("magnitude", "x", "y"):
                return 0.0
            return Vec2(0, 0)
        elif self.property in ("left_trigger", "right_trigger"):
            return 0.0
        elif self.property == "direction":
            return Vec2(1, 0)
        else:
            return 0.0

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add a builder to this group"""
        self.builders.append(builder)
        builder.group = self  # Back-reference for builder to find its group
        self._recalculate_final_target()

    def remove_builder(self, builder: 'ActiveBuilder'):
        """Remove a builder from this group"""
        if builder in self.builders:
            self.builders.remove(builder)
            self._recalculate_final_target()

    def clear_builders(self):
        """Remove all active builders (used by replace behavior)"""
        self.builders.clear()
        self._recalculate_final_target()

    def bake_builder(self, builder: 'ActiveBuilder') -> str:
        """Builder completed - bake its value

        Returns:
            "bake_to_base" for base layers (including reverted ones)
            "baked_to_group" for modifier layers
            "reverted" for modifier layers that reverted (clears accumulated value)
        """
        if builder.lifecycle.has_reverted():
            if self.is_base:
                return "bake_to_base"
            else:
                # Modifier layers that revert clear their accumulated value
                if isinstance(self.accumulated_value, Vec2):
                    self.accumulated_value = Vec2(0, 0)
                else:
                    self.accumulated_value = 0.0
                return "reverted"

        value = builder.get_interpolated_value()

        if self.is_base:
            return "bake_to_base"

        # Modifier layers: accumulate in group
        if self.accumulated_value is None:
            if isinstance(value, (int, float)):
                self.accumulated_value = 0.0
            elif isinstance(value, Vec2):
                self.accumulated_value = Vec2(0, 0)
            else:
                self.accumulated_value = value

        self.accumulated_value = self._apply_mode(self.accumulated_value, value, builder.config.mode)

        return "baked_to_group"

    def _apply_mode(self, current: Any, incoming: Any, mode: Optional[str]) -> Any:
        """Apply mode operation to combine values within this layer group"""
        if mode == "offset" or mode == "add":
            if current is None:
                return incoming
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current + incoming
            if isinstance(current, Vec2) and isinstance(incoming, Vec2):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            if isinstance(current, (int, float)) and isinstance(incoming, Vec2):
                return incoming
            if isinstance(current, Vec2) and isinstance(incoming, (int, float)):
                return current
            return incoming
        elif mode == "override":
            return incoming
        elif mode == "scale" or mode == "mul":
            if isinstance(current, Vec2) and isinstance(incoming, (int, float)):
                return Vec2(current.x * incoming, current.y * incoming)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current * incoming
            return incoming
        else:
            # Default: additive
            if isinstance(current, Vec2) and isinstance(incoming, Vec2):
                return Vec2(current.x + incoming.x, current.y + incoming.y)
            if isinstance(current, (int, float)) and isinstance(incoming, (int, float)):
                return current + incoming
            return incoming

    def get_current_value(self) -> Any:
        """Get aggregated value: accumulated + all active builders

        For base layers: Just return the builder's value directly (modes don't apply)
        For modifier layers: Apply modes (offset/override/scale) to accumulated value
        """
        if self.is_base:
            if not self.builders:
                return self.accumulated_value
            last_value = self.accumulated_value
            for builder in self.builders:
                builder_value = builder.get_interpolated_value()
                if builder_value is not None:
                    last_value = builder_value
            return last_value

        # Modifier layers: start with accumulated value and apply modes
        result = self.accumulated_value

        if result is None:
            if self.builders:
                first_value = self.builders[0].get_interpolated_value()
                if isinstance(first_value, Vec2):
                    result = Vec2(0, 0)
                else:
                    result = 0.0
            else:
                result = 0.0

        for builder in self.builders:
            builder_value = builder.get_interpolated_value()
            if builder_value is not None:
                result = self._apply_mode(result, builder_value, builder.config.mode)

        return result

    def _recalculate_final_target(self):
        """Recalculate cached final target value after all builders complete"""
        if not self.builders:
            self.final_target = None
            return

        if self.is_base:
            self.final_target = self.builders[-1].target_value
            return

        result = self.accumulated_value

        if result is None:
            first_target = self.builders[0].target_value
            if isinstance(first_target, Vec2):
                result = Vec2(0, 0)
            else:
                result = 0.0

        for builder in self.builders:
            target = builder.target_value
            if target is not None:
                result = self._apply_mode(result, target, builder.config.mode)

        self.final_target = result

    @property
    def value(self) -> Any:
        """Current value (accumulated + all active builders)"""
        return self.get_current_value()

    @property
    def target(self) -> Optional[Any]:
        """Final target value after all active builders complete (cached)"""
        return self.final_target

    def should_persist(self) -> bool:
        """Should this group stay alive?

        - Base: Only while it has active builders
        - Modifier: If has non-zero accumulated value OR active builders
        """
        if len(self.builders) > 0:
            return True

        if self.is_base:
            return False

        is_zero = self._is_reverted_to_zero()
        return not is_zero

    def _is_reverted_to_zero(self) -> bool:
        """Check if accumulated value is effectively zero/identity"""
        if self.accumulated_value is None:
            return True

        if isinstance(self.accumulated_value, Vec2):
            return (abs(self.accumulated_value.x) < EPSILON and
                    abs(self.accumulated_value.y) < EPSILON)

        if isinstance(self.accumulated_value, (int, float)):
            return abs(self.accumulated_value) < EPSILON

        return False

    def enqueue_builder(self, execution_callback: Callable):
        """Add a builder to this group's queue"""
        self.pending_queue.append(execution_callback)

    def start_next_queued(self) -> bool:
        """Start next queued builder if available

        Returns:
            True if a builder was started, False if queue empty
        """
        if len(self.pending_queue) == 0:
            self.is_queue_active = False
            return False

        callback = self.pending_queue.popleft()
        self.is_queue_active = True
        callback()
        return True

    def on_builder_complete(self, builder: 'ActiveBuilder'):
        """Called when a builder completes - handle queue progression

        Note: Does NOT remove the builder - caller is responsible for removal
        """
        bake_result = self.bake_builder(builder)

        if len(self.pending_queue) > 0:
            self.start_next_queued()

        return bake_result

    def advance(self, current_time: float) -> list[tuple['ActiveBuilder', str]]:
        """Advance all builders in this group

        Returns:
            List of (builder, completed_phase) for callbacks
        """
        phase_transitions = []
        builders_to_remove = []

        for builder in self.builders:
            old_phase = builder.lifecycle.phase
            builder.advance(current_time)
            new_phase = builder.lifecycle.phase

            if old_phase != new_phase and old_phase is not None:
                phase_transitions.append((builder, old_phase))

            is_complete = builder.lifecycle.is_complete()
            should_gc = builder.lifecycle.should_be_garbage_collected()

            if old_phase is not None and new_phase is None:
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))
            elif should_gc:
                builder._marked_for_removal = True
                bake_result = self.on_builder_complete(builder)
                builders_to_remove.append((builder, bake_result))

        return phase_transitions, builders_to_remove

    def __repr__(self) -> str:
        sub = f".{self.subproperty}" if self.subproperty else ""
        return f"<LayerGroup '{self.layer_name}' {self.property}{sub} mode={self.mode} builders={len(self.builders)} accumulated={self.accumulated_value}>"
