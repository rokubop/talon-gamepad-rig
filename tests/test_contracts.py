"""Contract validation tests - ensure schemas match actual implementation

Prevents drift between validation schemas and actual code.
"""

import inspect


def test_rig_methods_exist(on_success, on_failure):
    """All methods in VALID_RIG_METHODS exist on Rig"""
    try:
        from ..src.contracts import VALID_RIG_METHODS
        from ..src import Rig

        for method_name in VALID_RIG_METHODS:
            if not hasattr(Rig, method_name):
                on_failure(f"Rig.{method_name} doesn't exist but is in VALID_RIG_METHODS")
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_rig_properties_exist(on_success, on_failure):
    """All properties in VALID_RIG_PROPERTIES exist on Rig"""
    try:
        from ..src.contracts import VALID_RIG_PROPERTIES
        from ..src import Rig

        for prop_name in VALID_RIG_PROPERTIES:
            if not hasattr(Rig, prop_name):
                on_failure(f"Rig.{prop_name} doesn't exist but is in VALID_RIG_PROPERTIES")
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_builder_methods_exist(on_success, on_failure):
    """All methods in VALID_BUILDER_METHODS exist on GamepadBuilder"""
    try:
        from ..src.contracts import VALID_BUILDER_METHODS
        from ..src import GamepadBuilder

        for method_name in VALID_BUILDER_METHODS:
            if not hasattr(GamepadBuilder, method_name):
                on_failure(f"GamepadBuilder.{method_name} doesn't exist but is in VALID_BUILDER_METHODS")
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_property_operators_complete(on_success, on_failure):
    """VALID_OPERATORS covers all VALID_PROPERTIES"""
    try:
        from ..src.contracts import VALID_OPERATORS, VALID_PROPERTIES

        valid_operator_methods = ['to', 'add', 'by', 'mul', 'bake']

        for prop in VALID_PROPERTIES:
            if prop not in VALID_OPERATORS:
                on_failure(f"Missing operators definition for property '{prop}'")
                return

            operators = VALID_OPERATORS[prop]
            if len(operators) == 0:
                on_failure(f"No operators defined for property '{prop}'")
                return

            for operator in operators:
                if operator not in valid_operator_methods:
                    on_failure(
                        f"Invalid operator '{operator}' for property '{prop}'. "
                        f"Valid operators: {valid_operator_methods}"
                    )
                    return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_no_extra_schemas(on_success, on_failure):
    """No schemas for non-existent methods"""
    try:
        from ..src.contracts import METHOD_SIGNATURES
        from ..src import GamepadBuilder, Rig

        if METHOD_SIGNATURES is None:
            on_success()  # No schemas defined yet
            return

        for method_name in METHOD_SIGNATURES.keys():
            exists_on_builder = hasattr(GamepadBuilder, method_name)
            exists_on_rig = hasattr(Rig, method_name)

            if not (exists_on_builder or exists_on_rig):
                on_failure(
                    f"Schema exists for '{method_name}' but method doesn't exist on GamepadBuilder or Rig"
                )
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_easings_are_implemented(on_success, on_failure):
    """All VALID_EASINGS are implemented"""
    try:
        from ..src.contracts import VALID_EASINGS
        from ..src.core import EASING_FUNCTIONS

        if VALID_EASINGS is None:
            on_success()  # Not yet initialized
            return

        for easing in VALID_EASINGS:
            if easing not in EASING_FUNCTIONS:
                on_failure(
                    f"Easing '{easing}' is in VALID_EASINGS but not in EASING_FUNCTIONS.\n"
                    f"Available: {list(EASING_FUNCTIONS.keys())}"
                )
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_interpolations_are_valid(on_success, on_failure):
    """VALID_INTERPOLATIONS contains only valid values"""
    try:
        from ..src.contracts import VALID_INTERPOLATIONS

        if VALID_INTERPOLATIONS is None:
            on_success()  # Not yet initialized
            return

        valid_interpolations = {'lerp', 'slerp', 'linear'}

        for interp in VALID_INTERPOLATIONS:
            if interp not in valid_interpolations:
                on_failure(
                    f"Interpolation '{interp}' is not a valid mode.\n"
                    f"Valid: {valid_interpolations}"
                )
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


def test_valid_layer_state_attrs(on_success, on_failure):
    """VALID_LAYER_STATE_ATTRS covers expected properties"""
    try:
        from ..src.contracts import VALID_LAYER_STATE_ATTRS

        expected = ['left_stick', 'right_stick', 'left_trigger', 'right_trigger']
        for attr in expected:
            if attr not in VALID_LAYER_STATE_ATTRS:
                on_failure(f"Expected '{attr}' in VALID_LAYER_STATE_ATTRS")
                return

        on_success()
    except Exception as e:
        on_failure(f"Unexpected error: {e}")


# ============================================================================
# TEST REGISTRY
# ============================================================================

CONTRACTS_TESTS = [
    ("rig methods exist", test_rig_methods_exist),
    ("rig properties exist", test_rig_properties_exist),
    ("builder methods exist", test_builder_methods_exist),
    ("property operators complete", test_property_operators_complete),
    ("no extra schemas", test_no_extra_schemas),
    ("easings implemented", test_easings_are_implemented),
    ("interpolations valid", test_interpolations_are_valid),
    ("layer state attrs complete", test_valid_layer_state_attrs),
]
