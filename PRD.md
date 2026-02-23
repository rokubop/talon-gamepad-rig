# Gamepad Rig - Product Requirements Document

## Overview

A smooth interpolation and rate-based control system for gamepad inputs, adapting the mouse_rig architecture for analog sticks and triggers. Enables voice-controlled gamepad manipulation with professional-grade timing and easing.

## Vision

```python
gamepad = actions.user.gamepad_rig()

# Analog sticks - smooth transitions
gamepad.left_thumb.to(1, 0)                           # instant full right
gamepad.left_thumb.to(1, 0).over(1000)                # smooth transition over 1s
gamepad.left_thumb.magnitude.to(0.5).over(100)        # walk → run transition
gamepad.left_thumb.direction.by(90).over(1000)        # rotate 90° over 1s
gamepad.right_thumb(0.3, 0.5)                         # shorthand

# Triggers - smooth press/release
gamepad.left_trigger.to(1).over(100).revert(100)      # smooth press and release
gamepad.right_trigger.to(0.5)                         # half press for aiming

# Layer system for modifiers
gamepad.layer("aim").left_thumb.magnitude.override.to(0.3)  # slower for precision
gamepad.right_thumb.offset.magnitude.add(0.2)               # temporary sensitivity boost

# Chaining and callbacks
gamepad.left_thumb.to(1, 0).over(500).hold(1000).then(lambda: print("done"))
gamepad.stop()                                        # center all sticks, release all triggers
gamepad.stop(500)                                     # smooth stop over 500ms
```

## Architecture Mapping

### From mouse_rig → gamepad_rig

```
mouse_rig/                  →  gamepad/
├── mouse_rig.py           →  gamepad_rig.py
├── src/                   →  src/
│   ├── builder.py         →  builder.py (adapt for gamepad properties)
│   ├── core.py            →  core.py (adapt Vec2 for bounded stick values)
│   ├── mouse_api.py       →  gamepad_api.py (vgamepad backend)
│   ├── contracts.py       →  contracts.py (gamepad-specific contracts)
│   ├── lifecycle.py       →  lifecycle.py (REUSE - interpolation logic)
│   ├── rate_utils.py      →  rate_utils.py (REUSE)
│   ├── queue.py           →  queue.py (REUSE)
│   └── state.py           →  state.py (gamepad state)
```

**Strategy**: Copy entire `src/` folder and adapt. (Future: extract common core)

## API Specification

### Entry Point

```python
gamepad = actions.user.gamepad_rig()
```

### Properties

#### Analog Sticks (Vec2)
- `gamepad.left_thumb` - Vec2 property, range (-1, -1) to (1, 1)
- `gamepad.right_thumb` - Vec2 property, range (-1, -1) to (1, 1)

**Operations:**
- `.to(x, y)` - Set absolute position
- `.by(dx, dy)` - Relative adjustment
- `.add(dx, dy)` - Additive (alias for .by)
- `(x, y)` - Shorthand for .to(x, y)

**Subproperties:**
- `.magnitude` - Scalar (0 to 1) - distance from center
- `.direction` - Vec2 (normalized) - direction vector
- `.x` - Scalar (-1 to 1) - horizontal component
- `.y` - Scalar (-1 to 1) - vertical component

**Direction operations:**
- `.direction.to(x, y)` - Set absolute direction (Vec2)
- `.direction.by(degrees)` - Rotate by degrees (like mouse_rig)

#### Triggers (Scalar)
- `gamepad.left_trigger` - Scalar property, range 0 to 1
- `gamepad.right_trigger` - Scalar property, range 0 to 1

**Operations:**
- `.to(value)` - Set absolute value
- `.by(delta)` - Relative adjustment
- `.add(delta)` - Additive (alias for .by)
- `(value)` - Shorthand for .to(value)

**Note:** `.x` and `.y` subproperties on sticks allow individual axis control for state purposes:
```python
gamepad.left_thumb.x.to(0.5)  # Set x-axis only, preserve y-axis
gamepad.left_thumb.y.to(-0.3) # Set y-axis only, preserve x-axis
```

### Timing & Easing

All properties support:
```python
.over(duration_ms, easing="linear")
.over(rate=units_per_second)
.hold(duration_ms)
.then(callback)
.revert(duration_ms, easing="linear")
```

**Easing functions**: `"linear"`, `"ease_in"`, `"ease_out"`, `"ease_in_out"`, etc.

### State Decomposition

Like mouse_rig's speed/direction relationship:

```python
# Setting magnitude preserves direction
gamepad.left_thumb.direction.to(1, 0)  # right
gamepad.left_thumb.magnitude.to(0.8)   # 80% in that direction → (0.8, 0)

# Setting direction preserves magnitude
gamepad.left_thumb.magnitude.to(0.5)
gamepad.left_thumb.direction.by(90).over(500)  # rotate 90° over 500ms, keeps magnitude 0.5
```

### Layer System

Support offset/override/scale modes for temporary modifiers:

```python
# Offset - additive layer
gamepad.offset.left_thumb.magnitude.add(0.2)
gamepad.layer("boost").left_thumb.magnitude.offset.add(0.3)

# Override - replacement layer
gamepad.layer("aim").left_thumb.magnitude.override.to(0.3)
gamepad.layer("aim").revert()
gamepad.layer("aim").revert(500, "ease_out")

# Scale - multiplicative layer (less important for gamepad since values are clamped)
gamepad.scale.left_trigger.mul(0.5)
```

### Stop Behavior

```python
# Global stop - center all sticks, release all triggers
gamepad.stop()
gamepad.stop(500)              # smooth stop over 500ms
gamepad.stop(500, "ease_out")

# Individual stop
gamepad.left_thumb.stop()      # center this stick
gamepad.left_trigger.stop()    # release this trigger (→ 0)
```

