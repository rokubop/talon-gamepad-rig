"""Type contracts and protocols for gamepad rig

Adapted from mouse rig contracts for gamepad-specific properties and operations.
"""

from typing import Protocol, Callable, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Vec2

# Gamepad properties: sticks (Vec2) and triggers (scalar)
VALID_PROPERTIES = ['left_stick', 'right_stick', 'left_trigger', 'right_trigger']

# Valid operators per property type
# Sticks (Vec2): full set of operators
# Triggers (scalar): full set of operators
# Note: .by() for sticks operates on components, .by() for triggers operates on value
# Direction subproperty uses .by(degrees) for rotation
VALID_OPERATORS = {
    'left_stick': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'right_stick': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'left_trigger': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'right_trigger': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    # Subproperties
    'magnitude': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'direction': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'x': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'y': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
}

VALID_MODES = ['offset', 'override', 'scale']

VALID_EASINGS = [
    'linear',
    'ease_in', 'ease_out', 'ease_in_out',
    'ease_in2', 'ease_out2', 'ease_in_out2',
    'ease_in3', 'ease_out3', 'ease_in_out3',
    'ease_in4', 'ease_out4', 'ease_in_out4',
]
VALID_INTERPOLATIONS = ['lerp', 'slerp', 'linear']
VALID_BEHAVIORS = ['stack', 'replace', 'queue', 'throttle', 'debounce']

METHOD_SIGNATURES = {
    'over': {
        'params': ['ms', 'easing', 'rate', 'interpolation'],
        'signature': "over(ms=None, easing='linear', *, rate=None, interpolation='lerp')",
        'validations': {
            'easing': ('easing', VALID_EASINGS),
            'interpolation': ('interpolation', VALID_INTERPOLATIONS)
        }
    },
    'revert': {
        'params': ['ms', 'easing', 'rate', 'interpolation'],
        'signature': "revert(ms=None, easing='linear', *, rate=None, interpolation='lerp')",
        'validations': {
            'easing': ('easing', VALID_EASINGS),
            'interpolation': ('interpolation', VALID_INTERPOLATIONS)
        }
    },
    'hold': {
        'params': ['ms'],
        'signature': 'hold(ms)',
        'validations': {}
    },
    'then': {
        'params': ['callback'],
        'signature': 'then(callback)',
        'validations': {}
    },
    'stop': {
        'params': ['transition_ms', 'easing'],
        'signature': "stop(transition_ms=None, easing='linear')",
        'validations': {
            'easing': ('easing', VALID_EASINGS)
        }
    },
    'bake': {
        'params': ['value'],
        'signature': 'bake(value=True)',
        'validations': {}
    }
}

# Add behavior methods
for behavior in VALID_BEHAVIORS:
    METHOD_SIGNATURES[behavior] = {
        'params': [],
        'signature': f'{behavior}()',
        'validations': {}
    }

VALID_RIG_METHODS = [
    'stop', 'layer', 'offset', 'override', 'scale',
    'left_stick', 'right_stick', 'left_trigger', 'right_trigger'
]

VALID_RIG_PROPERTIES = VALID_PROPERTIES

VALID_BUILDER_METHODS = [
    'over', 'hold', 'revert', 'then', 'bake',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
    'offset', 'override', 'scale',
    'to', 'by', 'add', 'sub', 'mul', 'div'
]

# Parameter name suggestions for common typos
PARAMETER_SUGGESTIONS = {
    'duration': 'ms',
    'time': 'ms',
    'ease': 'easing',
    'callback': 'callback',
}

# Layer state attributes that can be accessed for reading
VALID_LAYER_STATE_ATTRS = [
    'left_stick', 'right_stick', 'left_trigger', 'right_trigger',
    'magnitude', 'direction', 'x', 'y',
    'current', 'target', 'layers'
]

# ============================================================================
# ERROR CLASSES
# ============================================================================

class GamepadRigError(Exception):
    """Base exception for gamepad rig errors"""
    pass


class ConfigError(GamepadRigError):
    """Configuration or validation error"""
    pass


class GamepadRigUsageError(GamepadRigError):
    """Usage error (e.g., calling methods in wrong order)"""
    pass


class GamepadRigAttributeError(GamepadRigError, AttributeError):
    """Attribute access error"""
    pass


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def find_closest_match(name: str, valid_options: list[str], max_distance: int = 3) -> Optional[str]:
    """Find the closest matching string from a list of options"""
    if not valid_options:
        return None

    name_lower = name.lower()
    best_match = None
    best_distance = max_distance + 1

    for option in valid_options:
        option_lower = option.lower()

        # Check for substring match first
        if name_lower in option_lower or option_lower in name_lower:
            return option

        # Simple Levenshtein distance
        distance = _levenshtein(name_lower, option_lower)
        if distance < best_distance:
            best_distance = distance
            best_match = option

    return best_match if best_distance <= max_distance else None


