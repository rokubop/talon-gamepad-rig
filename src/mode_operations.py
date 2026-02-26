"""Gamepad mode operations - imports from rig-core + gamepad-specific wrappers"""

# Will be set by _build_classes
calculate_scalar_target = None
apply_scalar_mode = None
calculate_direction_target = None
apply_direction_mode = None
calculate_position_target = None
apply_position_mode = None
calculate_vector_target = None
apply_vector_mode = None


def _build_classes(core):
    global calculate_scalar_target, apply_scalar_mode
    global calculate_direction_target, apply_direction_mode
    global calculate_position_target, apply_position_mode
    global calculate_vector_target, apply_vector_mode

    calculate_scalar_target = core.mode_operations.calculate_scalar_target
    apply_scalar_mode = core.mode_operations.apply_scalar_mode
    calculate_direction_target = core.mode_operations.calculate_direction_target
    apply_direction_mode = core.mode_operations.apply_direction_mode
    calculate_position_target = core.mode_operations.calculate_position_target
    apply_position_mode = core.mode_operations.apply_position_mode
    calculate_vector_target = core.mode_operations.calculate_vector_target
    apply_vector_mode = core.mode_operations.apply_vector_mode


# Gamepad-specific wrappers
def calculate_stick_target(operator, value, current, mode):
    """Calculate target for stick property. Decomposes Vec2 into magnitude + direction, delegates to calculate_vector_target."""
    from .core import Vec2, EPSILON
    current_mag = current.magnitude() if hasattr(current, 'magnitude') else 0.0
    current_dir = current.normalized() if hasattr(current, 'normalized') and current_mag > EPSILON else Vec2(1, 0)
    return calculate_vector_target(operator, value, current_mag, current_dir, mode)


def calculate_trigger_target(operator, value, current, mode):
    """Calculate target for trigger property. Delegates to calculate_scalar_target."""
    return calculate_scalar_target(operator, value, current, mode)


def apply_stick_mode(mode, value, accumulated):
    """Apply mode to stick value via vector decomposition, clamp result to unit circle."""
    from .core import Vec2, clamp_stick_vec2, EPSILON
    acc_mag = accumulated.magnitude() if hasattr(accumulated, 'magnitude') else 0.0
    acc_dir = accumulated.normalized() if hasattr(accumulated, 'normalized') and acc_mag > EPSILON else Vec2(1, 0)
    new_speed, new_dir = apply_vector_mode(mode, value, acc_mag, acc_dir)
    result = new_dir * new_speed
    return clamp_stick_vec2(result)


def apply_trigger_mode(mode, value, accumulated):
    """Apply mode to trigger value and clamp result to [0, 1]."""
    from .core import clamp_trigger_value
    result = apply_scalar_mode(mode, value, accumulated)
    return clamp_trigger_value(result)
