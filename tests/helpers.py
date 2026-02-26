"""Test helpers for gamepad-rig tests.

No mocks — real rig sends real output to the virtual gamepad.
Tests verify via r.state.* and visual feedback via gamepad tester.
"""

from ..src import rig, reset_rig


def setup():
    """Clean rig state before a test."""
    reset_rig()


def teardown():
    """Stop rig and clean state after a test."""
    try:
        rig().stop()
    except Exception:
        pass
    reset_rig()