def _levenshtein(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def suggest_correction(provided: str, valid_options: list[str]) -> Optional[str]:
    """Find close match for typos using simple heuristics"""
    provided_lower = provided.lower()

    # Check parameter suggestions first
    if provided_lower in PARAMETER_SUGGESTIONS:
        return PARAMETER_SUGGESTIONS[provided_lower]

    # Check for close matches in valid options
    for option in valid_options:
        if provided_lower in option.lower() or option.lower() in provided_lower:
            return option

    return None


def format_validation_error(
    method: str,
    unknown_params: Optional[list[str]] = None,
    invalid_values: Optional[dict[str, tuple[Any, list]]] = None,
    provided_kwargs: Optional[dict] = None
) -> str:
    """Format a comprehensive validation error message"""
    schema = METHOD_SIGNATURES.get(method, {})
    signature = schema.get('signature', f'{method}(...)')

    msg = f"{method}() validation failed\n"
    msg += f"\nSignature: {signature}\n"

    if provided_kwargs:
        provided_str = ', '.join(f"{k}={repr(v)}" for k, v in provided_kwargs.items())
        msg += f"You provided: {provided_str}\n"

    if unknown_params:
        msg += f"\nUnknown parameter(s): {', '.join(repr(p) for p in unknown_params)}\n"

        # Suggest corrections
        suggestions = []
        valid_params = schema.get('params', [])
        for param in unknown_params:
            suggestion = suggest_correction(param, valid_params)
            if suggestion:
                suggestions.append(f"  - '{param}' → '{suggestion}'")

        if suggestions:
            msg += "\nDid you mean:\n" + "\n".join(suggestions) + "\n"

    if invalid_values:
        msg += "\nInvalid value(s):\n"
        for param, (value, valid_options) in invalid_values.items():
            msg += f"  - {param}={repr(value)}\n"
            msg += f"    Valid options: {', '.join(repr(v) for v in valid_options)}\n"

            # Suggest close match
            if isinstance(value, str):
                suggestion = suggest_correction(value, valid_options)
                if suggestion:
                    msg += f"    Did you mean: {repr(suggestion)}?\n"

    return msg


# ============================================================================
# PROTOCOLS
# ============================================================================

class LifecyclePhase:
    """Represents a phase in the lifecycle (over/hold/revert)"""
    OVER = "over"
    HOLD = "hold"
    REVERT = "revert"


class LayerType:
    """Layer type classification"""
    BASE = "base"                           # base.{property} - transient, auto-bakes
    AUTO_NAMED_MODIFIER = "auto_modifier"   # {property}.{mode} - persistent, auto-named
    USER_NAMED_MODIFIER = "user_modifier"   # custom name + mode - persistent, user-named


class BuilderConfig:
    """Configuration collected by GamepadBuilder during fluent API calls"""
    def __init__(self):
        # Device type
        self.device: str = "gamepad"

        # Property and operator
        self.property: Optional[str] = None  # left_stick, right_stick, left_trigger, right_trigger
        self.subproperty: Optional[str] = None  # magnitude, direction, x, y (for sticks)
        self.operator: Optional[str] = None  # to, by, add, sub, mul, div
        self.value: Any = None
        self.mode: Optional[str] = None  # 'offset', 'override', or 'scale'
        self.order: Optional[int] = None  # Explicit layer ordering

        # Identity
        self.layer_name: Optional[str] = None  # Layer name
        self.layer_type: str = LayerType.BASE  # Default to base
        self.is_user_named: bool = False  # True if user explicitly provided layer name

        # Behavior
        self.behavior: Optional[str] = None  # stack, replace, queue, throttle
        self.behavior_args: tuple = ()

        # Lifecycle timing
        self.over_ms: Optional[float] = None
        self.over_easing: str = "linear"
        self.over_rate: Optional[float] = None
        self.over_interpolation: str = "lerp"

        self.hold_ms: Optional[float] = None

        self.revert_ms: Optional[float] = None
        self.revert_easing: str = "linear"
        self.revert_rate: Optional[float] = None
        self.revert_interpolation: str = "lerp"

        # Callbacks
        self.then_callbacks: list[tuple[str, Callable]] = []

        # Persistence
        self.bake_value: Optional[bool] = None

        # (No synchronous mode for gamepad - all operations go through frame loop)

    # ========================================================================
    # LAYER CLASSIFICATION
    # ========================================================================

    def is_base_layer(self) -> bool:
        return self.layer_type == LayerType.BASE

    def is_modifier_layer(self) -> bool:
        return self.layer_type in (LayerType.AUTO_NAMED_MODIFIER, LayerType.USER_NAMED_MODIFIER)

    def is_auto_named_modifier(self) -> bool:
        return self.layer_type == LayerType.AUTO_NAMED_MODIFIER

    def is_user_named_modifier(self) -> bool:
        return self.layer_type == LayerType.USER_NAMED_MODIFIER

    def get_effective_behavior(self) -> str:
        """Get behavior with defaults applied"""
        if self.behavior is not None:
            return self.behavior
        # Default: .to() = replace, others = stack
        if self.operator == "to":
            return "replace"
        else:
            return "stack"

    def get_effective_bake(self) -> bool:
        """Get bake setting with defaults applied"""
        if self.bake_value is not None:
            return self.bake_value
        # Default: base layers auto-bake, modifier layers don't
        return self.is_base_layer()

    def validate_method_kwargs(self, method: str, mark_invalid: Optional[Callable[[], None]] = None, **kwargs) -> None:
        """Validate kwargs for a method call"""
        if not kwargs:
            return

        schema = METHOD_SIGNATURES.get(method)
        if not schema:
            return

        valid_params = schema['params']
        validations = schema.get('validations', {})

        # Check for unknown parameters
        unknown = [k for k in kwargs.keys() if k not in valid_params]

        # Check for invalid values
        invalid_values = {}
        for param, value in kwargs.items():
            if param in validations:
                param_name, valid_options = validations[param]
                if value is not None and value not in valid_options:
                    invalid_values[param] = (value, valid_options)

        # Raise error if any issues found
        if unknown or invalid_values:
            if mark_invalid:
                mark_invalid()
            raise ConfigError(format_validation_error(
                method=method,
                unknown_params=unknown if unknown else None,
                invalid_values=invalid_values if invalid_values else None,
                provided_kwargs=kwargs
            ))

    def validate_property_operator(self, mark_invalid: Optional[Callable[[], None]] = None) -> None:
        """Validate that operator is valid for the property"""
        if not self.property and not self.subproperty:
            return
        if not self.operator:
            return

        # Use subproperty for validation if set (e.g., magnitude, direction)
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

        # Validate direction values (zero vector not allowed)
        if self.subproperty == "direction" and self.operator in ("to", "add", "by"):
            if isinstance(self.value, (tuple, list)) and len(self.value) >= 2:
                x, y = self.value[0], self.value[1]
                if x == 0 and y == 0:
                    if mark_invalid:
                        mark_invalid()
                    raise ConfigError(
                        "Invalid direction vector (0, 0).\n\n"
                        "Direction cannot be a zero vector.\n\n"
                        "To center the stick, use:\n"
                        "  gamepad.left_stick.to(0, 0)  # Center stick\n"
                        "  gamepad.stop()                # Center all sticks/release triggers"
                    )

    def validate_mode(self, mark_invalid: Optional[Callable[[], None]] = None) -> None:
        """Validate that mode is set for layer operations"""
        if not self.is_user_named:
            return

        if self.mode is None:
            if mark_invalid:
                mark_invalid()
            raise ConfigError(
                f"Layer operations require an explicit mode.\n\n"
                f"Available modes:\n"
                f"  - .offset   - offset the value\n"
                f"  - .override - replace the value\n"
                f"  - .scale    - multiply the value\n\n"
                f"Examples:\n"
                f"  gamepad.layer('aim').left_stick.magnitude.override.to(0.3)\n"
                f"  gamepad.layer('boost').left_trigger.offset.add(0.2)"
            )

        if self.mode not in VALID_MODES:
            if mark_invalid:
                mark_invalid()
            valid_str = ', '.join(repr(m) for m in VALID_MODES)
            raise ConfigError(
                f"Invalid mode: {repr(self.mode)}\n"
                f"Valid modes: {valid_str}"
            )


def validate_timing(value: Any, param_name: str, method: str = None, mark_invalid: Optional[Callable[[], None]] = None) -> Optional[float]:
    """Validate timing parameters (ms, rate, etc.)"""
    if value is None:
        return None

    method_str = f".{method}({param_name}=...)" if method else f"'{param_name}'"

    if not isinstance(value, (int, float)):
        if mark_invalid:
            mark_invalid()
        raise TypeError(
            f"Invalid type for {method_str}\n\n"
            f"Expected: number (int or float)\n"
            f"Got: {type(value).__name__} = {repr(value)}\n\n"
            f"Timing parameters must be numeric values."
        )

    float_value = float(value)

    if float_value < 0:
        if mark_invalid:
            mark_invalid()
        raise ConfigError(
            f"Negative duration not allowed: {method_str}\n\n"
            f"Got: {value}\n\n"
            f"Duration values must be >= 0."
        )

    return float_value


def validate_has_operation(config: 'BuilderConfig', method_name: str, mark_invalid: Optional[Callable[[], None]] = None) -> None:
    """Validate that a timing method has a prior operation to apply to"""
    if config.property is None or config.operator is None:
        if mark_invalid:
            mark_invalid()
        raise GamepadRigUsageError(
            f"Cannot call .{method_name}() without a prior operation. "
            f"You must set a property first (e.g., .left_stick.to(1, 0), .left_trigger.to(0.5))."
        )
