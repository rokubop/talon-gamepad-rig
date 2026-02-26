"""Core utilities - imports from rig-core + gamepad-specific clamping"""

# These will be set by _build_classes when rig-core loads
Vec2 = None
is_vec2 = None
EPSILON = None
lerp = None
clamp = None
normalize_vector = None
get_easing_function = None
EASING_FUNCTIONS = None


def _build_classes(core):
    global Vec2, is_vec2, EPSILON, lerp, clamp, normalize_vector
    global get_easing_function, EASING_FUNCTIONS
    Vec2 = core.Vec2
    is_vec2 = core.is_vec2
    EPSILON = core.EPSILON
    lerp = core.lerp
    clamp = core.clamp
    normalize_vector = core.normalize_vector
    get_easing_function = core.get_easing_function
    EASING_FUNCTIONS = core.EASING_FUNCTIONS


# Gamepad-specific clamping (stays here)
def clamp_stick_value(v: float) -> float:
    """Clamp value to gamepad stick range [-1, 1]"""
    return max(-1.0, min(1.0, float(v)))


def clamp_trigger_value(v: float) -> float:
    """Clamp value to gamepad trigger range [0, 1]"""
    return max(0.0, min(1.0, float(v)))


def clamp_stick_vec2(vec) -> 'Vec2':
    """Clamp Vec2 to gamepad stick ranges [-1, 1] for both axes"""
    return Vec2(clamp_stick_value(vec.x), clamp_stick_value(vec.y))
