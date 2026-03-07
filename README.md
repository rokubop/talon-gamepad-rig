# Gamepad Rig

![Version](https://img.shields.io/badge/version-0.8.1-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

Rig for programmatically controlling buttons, triggers, and sticks of a virtual gamepad. For Talon.

Included in [talon-gamekit](https://github.com/rokubop/talon-gamekit), but can be used standalone.

Supported platforms:
- Windows (ViGEmBus)
- Linux (uinput)
- macOS - Not currently supported on macOS

See [vgamepad](https://github.com/yannbouteiller/vgamepad) for more info.

## Usage

```python
gamepad = actions.user.gamepad_rig()

# Buttons
actions.user.gamepad_rig_button_press("a")
actions.user.gamepad_rig_button_release("a")
# buttons: a, b, x, y, lb, rb, l3, r3, start, select, home
# dpad: dpad_up, dpad_down, dpad_left, dpad_right

# Sticks
gamepad.left_stick.to(1, 0)               # full right
gamepad.left_stick.to(0.7, 0.7)           # diagonal
gamepad.left_stick.x.to(0.5)              # x axis only
gamepad.left_stick.magnitude.to(0.5)      # half magnitude, keep direction
gamepad.left_stick.direction.to(1, 0)     # change direction, keep magnitude
gamepad.left_stick.direction.by(90)       # rotate 90 degrees
gamepad.left_stick.by(0.1, 0)             # nudge relative

# Triggers
gamepad.left_trigger.to(1)                # full press
gamepad.left_trigger.to(0.5)              # half press

# Smooth transitions (over, hold, revert)
gamepad.left_stick.to(1, 0).over(500)                        # move over 500ms
gamepad.left_stick.to(1, 0).over(500, "ease_in2")            # with easing
gamepad.left_trigger.to(1).over(200).revert(200)             # press and release
gamepad.left_stick.to(1, 0).over(300).hold(100).revert(300)  # full lifecycle

# Callbacks
gamepad.left_stick.to(1, 0).over(500).then(on_done)   # callback after transition

# Offset or override layers
gamepad.left_stick.magnitude.override.to(1)           # offset magnitude
gamepad.left_stick.magnitude.override.revert(200)     # remove layer smoothly

# Behaviors
replace, stack, queue, throttle, debounce
See [mouse rig](https://github.com/rokubop/talon-mouse-rig/tree/main) for examples - same concepts apply

# Control
gamepad.stop()                                         # stop all immediately
gamepad.stop(500)                                      # decelerate over 500ms
actions.user.gamepad_rig_reset()                       # reset to neutral
actions.user.gamepad_rig_connect()                     # connect virtual gamepad
actions.user.gamepad_rig_disconnect()                  # disconnect virtual gamepad

# State
state = actions.user.gamepad_rig_state()
state.left_stick.x                                     # current x position
state.left_stick.y                                     # current y position
state.left_trigger                                     # current trigger value
```

See `tests/` for comprehensive examples.

## Installation

### Dependencies

- [**talon-rig-core**](https://github.com/rokubop/talon-rig-core) (v0.6.3+)
- [**vgamepad**](https://pypi.org/project/vgamepad/) (Python package)

### 1. Install Python Packages

Install using Talon's bundled pip:

```sh
# Windows
~/AppData/Roaming/talon/venv/[VERSION]/Scripts/pip.bat install vgamepad

# Linux
~/.talon/bin/pip install vgamepad
```

> **Windows**: The first install will prompt you to install the [ViGEmBus](https://github.com/nefarius/ViGEmBus) driver by Nefarius Software Solutions. Accept and install it.
>
> **Linux**: You need access to `uinput`. See the [vgamepad Linux setup guide](https://github.com/yannbouteiller/vgamepad/blob/main/readme/linux.md) for details.
>
> **macOS**: Not supported. See [vgamepad](https://github.com/yannbouteiller/vgamepad) for more info.

### 2. Clone Repositories

Clone the dependencies and this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# Mac/Linux
cd ~/.talon/user

# Windows
cd ~/AppData/Roaming/talon/user

# Dependencies
git clone https://github.com/rokubop/talon-rig-core

# This repo
git clone https://github.com/rokubop/talon-gamepad-rig
```

### Development Dependencies

Optional dependencies for development and testing:
- [**community**](https://github.com/talonhub/community)
- [**talon-ui-elements**](https://github.com/rokubop/talon-ui-elements) (v0.15.0+)

```sh
git clone https://github.com/talonhub/community
git clone https://github.com/rokubop/talon-ui-elements
```

> **Note**: Review code from unfamiliar sources before installing.

## Settings

| Setting | Default | Description |
|---|---|---|
| `user.gamepad_rig_stick_deadzone` | `0.24` | Stick deadzone compensation |
| `user.gamepad_rig_trigger_deadzone` | `0.25` | Trigger deadzone compensation |

See [DEADZONE.md](DEADZONE.md) for technical details.