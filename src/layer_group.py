"""LayerGroup for gamepad - extends BaseLayerGroup with subproperty tracking"""

from typing import Optional, Any

# Module-level reference set by _build_classes
GamepadLayerGroup = None


def _build_classes(core):
    global GamepadLayerGroup

    class _GamepadLayerGroup(core.BaseLayerGroup):
        """Extends BaseLayerGroup with gamepad subproperty tracking"""

        def __init__(self, layer_name, property, property_kind, mode, layer_type, order=None, subproperty=None):
            super().__init__(layer_name, property, property_kind, mode, layer_type, order)
            self.subproperty = subproperty

        def copy(self, new_name: str) -> '_GamepadLayerGroup':
            """Create a copy including gamepad-specific subproperty"""
            copy_group = _GamepadLayerGroup(
                layer_name=new_name,
                property=self.property,
                property_kind=self.property_kind,
                mode=self.mode,
                layer_type=self.layer_type,
                order=self.order,
                subproperty=self.subproperty,
            )
            copy_group.source_layer = self.layer_name
            copy_group.builders = self.builders.copy()
            if hasattr(self.accumulated_value, 'x'):
                from .core import Vec2
                copy_group.accumulated_value = Vec2(self.accumulated_value.x, self.accumulated_value.y)
            else:
                copy_group.accumulated_value = self.accumulated_value
            copy_group.final_target = self.final_target
            copy_group.max_value = self.max_value
            copy_group.min_value = self.min_value
            return copy_group

        def __repr__(self):
            sub = f".{self.subproperty}" if self.subproperty else ""
            return f"<GamepadLayerGroup '{self.layer_name}' {self.property}{sub} kind={self.property_kind.value} mode={self.mode} builders={len(self.builders)} accumulated={self.accumulated_value}>"

    GamepadLayerGroup = _GamepadLayerGroup
