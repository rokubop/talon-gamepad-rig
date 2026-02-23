"""Core utilities for gamepad rig - adapted from mouse rig

This module contains low-level utilities:
- Vec2 class for 2D vectors with clamping for bounded stick values
- Easing functions
- No mouse-specific code (removed SubpixelAdjuster, mouse movement APIs)
"""

import math
from typing import Tuple, Union, Optional, Callable
from dataclasses import dataclass


# ============================================================================
# VECTOR UTILITIES
# ============================================================================

# Small value for floating point comparisons (avoid division by zero, etc.)
EPSILON = 1e-10


@dataclass
class Vec2:
    """2D vector with optional clamping for bounded values (gamepad sticks)"""
    x: float
    y: float

    def __repr__(self) -> str:
        return f"Vec2({self.x:.2f}, {self.y:.2f})"

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"

    def __add__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vec2':
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x / scalar, self.y / scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self) -> 'Vec2':
        mag = self.magnitude()
        if mag < EPSILON:
            return Vec2(0, 0)
        return Vec2(self.x / mag, self.y / mag)

    def dot(self, other: 'Vec2') -> float:
        return self.x * other.x + self.y * other.y

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def copy(self) -> 'Vec2':
        """Return a copy of this vector"""
        return Vec2(self.x, self.y)

    def clamped(self, min_x: float = -1.0, max_x: float = 1.0, 
                min_y: float = -1.0, max_y: float = 1.0) -> 'Vec2':
        """Return a new Vec2 with components clamped to specified ranges
        
        Default range is [-1, 1] for gamepad sticks.
        
        Args:
            min_x: Minimum x value
            max_x: Maximum x value
            min_y: Minimum y value
            max_y: Maximum y value
            
        Returns:
            New Vec2 with clamped components
        """
        return Vec2(
            max(min_x, min(max_x, self.x)),
            max(min_y, min(max_y, self.y))
        )

    def clamped_magnitude(self, max_magnitude: float = 1.0) -> 'Vec2':
        """Return a new Vec2 with magnitude clamped to specified maximum
        
        Useful for circular deadzone/clamping on gamepad sticks.
        Direction is preserved, only magnitude is reduced if necessary.
        
        Args:
            max_magnitude: Maximum allowed magnitude (default 1.0 for gamepad sticks)
            
        Returns:
            New Vec2 with clamped magnitude
        """
        mag = self.magnitude()
        if mag <= max_magnitude or mag < EPSILON:
            return self.copy()
        return self.normalized() * max_magnitude

    def to_cardinal(self) -> Optional[str]:
        """Convert vector to cardinal/intercardinal direction string

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if vector is zero.

        Uses a threshold to distinguish between pure cardinal directions
        (within 22.5 degrees of an axis) and intercardinal/diagonal directions.

        Examples:
            Vec2(1, 0).to_cardinal() -> "right"
            Vec2(-1, 0).to_cardinal() -> "left"
            Vec2(0, -1).to_cardinal() -> "up"
            Vec2(0, 1).to_cardinal() -> "down"
            Vec2(1, -1).to_cardinal() -> "up_right"  # 45 degrees diagonal
            Vec2(0.9, -0.2).to_cardinal() -> "right"  # Within 22.5 degrees of right
            Vec2(0, 0).to_cardinal() -> None
        """
        if self.x == 0 and self.y == 0:
            return None

        # Threshold for pure cardinal vs intercardinal
        # tan(67.5 degrees) ≈ 2.414, which is halfway between pure cardinal (90 degrees) and diagonal (45 degrees)
        # This means directions within ±22.5 degrees of an axis are considered pure cardinal
        threshold = 2.414

        # Pure cardinal directions (within 22.5 degrees of axis)
        if abs(self.x) > abs(self.y) * threshold:
            return "right" if self.x > 0 else "left"
        if abs(self.y) > abs(self.x) * threshold:
            return "up" if self.y < 0 else "down"

        # Intercardinal/diagonal directions
        if self.x > 0 and self.y < 0:
            return "up_right"
        elif self.x < 0 and self.y < 0:
            return "up_left"
        elif self.x > 0 and self.y > 0:
            return "down_right"
        elif self.x < 0 and self.y > 0:
            return "down_left"

        # Fallback (shouldn't happen)
        return "right"

    @staticmethod
    def from_tuple(t: Union[Tuple[float, float], 'Vec2']) -> 'Vec2':
        if isinstance(t, Vec2):
            return t
        return Vec2(t[0], t[1])


def is_vec2(value) -> bool:
    """Check if value is a Vec2 instance"""
    return isinstance(value, Vec2)


def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    mag = math.sqrt(x ** 2 + y ** 2)
    if mag < EPSILON:
        return (0.0, 0.0)
    return (x / mag, y / mag)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between two values"""
    return a + (b - a) * t


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]"""
    return max(min_val, min(max_val, value))


def clamp_stick_value(value: float) -> float:
    """Clamp value to gamepad stick range [-1, 1]"""
    return max(-1.0, min(1.0, value))


def clamp_trigger_value(value: float) -> float:
    """Clamp value to gamepad trigger range [0, 1]"""
    return max(0.0, min(1.0, value))


def clamp_stick_vec2(vec: Vec2) -> Vec2:
    """Clamp Vec2 to gamepad stick ranges [-1, 1] for both axes"""
    return vec.clamped(-1.0, 1.0, -1.0, 1.0)


# ============================================================================
# EASING FUNCTIONS
# ============================================================================

def ease_linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return 1 - math.cos(t * math.pi / 2)


def ease_out(t: float) -> float:
    return math.sin(t * math.pi / 2)


def ease_in_out(t: float) -> float:
    return (1 - math.cos(t * math.pi)) / 2


def ease_in2(t: float) -> float:
    return t ** 2


def ease_out2(t: float) -> float:
    return 1 - (1 - t) ** 2


def ease_in_out2(t: float) -> float:
    return 2 * t ** 2 if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def ease_in3(t: float) -> float:
    return t ** 3


def ease_out3(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out3(t: float) -> float:
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_in4(t: float) -> float:
    return t ** 4


def ease_out4(t: float) -> float:
    return 1 - (1 - t) ** 4


def ease_in_out4(t: float) -> float:
    return 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2


EASING_FUNCTIONS = {
    "linear": ease_linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
    "ease_in2": ease_in2,
    "ease_out2": ease_out2,
    "ease_in_out2": ease_in_out2,
    "ease_in3": ease_in3,
    "ease_out3": ease_out3,
    "ease_in_out3": ease_in_out3,
    "ease_in4": ease_in4,
    "ease_out4": ease_out4,
    "ease_in_out4": ease_in_out4,
}


def get_easing_function(name: str) -> Callable[[float], float]:
    """Get easing function by name, defaults to linear"""
    return EASING_FUNCTIONS.get(name, ease_linear)
