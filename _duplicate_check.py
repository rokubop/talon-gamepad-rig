"""Detects if this package is loaded from multiple locations."""
from talon import actions

_duplicate = False
try:
    actions.user.gamepad_rig_version()
    _duplicate = True
except Exception:
    pass

if _duplicate:
    print("============================================================")
    print("DUPLICATE PACKAGE: talon-gamepad-rig (user.gamepad_rig)")
    print("")
    print("  talon-gamepad-rig is already loaded from another location.")
    print("  If using talon-gamekit, remove your standalone talon-gamepad-rig clone.")
    print("  Only one copy of talon-gamepad-rig can exist in talon/user.")
    print("============================================================")
    raise RuntimeError(
        "Duplicate package: talon-gamepad-rig (user.gamepad_rig) is already loaded."
    )
