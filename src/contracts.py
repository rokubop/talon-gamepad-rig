"""Gamepad-specific contracts - extends rig-core BaseBuilderConfig"""

from typing import Callable, Any, Optional

# Shared imports will be set by _build_classes
BaseBuilderConfig = None
LifecyclePhase = None
LayerType = None
ConfigError = None
RigUsageError = None
validate_timing = None
validate_has_operation = None
find_closest_match = None
suggest_correction = None
format_validation_error = None
METHOD_SIGNATURES = None
VALID_MODES = None
VALID_EASINGS = None
VALID_INTERPOLATIONS = None
VALID_BEHAVIORS = None
PARAMETER_SUGGESTIONS = None

# Gamepad-specific config class - set by _build_classes
GamepadBuilderConfig = None

# Gamepad-specific constants
VALID_PROPERTIES = ['left_stick', 'right_stick', 'left_trigger', 'right_trigger']

VALID_OPERATORS = {
    'left_stick': ['to', 'add', 'by', 'mul', 'bake'],
    'right_stick': ['to', 'add', 'by', 'mul', 'bake'],
    'left_trigger': ['to', 'add', 'by', 'mul', 'bake'],
    'right_trigger': ['to', 'add', 'by', 'mul', 'bake'],
    # Subproperties
    'magnitude': ['to', 'add', 'by', 'mul', 'bake'],
    'direction': ['to', 'add', 'by', 'mul', 'bake'],
    'x': ['to', 'add', 'by', 'mul', 'bake'],
    'y': ['to', 'add', 'by', 'mul', 'bake'],
}

VALID_RIG_METHODS = [
    'stop', 'layer', 'reverse',
]
VALID_RIG_PROPERTIES = VALID_PROPERTIES

VALID_BUILDER_METHODS = [
    'over', 'hold', 'revert', 'then', 'bake',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
    'offset', 'override', 'scale',
]

VALID_LAYER_STATE_ATTRS = [
    'left_stick', 'right_stick', 'left_trigger', 'right_trigger',
    'magnitude', 'direction', 'x', 'y',
    'current', 'target', 'layers'
]


# Gamepad-specific error classes
class GamepadRigError(Exception):
    """Base exception for gamepad rig errors"""
    pass


class GamepadRigAttributeError(GamepadRigError, AttributeError):
    """Attribute access error"""
    pass


class GamepadRigUsageError(GamepadRigError):
    """Usage error (e.g., calling methods in wrong order)"""
    pass


def _build_classes(core):
    global BaseBuilderConfig, LifecyclePhase, LayerType, ConfigError, RigUsageError
    global validate_timing, validate_has_operation, find_closest_match
    global suggest_correction, format_validation_error
    global METHOD_SIGNATURES, VALID_MODES, VALID_EASINGS, VALID_INTERPOLATIONS
    global VALID_BEHAVIORS, PARAMETER_SUGGESTIONS
    global GamepadBuilderConfig

    # Import shared symbols from core
    BaseBuilderConfig = core.BaseBuilderConfig
    LifecyclePhase = core.LifecyclePhase
    LayerType = core.LayerType
    ConfigError = core.ConfigError
    RigUsageError = core.RigUsageError
    validate_timing = core.validate_timing
    validate_has_operation = core.validate_has_operation
    find_closest_match = core.find_closest_match
    suggest_correction = core.suggest_correction
    format_validation_error = core.format_validation_error
    METHOD_SIGNATURES = core.METHOD_SIGNATURES
    VALID_MODES = core.VALID_MODES
    VALID_EASINGS = core.VALID_EASINGS
    VALID_INTERPOLATIONS = core.VALID_INTERPOLATIONS
    VALID_BEHAVIORS = core.VALID_BEHAVIORS
    PARAMETER_SUGGESTIONS = core.PARAMETER_SUGGESTIONS

    class _GamepadBuilderConfig(core.BaseBuilderConfig):
        """Gamepad-specific builder config - adds subproperty and device field"""
        def __init__(self):
            super().__init__()
            self.device = "gamepad"
            self.subproperty: Optional[str] = None  # magnitude, direction, x, y

        def validate_property_operator(self, mark_invalid=None):
            """Validate operator is valid for this gamepad property"""
            if not self.property and not self.subproperty:
                return
            if not self.operator:
                return

            prop_to_validate = self.subproperty if self.subproperty else self.property
            if prop_to_validate not in VALID_OPERATORS:
                if mark_invalid:
                    mark_invalid()
                valid_str = ', '.join(repr(p) for p in VALID_PROPERTIES)
                raise ConfigError(
                    f"Invalid property: {repr(prop_to_validate)}\n"
                    f"Valid properties: {valid_str}"
                )

            valid_ops = VALID_OPERATORS.get(prop_to_validate, [])
            if self.operator not in valid_ops:
                if mark_invalid:
                    mark_invalid()
                valid_str = ', '.join(repr(op) for op in valid_ops)
                raise ConfigError(
                    f"Invalid operator {repr(self.operator)} for property {repr(prop_to_validate)}\n"
                    f"Valid operators for {prop_to_validate}: {valid_str}"
                )

            if self.subproperty == "direction" and self.operator in ("to", "add", "by"):
                if isinstance(self.value, (tuple, list)) and len(self.value) >= 2:
                    x, y = self.value[0], self.value[1]
                    if x == 0 and y == 0:
                        if mark_invalid:
                            mark_invalid()
                        raise ConfigError(
                            "Invalid direction vector (0, 0).\n\n"
                            "Direction cannot be a zero vector."
                        )

    GamepadBuilderConfig = _GamepadBuilderConfig
