# Gamepad Rig

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

Smooth interpolation and rate-based control for gamepad inputs. Adapted from mouse_rig architecture.

## Status: Alpha / In Development

This is an initial implementation with basic structure in place. Core functionality is being developed.

## Requirements

- Python package: `vgamepad`
  ```bash
  pip install vgamepad
  ```

## Quick Start

```python
from talon import actions

# Get the gamepad rig
gamepad = actions.user.gamepad_rig()

# Move left stick smoothly
gamepad.left_stick.to(1, 0).over(1000)  # Full right over 1 second

# Press left trigger smoothly
gamepad.left_trigger.to(1).over(100).revert(100)  # Press and release

# Use magnitude/direction decomposition
gamepad.left_stick.magnitude.to(0.5)  # Half speed
gamepad.left_stick.direction.by(90).over(500)  # Rotate 90° over 0.5s

# Layer for temporary modifiers
gamepad.layer("aim").left_stick.magnitude.override.to(0.3)
gamepad.layer("aim").revert(200)  # Revert smoothly

# Stop everything
gamepad.stop()
gamepad.stop(500)  # Stop smoothly over 500ms
```

## Architecture

Based on mouse_rig V2 architecture:

- **[core.py](src/core.py)** - Vec2 with clamping for bounded values
- **[builder.py](src/builder.py)** - Fluent API builder (sticks and triggers)
- **[state.py](src/state.py)** - State management with frame loop
- **[gamepad_api.py](src/gamepad_api.py)** - vgamepad backend integration
- **[contracts.py](src/contracts.py)** - Type contracts and validation
- **[lifecycle.py](src/lifecycle.py)** - Over/Hold/Revert phases (reused)
- **[queue.py](src/queue.py)** - Queue system (reused)
- **[rate_utils.py](src/rate_utils.py)** - Rate calculations (reused)

## API Overview

### Properties

**Analog Sticks** (Vec2, range [-1, 1]):
- `gamepad.left_stick`
- `gamepad.right_stick`

**Triggers** (Scalar, range [0, 1]):
- `gamepad.left_trigger`
- `gamepad.right_trigger`

### Operations

- `.to(x, y)` or `.to(value)` - Set absolute value
- `.by(dx, dy)` or `.by(delta)` - Relative adjustment
- `.add(...)` - Alias for .by()
- `(x, y)` or `(value)` - Shorthand for .to()

### Subproperties (Sticks)

- `.magnitude` - Distance from center (0 to 1)
- `.direction` - Direction vector (normalized)
  - `.direction.to(x, y)` - Set direction
  - `.direction.by(degrees)` - Rotate by degrees
- `.x` - Horizontal component
- `.y` - Vertical component

### Timing & Easing

- `.over(duration_ms, easing="linear")` - Smooth transition
- `.over(rate=units_per_second)` - Rate-based duration
- `.hold(duration_ms)` - Sustain value
- `.then(callback)` - Execute callback after phase
- `.revert(duration_ms, easing="linear")` - Return to base

### Layers

- `.offset` - Additive layer
- `.override` - Replacement layer
- `.scale` - Multiplicative layer (less useful for gamepad)

See [PRD.md](../../talon-gamepad-rig/PRD.md) for complete specification.

## Development Notes

This is a minimal viable implementation. Many features from the PRD are not yet implemented:

**TODO:**
- Full builder execution in state
- Layer composition and evaluation
- Rate-based timing calculations
- Complete stop() implementation
- Mode operations (offset/override/scale)
- Behavior modes (queue/throttle/debounce)
- Comprehensive error handling
- Tests

## Installation

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

git clone <github_url>  # Add github URL to manifest.json
```

## License

See parent directory LICENSE file.
