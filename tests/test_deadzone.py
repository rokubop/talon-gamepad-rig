"""Tests for discovering vgamepad/Windows deadzone and quantization behavior.

Sends known values through vgamepad, reads back via gamepad tester
(which receives gamepad(left_xy) events from Windows), and logs
the round-trip results to discover deadzone thresholds and precision loss.
"""

from talon import cron, actions
from .helpers import setup, teardown
from ..src import rig


def _read_tester_stick():
    """Read current left stick value as reported by Windows via gamepad tester"""
    try:
        x, y = actions.user.gamepad_tester_get_stick("left")
        return x, y
    except Exception:
        return None, None


def test_deadzone_discovery(on_success, on_failure):
    """Send values from 0.0 to 1.0 and log what Windows reports back"""
    setup()

    test_values = [0.0, 0.05, 0.1, 0.15, 0.2, 0.23, 0.24, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    results = []
    index = {"i": 0}

    def send_next():
        if index["i"] >= len(test_values):
            print("\n" + "=" * 60)
            print("DEADZONE DISCOVERY RESULTS")
            print("=" * 60)
            print(f"{'Sent':>8} | {'Received X':>12} | {'Received Y':>12} | {'Loss':>8}")
            print("-" * 60)
            for sent, rx, ry in results:
                loss = sent - rx if sent > 0 and rx is not None else 0
                marker = " <-- DEADZONE" if (rx == 0 or rx is None) and sent > 0 else ""
                rx_str = f"{rx:.4f}" if rx is not None else "N/A"
                ry_str = f"{ry:.4f}" if ry is not None else "N/A"
                print(f"{sent:>8.3f} | {rx_str:>12} | {ry_str:>12} | {loss:>8.4f}{marker}")
            print("=" * 60 + "\n")
            teardown()
            on_success()
            return

        val = test_values[index["i"]]
        r = rig()
        r.left_stick.to(val, 0).run()

        def read_back():
            rx, ry = _read_tester_stick()
            results.append((val, rx, ry))
            index["i"] += 1
            cron.after("50ms", send_next)

        cron.after("100ms", read_back)

    send_next()


def test_deadzone_negative(on_success, on_failure):
    """Send negative values to check if deadzone is symmetric"""
    setup()

    test_values = [-0.05, -0.1, -0.2, -0.24, -0.25, -0.3, -0.5, -1.0]
    results = []
    index = {"i": 0}

    def send_next():
        if index["i"] >= len(test_values):
            print("\n" + "=" * 60)
            print("NEGATIVE DEADZONE RESULTS")
            print("=" * 60)
            print(f"{'Sent':>8} | {'Received X':>12}")
            print("-" * 60)
            for sent, rx, ry in results:
                rx_str = f"{rx:.4f}" if rx is not None else "N/A"
                marker = " <-- DEADZONE" if (rx == 0 or rx is None) and sent != 0 else ""
                print(f"{sent:>8.3f} | {rx_str:>12}{marker}")
            print("=" * 60 + "\n")
            teardown()
            on_success()
            return

        val = test_values[index["i"]]
        r = rig()
        r.left_stick.to(val, 0).run()

        def read_back():
            rx, ry = _read_tester_stick()
            results.append((val, rx, ry))
            index["i"] += 1
            cron.after("50ms", send_next)

        cron.after("100ms", read_back)

    send_next()


def test_deadzone_diagonal(on_success, on_failure):
    """Check deadzone on diagonals (both axes nonzero)"""
    setup()

    test_values = [
        (0.1, 0.1), (0.15, 0.15), (0.2, 0.2), (0.25, 0.25),
        (0.3, 0.3), (0.5, 0.5), (0.7, 0.7),
    ]
    results = []
    index = {"i": 0}

    def send_next():
        if index["i"] >= len(test_values):
            print("\n" + "=" * 60)
            print("DIAGONAL DEADZONE RESULTS")
            print("=" * 60)
            print(f"{'Sent X':>8} {'Sent Y':>8} | {'Recv X':>10} {'Recv Y':>10} | {'Sent Mag':>10} {'Recv Mag':>10}")
            print("-" * 60)
            for (sx, sy), rx, ry in results:
                sent_mag = (sx ** 2 + sy ** 2) ** 0.5
                if rx is not None and ry is not None:
                    recv_mag = (rx ** 2 + ry ** 2) ** 0.5
                    marker = " <-- DEADZONE" if rx == 0 and ry == 0 else ""
                    print(f"{sx:>8.3f} {sy:>8.3f} | {rx:>10.4f} {ry:>10.4f} | {sent_mag:>10.4f} {recv_mag:>10.4f}{marker}")
                else:
                    print(f"{sx:>8.3f} {sy:>8.3f} | {'N/A':>10} {'N/A':>10} | {sent_mag:>10.4f} {'N/A':>10}")
            print("=" * 60 + "\n")
            teardown()
            on_success()
            return

        sx, sy = test_values[index["i"]]
        r = rig()
        r.left_stick.to(sx, sy).run()

        def read_back():
            rx, ry = _read_tester_stick()
            results.append(((sx, sy), rx, ry))
            index["i"] += 1
            cron.after("50ms", send_next)

        cron.after("100ms", read_back)

    send_next()


def test_quantization_precision(on_success, on_failure):
    """Fine-grained test around small values to find exact deadzone edge"""
    setup()

    test_values = [round(i * 0.01, 2) for i in range(0, 35)]
    results = []
    index = {"i": 0}

    def send_next():
        if index["i"] >= len(test_values):
            print("\n" + "=" * 60)
            print("QUANTIZATION PRECISION (0.00 to 0.34)")
            print("=" * 60)
            print(f"{'Sent':>8} | {'Received':>10} | {'Int16':>8} | {'Note':>20}")
            print("-" * 60)
            first_nonzero = None
            for sent, rx, ry in results:
                int16_val = round(sent * 32767)
                note = ""
                if (rx is None or rx == 0) and sent > 0:
                    note = "DEADZONE"
                elif first_nonzero is None and rx is not None and rx != 0:
                    first_nonzero = sent
                    note = "FIRST NONZERO"
                rx_str = f"{rx:.4f}" if rx is not None else "N/A"
                print(f"{sent:>8.2f} | {rx_str:>10} | {int16_val:>8d} | {note:>20}")
            if first_nonzero is not None:
                print(f"\nDeadzone edge: ~{first_nonzero:.2f} (int16: {round(first_nonzero * 32767)})")
            print("=" * 60 + "\n")
            teardown()
            on_success()
            return

        val = test_values[index["i"]]
        r = rig()
        r.left_stick.to(val, 0).run()

        def read_back():
            rx, ry = _read_tester_stick()
            results.append((val, rx, ry))
            index["i"] += 1
            cron.after("50ms", send_next)

        cron.after("100ms", read_back)

    send_next()


def _read_tester_trigger():
    """Read current left trigger value as reported by Windows via gamepad tester"""
    try:
        return actions.user.gamepad_tester_get_trigger("l2")
    except Exception:
        return None


def test_trigger_deadzone(on_success, on_failure):
    """Send trigger values from 0.0 to 1.0 and log what Windows reports back"""
    setup()

    test_values = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    results = []
    index = {"i": 0}

    def send_next():
        if index["i"] >= len(test_values):
            print("\n" + "=" * 60)
            print("TRIGGER DEADZONE RESULTS")
            print("=" * 60)
            print(f"{'Sent':>8} | {'Received':>10} | {'Byte':>6} | {'Note':>20}")
            print("-" * 60)
            first_nonzero = None
            for sent, received in results:
                byte_val = round(sent * 255)
                note = ""
                if (received is None or received == 0) and sent > 0:
                    note = "DEADZONE"
                elif first_nonzero is None and received is not None and received != 0:
                    first_nonzero = sent
                    note = "FIRST NONZERO"
                rv = f"{received:.4f}" if received is not None else "N/A"
                print(f"{sent:>8.3f} | {rv:>10} | {byte_val:>6d} | {note:>20}")
            if first_nonzero is not None:
                print(f"\nTrigger deadzone edge: ~{first_nonzero:.3f} (byte: {round(first_nonzero * 255)})")
            else:
                print("\nNo trigger deadzone detected")
            print("=" * 60 + "\n")
            teardown()
            on_success()
            return

        val = test_values[index["i"]]
        r = rig()
        r.left_trigger.to(val).run()

        def read_back():
            received = _read_tester_trigger()
            results.append((val, received))
            index["i"] += 1
            cron.after("50ms", send_next)

        cron.after("100ms", read_back)

    send_next()


DEADZONE_TESTS = [
    ("deadzone discovery", test_deadzone_discovery),
    ("deadzone negative", test_deadzone_negative),
    ("deadzone diagonal", test_deadzone_diagonal),
    ("quantization precision", test_quantization_precision),
    ("trigger deadzone", test_trigger_deadzone),
]