### Bounds & Clamping

- Sticks auto-clamp to (-1, -1) to (1, 1)
- Triggers auto-clamp to 0 to 1
- Magnitude auto-clamps to 0 to 1
- Direction is always normalized (magnitude handled separately)

## Technical Details

### Rate Calculation

For `.over(rate=units_per_second)`:
- **Sticks**: "units" = stick position range
  - Full range is 2.0 units (-1 to 1)
  - `rate=2` means full deflection in 1 second
  - `rate=1` means from center to edge in 1 second
- **Triggers**: "units" = trigger range
  - Full range is 1.0 unit (0 to 1)
  - `rate=1` means full press in 1 second

### State Persistence

- Sticks hold position until changed (don't auto-center)
- Triggers hold value until changed (don't auto-release)
- Explicit `.stop()` required to return to neutral

### Backend

- Uses `vgamepad` library for virtual Xbox controller
- `gamepad.left_joystick_float(x, y)` for stick updates
- `gamepad.left_trigger_float(value)` for trigger updates
- Frame loop runs at 60fps (same as mouse_rig)
- Backend initialization handled separately (not part of this PRD scope)

**Expected backend setup:**
```python
# In gamepad_api.py
import vgamepad as vg
_gamepad = vg.VX360Gamepad()

def update_left_stick(x: float, y: float):
    _gamepad.left_joystick_float(x, y)
    _gamepad.update()
```

## Scope - Phase 1 (MVP)

### In Scope
- ✅ Left/right analog sticks (Vec2)
- ✅ Left/right triggers (Scalar)
- ✅ Magnitude/direction decomposition for sticks
- ✅ .x/.y individual access for sticks
- ✅ Interpolation with `.over(duration)` and `.over(rate=...)`
- ✅ Easing functions
- ✅ Chaining with `.hold()`, `.then()`, `.revert()`
- ✅ Layer system (offset/override)
- ✅ Auto-clamping bounds
- ✅ Stop behavior (global and individual)
- ✅ Shorthand call syntax `()`

### Out of Scope (Future)
- ❌ Buttons (A, B, X, Y, bumpers, etc.)
- ❌ D-pad
- ❌ Convenience Talon actions (only `gamepad_rig()` for now)
- ❌ Multiple gamepad instances
- ❌ Backend initialization/management
- ❌ Core library extraction (copy src/ for now)

## Implementation Notes

### Key Differences from mouse_rig

1. **Bounded values** - Sticks/triggers have hard limits, mouse doesn't
2. **Two value types** - Vec2 (sticks) and Scalar (triggers), mouse only has Vec2
3. **No pixel accumulation** - Gamepad values are absolute, not cumulative
4. **Different backend** - vgamepad vs mouse APIs

### Reusable Components

- `lifecycle.py` - PropertyAnimator, Lifecycle phases (reuse as-is)
- `rate_utils.py` - Rate calculations, easing functions (reuse as-is)
- `queue.py` - Job queue system (reuse as-is)

### Adaptations Needed

- `builder.py` - Property names, operations, bounds checking
- `core.py` - Vec2 clamping, no pixel accumulation
- `contracts.py` - Gamepad-specific properties and operations
- `state.py` - Stick/trigger state instead of mouse state
- `gamepad_api.py` - vgamepad backend instead of mouse APIs

## Success Criteria

A successful MVP should support:

```python
gamepad = actions.user.gamepad_rig()

# Smooth stick movement
gamepad.left_thumb.to(1, 0).over(1000)

# Circle strafe (360° over 4 seconds at 90 deg/sec)
gamepad.left_thumb.direction.by(360).over(rate=90)

# Walk to run transition
gamepad.left_thumb.magnitude.to(0.5).over(500).hold(1000).to(1).over(500)

# Aim mode with override
gamepad.layer("aim").right_thumb.magnitude.override.to(0.3)
# ... do aiming ...
gamepad.layer("aim").revert(200)

# Smooth trigger press
gamepad.right_trigger.to(1).over(100).revert(100)

# Stop everything smoothly
gamepad.stop(500)
```

## Questions Resolved

1. ✅ **Property naming**: `left_thumb` / `right_thumb` (matches vgamepad)
2. ✅ **Buttons**: Not in Phase 1
3. ✅ **D-pad**: Not in Phase 1
4. ✅ **Code reuse**: Copy src/, adapt as needed
5. ✅ **Entry point**: `actions.user.gamepad_rig()`
6. ✅ **Bounds**: Auto-clamp to valid ranges
7. ✅ **Stop behavior**: Global and individual stop supported
8. ✅ **Rate**: Units per second (1 = center to edge for sticks)
9. ✅ **State**: Persistent until changed
10. ✅ **Backend init**: Out of scope for now
11. ✅ **Operations**: to/by/add/call supported for sticks and triggers
12. ✅ **Decomposition**: magnitude/direction like mouse speed/direction
13. ✅ **Modes**: offset/override/scale supported (scale less important for gamepad)
14. ✅ **Shorthand**: `()` call syntax supported
15. ✅ **Direction rotation**: `.direction.by(degrees)` follows mouse_rig pattern
16. ✅ **Subproperties**: `.x` and `.y` supported for individual axis control
17. ✅ **Frame rate**: 60fps matching mouse_rig

## Next Steps

1. Copy `src/` to `gamepad/src/`
2. Adapt `core.py` for bounded Vec2 values
3. Adapt `contracts.py` for gamepad properties
4. Adapt `state.py` for stick/trigger state
5. Create `gamepad_api.py` with vgamepad backend
6. Adapt `builder.py` for gamepad operations
7. Create `gamepad_rig.py` as entry point
8. Write tests
