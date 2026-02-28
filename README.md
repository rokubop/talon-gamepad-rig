# Gamepad Rig (WIP)

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

Actions for controlling a virtual gamepad rig. Advanced control of vectors, magnitudes, directions, timing, easing, rotation, reverses, accounting for deadzones for sticks and triggers, and regular button presses. For Talon.

## Status: Experimental (in development)

Talon actions are still being developed and will likely change soon.

## Installation

### Dependencies

- [**talon-rig-core**](https://github.com/rokubop/talon-rig-core) (v0.5.0+)
- [**vgamepad**](https://pypi.org/project/vgamepad/)

### Development Dependencies

Optional dependencies for development and testing:
- [**talon-ui-elements**](https://github.com/rokubop/talon-ui-elements) (v0.15.0+)

### Install

#### vgamepad is a required dependency that must be installed manually with Talon's `pip` package installer.

Windows (If your TALON_HOME is `~/AppData/Roaming/talon`)
```
~/AppData/Roaming/talon/venv/3.13/Scripts/pip.bat install vgamepad
```

Linux: (Not tested)
```
[TALON_HOME]/bin/pip install vgamepad
```

#### Repositories

Clone the dependencies and this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

# Dependencies
git clone https://github.com/rokubop/talon-rig-core

# This repo
git clone https://github.com/Rokubop/talon-gamepad-rig

# Dev Dependencies (optional)
git clone https://github.com/rokubop/talon-ui-elements
```
