# Virtual Gamepad Deadzone & Quantization

Discovered via round-trip testing: gamepad-rig -> vgamepad -> Windows XInput -> Talon -> gamepad_tester.

## Stick Deadzone

Windows/XInput applies the standard Xbox deadzone per-axis:

- **Threshold**: ~0.24 (int16: 7864, XInput constant `XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE = 7849`)
- **Symmetric**: Same for positive and negative values
- **Per-axis**: Each axis is deadzone'd independently, not radially

## Trigger Deadzone

- **Threshold**: ~0.25 (byte: 64, XInput constant `XINPUT_GAMEPAD_TRIGGER_THRESHOLD = 30`)
- **Same rescaling pattern**: range [0.25, 1.0] maps to [~0, 1.0]

## Raw vs Compensated

| Sent  | Stick (raw) | Stick (compensated) | Trigger (raw) | Trigger (compensated) |
|-------|-------------|---------------------|---------------|----------------------|
| 0.000 | 0.0000      | 0.0000              | 0.0000        | 0.0000               |
| 0.050 | 0.0000 (dz) | ~0.05               | 0.0000 (dz)   | ~0.05                |
| 0.100 | 0.0000 (dz) | ~0.10               | 0.0000 (dz)   | ~0.10                |
| 0.200 | 0.0000 (dz) | ~0.20               | 0.0000 (dz)   | ~0.20                |
| 0.250 | 0.0138      | ~0.25               | 0.0205        | ~0.25                |
| 0.500 | 0.3425      | ~0.50               | 0.3487        | ~0.50                |
| 0.700 | 0.6055      | ~0.70               | 0.6051        | ~0.70                |
| 1.000 | 1.0000      | 1.0000              | 1.0000        | 1.0000               |

## Compensation

Enabled by default via settings:

- `user.gamepad_rig_stick_deadzone` (default: 0.24)
- `user.gamepad_rig_trigger_deadzone` (default: 0.25)

Set to 0 to disable. The transform is applied at the output boundary in `gamepad_api.update_all()`:

```
# Sticks (per-axis, bidirectional):
hardware = sign(v) * (|v| * (1 - deadzone) + deadzone)    # |v| > 0.001
hardware = 0                                                # |v| <= 0.001

# Triggers (unidirectional):
hardware = v * (1 - deadzone) + deadzone                   # v > 0.001
hardware = 0                                                # v <= 0.001
```

All rig internals (.over(), .revert(), reverse(), layers, interpolation) operate in logical [0, 1] space and are unaffected.

## Diagonal behavior (without compensation)

Per-axis deadzone means diagonals have a square deadzone shape, not circular:

| Sent X | Sent Y | Magnitude | Recv X  | Recv Y  | Recv Mag |
|--------|--------|-----------|---------|---------|----------|
| 0.100  | 0.100  | 0.141     | 0.0000  | 0.0000  | 0.000 (dz) |
| 0.200  | 0.200  | 0.283     | 0.0000  | 0.0000  | 0.000 (dz) |
| 0.250  | 0.250  | 0.354     | 0.0138  | 0.0143  | 0.020 |
| 0.500  | 0.500  | 0.707     | 0.3475  | 0.3989  | 0.529 |

## Quantization

- **Sticks**: float -> int16 [-32768, 32767], ~0.00003 precision per step
- **Triggers**: float -> byte [0, 255], ~0.004 precision per step
