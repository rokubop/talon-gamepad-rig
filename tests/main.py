"""Gamepad Rig Tests

Run via voice command or action:
  actions.user.gamepad_rig_tests()
"""

import inspect
import re
from talon import actions, cron, scope
from ..src import gamepad_api

from .test_stick_basic import STICK_BASIC_TESTS
from .test_stick_over import STICK_OVER_TESTS
from .test_stick_hold_revert import STICK_HOLD_REVERT_TESTS
from .test_stick_advanced import STICK_ADVANCED_TESTS
from .test_trigger import TRIGGER_TESTS
from .test_trigger_advanced import TRIGGER_ADVANCED_TESTS
from .test_layers import LAYER_TESTS
from .test_buttons import BUTTON_TESTS
from .test_state import STATE_TESTS
from .test_stop_reset import STOP_RESET_TESTS
from .test_transitions import TRANSITION_TESTS
from .test_behaviors import BEHAVIOR_TESTS
from .test_validation import VALIDATION_TESTS
from .test_contracts import CONTRACTS_TESTS

TEST_GROUPS = [
    ("Stick Basic", STICK_BASIC_TESTS),
    ("Stick Over", STICK_OVER_TESTS),
    ("Stick Hold/Revert", STICK_HOLD_REVERT_TESTS),
    ("Stick Advanced", STICK_ADVANCED_TESTS),
    ("Trigger", TRIGGER_TESTS),
    ("Trigger Advanced", TRIGGER_ADVANCED_TESTS),
    ("Layers", LAYER_TESTS),
    ("Buttons", BUTTON_TESTS),
    ("State", STATE_TESTS),
    ("Stop/Reset", STOP_RESET_TESTS),
    ("Transitions", TRANSITION_TESTS),
    ("Behaviors", BEHAVIOR_TESTS),
    ("Validation", VALIDATION_TESTS),
    ("Contracts", CONTRACTS_TESTS),
]

_test_runner_state = {
    "running": False,
    "current_test_index": 0,
    "tests": [],
    "stop_requested": False,
    "passed_count": 0,
    "failed_count": 0,
    "all_tests_running": False,
    "group_names": [],
    "opened_tester": False,
}


# =========================================================================
# Gamepad tester integration
# =========================================================================

def _open_gamepad_tester():
    """Open gamepad tester if not already open."""
    tester_showing = "user.gamepad_tester" in (scope.get("tag") or [])
    if not tester_showing:
        try:
            actions.user.gamepad_tester_toggle()
            _test_runner_state["opened_tester"] = True
        except Exception:
            pass


def _close_gamepad_tester():
    """Close gamepad tester if we opened it."""
    if _test_runner_state["opened_tester"]:
        try:
            actions.user.gamepad_tester_toggle()
        except Exception:
            pass
        _test_runner_state["opened_tester"] = False



# =========================================================================
# Test execution
# =========================================================================

def run_single_test(test_name, test_func, on_complete=None, test_group=None, fast_mode=False):
    actions.user.ui_elements_set_state("current_test", test_name)
    actions.user.ui_elements_set_state("test_result", None)

    sanitized_group = re.sub(r'[^a-zA-Z0-9_]', '_', test_group or "")
    sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', test_name)
    test_button_id = f"test_button_{sanitized_group}_{sanitized_name}"
    actions.user.ui_elements_highlight(test_button_id)

    result_delay = "200ms" if fast_mode else "1s"

    def on_test_success():
        actions.user.ui_elements_set_state("test_result", {
            "success": True,
            "message": "PASSED"
        })
        print(f"PASSED: {test_name}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            actions.user.ui_elements_unhighlight(test_button_id)
            if on_complete:
                on_complete(True)
        cron.after(result_delay, clear_and_complete)

    def on_test_failure(error_msg):
        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "FAILED"
        })
        print(f"FAILED: {test_name}")
        print(f"  Error: {error_msg}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            actions.user.ui_elements_unhighlight(test_button_id)
            if on_complete:
                on_complete(False)
        cron.after(result_delay, clear_and_complete)

    def execute_test():
        try:
            sig = inspect.signature(test_func)
            is_async_test = len(sig.parameters) >= 2

            if is_async_test:
                timed_out = {"value": False}

                def guarded_success():
                    if timed_out["value"]:
                        return
                    timed_out["value"] = True
                    on_test_success()

                def guarded_failure(msg=""):
                    if timed_out["value"]:
                        return
                    timed_out["value"] = True
                    on_test_failure(msg)

                def on_timeout():
                    if timed_out["value"]:
                        return
                    timed_out["value"] = True
                    on_test_failure("TIMEOUT (5s)")

                cron.after("5s", on_timeout)
                test_func(guarded_success, guarded_failure)
            else:
                try:
                    test_func()
                    on_test_success()
                except AssertionError as e:
                    on_test_failure(str(e))
                except Exception as e:
                    on_test_failure(f"Exception: {e}")

        except Exception as e:
            actions.user.ui_elements_set_state("test_result", {
                "success": False,
                "message": "ERROR"
            })
            print(f"ERROR: {test_name}")
            print(f"  Exception: {e}")

            def clear_and_complete():
                actions.user.ui_elements_set_state("test_result", None)
                actions.user.ui_elements_set_state("current_test", None)
                actions.user.ui_elements_unhighlight(test_button_id)
                if on_complete:
                    on_complete(False)
            cron.after(result_delay, clear_and_complete)

    execute_test()


def run_all_tests(tests, group_name):
    if _test_runner_state["running"]:
        return

    _test_runner_state["running"] = True
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = tests
    _test_runner_state["group_name"] = group_name
    _test_runner_state["stop_requested"] = False
    _test_runner_state["passed_count"] = 0
    _test_runner_state["failed_count"] = 0

    actions.user.ui_elements_set_state("run_all_active", True)

    def run_next_test():
        if _test_runner_state["stop_requested"]:
            stop_all_tests()
            return

        if _test_runner_state["current_test_index"] >= len(_test_runner_state["tests"]):
            show_summary()
            return

        test_name, test_func = _test_runner_state["tests"][_test_runner_state["current_test_index"]]
        _test_runner_state["current_test_index"] += 1

        def on_test_complete(success):
            if success:
                _test_runner_state["passed_count"] += 1
            else:
                _test_runner_state["failed_count"] += 1

            stop_on_fail = actions.user.ui_elements_get_state("stop_on_fail", True)
            if not success and stop_on_fail:
                print("Stopping test run due to failure")
                show_summary()
            elif _test_runner_state["running"]:
                fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
                delay = "50ms" if fast_mode else "200ms"
                cron.after(delay, run_next_test)

        fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
        run_single_test(test_name, test_func, on_complete=on_test_complete, test_group=group_name, fast_mode=fast_mode)

    run_next_test()


def run_all_tests_global():
    """Run all tests from all groups."""
    if _test_runner_state["running"]:
        return

    all_tests = []
    for group_name, tests in TEST_GROUPS:
        for test_name, test_func in tests:
            all_tests.append((test_name, test_func, group_name))

    _test_runner_state["running"] = True
    _test_runner_state["all_tests_running"] = True
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = all_tests
    _test_runner_state["stop_requested"] = False
    _test_runner_state["passed_count"] = 0
    _test_runner_state["failed_count"] = 0

    actions.user.ui_elements_set_state("run_all_tests_global", True)
    for group_name, _ in TEST_GROUPS:
        actions.user.ui_elements_set_state(f"collapsed_{group_name}", False)

    def run_next_test():
        if _test_runner_state["stop_requested"]:
            finalize()
            return

        if _test_runner_state["current_test_index"] >= len(_test_runner_state["tests"]):
            finalize()
            return

        test_name, test_func, group_name = _test_runner_state["tests"][_test_runner_state["current_test_index"]]
        _test_runner_state["current_test_index"] += 1

        def on_test_complete(success):
            if success:
                _test_runner_state["passed_count"] += 1
            else:
                _test_runner_state["failed_count"] += 1

            stop_on_fail = actions.user.ui_elements_get_state("stop_on_fail", True)
            if not success and stop_on_fail:
                print("Stopping test run due to failure")
                finalize()
            elif _test_runner_state["running"]:
                fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
                delay = "50ms" if fast_mode else "200ms"
                cron.after(delay, run_next_test)

        fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
        run_single_test(test_name, test_func, on_complete=on_test_complete, test_group=group_name, fast_mode=fast_mode)

    def finalize():
        passed = _test_runner_state["passed_count"]
        failed = _test_runner_state["failed_count"]
        total = passed + failed
        all_passed = failed == 0

        actions.user.ui_elements_set_state("test_summary", {
            "passed": passed,
            "failed": failed,
            "total": total,
            "all_passed": all_passed
        })

        print(f"\n{'='*50}")
        print(f"Test Run Complete: {passed}/{total} passed")
        if failed > 0:
            print(f"Failed: {failed}")
        print(f"{'='*50}\n")

        def clear_summary():
            actions.user.ui_elements_set_state("test_summary", None)
            stop_all_tests()

        cron.after("1s", clear_summary)

    run_next_test()


def show_summary():
    passed = _test_runner_state["passed_count"]
    failed = _test_runner_state["failed_count"]
    total = passed + failed
    all_passed = failed == 0

    actions.user.ui_elements_set_state("test_summary", {
        "passed": passed,
        "failed": failed,
        "total": total,
        "all_passed": all_passed
    })

    print(f"\n{'='*50}")
    print(f"Test Run Complete: {passed}/{total} passed")
    if failed > 0:
        print(f"Failed: {failed}")
    print(f"{'='*50}\n")

    def clear_summary():
        actions.user.ui_elements_set_state("test_summary", None)
        stop_all_tests()

    cron.after("1s", clear_summary)


def stop_all_tests():
    _test_runner_state["running"] = False
    _test_runner_state["stop_requested"] = False
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = []
    _test_runner_state["all_tests_running"] = False

    for name in _test_runner_state["group_names"]:
        actions.user.ui_elements_set_state(f"run_all_{name}", False)
    actions.user.ui_elements_set_state("run_all_tests_global", False)
    actions.user.ui_elements_set_state("current_test", None)


def toggle_run_all_tests_global():
    if _test_runner_state["all_tests_running"]:
        _test_runner_state["stop_requested"] = True
        stop_all_tests()
    else:
        run_all_tests_global()


def toggle_run_all(tests, group_name):
    state_key = f"run_all_{group_name}"
    if _test_runner_state["running"] and actions.user.ui_elements_get_state(state_key, False):
        _test_runner_state["stop_requested"] = True
        stop_all_tests()
        actions.user.ui_elements_set_state(state_key, False)
    else:
        actions.user.ui_elements_set_state(f"collapsed_{group_name}", False)
        actions.user.ui_elements_set_state(state_key, True)
        run_all_tests(tests, group_name)


# =========================================================================
# UI
# =========================================================================

def test_runner_ui():
    screen, window, div, button, state, icon, text, checkbox = actions.user.ui_elements(
        ["screen", "window", "div", "button", "state", "icon", "text", "checkbox"]
    )

    fast_mode, set_fast_mode = state.use("fast_mode", True)
    stop_on_fail, set_stop_on_fail = state.use("stop_on_fail", True)

    run_all_tests_active = state.get("run_all_tests_global", False)
    run_all_tests_icon = "stop" if run_all_tests_active else "play"
    run_all_tests_label = "Stop All Tests" if run_all_tests_active else "Run All Tests"
    run_all_tests_color = "#ff5555" if run_all_tests_active else "#0088ff"

    checkbox_props = {
        "background_color": "#1e1e1e",
        "border_color": "#3e3e3e",
        "border_width": 1,
        "border_radius": 2,
    }

    run_all_tests_button = div(
        flex_direction="column",
        justify_content="center",
        align_items="center",
        gap=20,
        margin_bottom=32
    )[
        button(
            padding=10,
            padding_left=16,
            padding_right=16,
            background_color=run_all_tests_color,
            flex_direction="row",
            align_items="center",
            gap=8,
            border_radius=4,
            on_click=lambda e: toggle_run_all_tests_global()
        )[
            icon(run_all_tests_icon, size=14, color="white"),
            text(run_all_tests_label, color="white", font_weight="bold", font_size=13)
        ],
        div(flex_direction="row", gap=24, align_items="center")[
            div(flex_direction="row", gap=8, align_items="center")[
                checkbox(checkbox_props, background_color="#454545", id="fast_mode", checked=fast_mode, on_change=lambda e: set_fast_mode(e.checked)),
                text("Fast", for_id="fast_mode", color="#cccccc", font_size=14, font_weight="bold"),
            ],
            div(flex_direction="row", gap=8, align_items="center")[
                checkbox(checkbox_props, background_color="#454545", id="stop_on_fail", checked=stop_on_fail, on_change=lambda e: set_stop_on_fail(e.checked)),
                text("Stop on fail", for_id="stop_on_fail", color="#cccccc", font_size=14, font_weight="bold"),
            ]
        ]
    ]

    groups = []

    for group_name, tests in TEST_GROUPS:
        state_key = f"run_all_{group_name}"
        run_all_active = state.get(state_key, False)
        is_collapsed, set_collapsed = state.use(f"collapsed_{group_name}", True)
        run_all_icon = "stop" if run_all_active else "play"
        run_all_label = f"Stop All {group_name}" if run_all_active else f"Run All {group_name}"
        run_all_color = "#ff5555" if run_all_active else "#00aa00"
        chevron_icon = "chevron_right" if is_collapsed else "chevron_down"

        group_header = div(
            flex_direction="row",
            gap=10,
            align_items="center",
            padding=8,
            background_color="#222222",
            border_radius=4
        )[
            button(
                padding=8,
                padding_right=12,
                background_color="#2a2a2a",
                flex_direction="row",
                align_items="center",
                gap=8,
                flex=1,
                border_radius=3,
                on_click=lambda e, sc=set_collapsed, ic=is_collapsed: sc(not ic)
            )[
                icon(chevron_icon, size=14, color="white"),
                text(group_name, color="white", font_weight="bold", font_size=14)
            ],
            button(
                padding=8,
                padding_left=12,
                padding_right=12,
                background_color=run_all_color,
                flex_direction="row",
                align_items="center",
                gap=8,
                border_radius=3,
                on_click=lambda e, t=tests, g=group_name: toggle_run_all(t, g)
            )[
                icon(run_all_icon, size=14, color="white"),
                text(run_all_label, color="white", font_weight="bold", font_size=13)
            ]
        ]

        test_buttons = []
        if not is_collapsed:
            test_items = []
            for test_name, test_func in tests:
                sanitized_g = re.sub(r'[^a-zA-Z0-9_]', '_', group_name)
                sanitized_n = re.sub(r'[^a-zA-Z0-9_]', '_', test_name)
                test_button_id = f"test_button_{sanitized_g}_{sanitized_n}"
                test_items.append(
                    button(
                        test_name,
                        id=test_button_id,
                        padding=8,
                        padding_left=16,
                        margin_bottom=2,
                        background_color="#2a2a2a",
                        color="#cccccc",
                        font_size=13,
                        border_radius=2,
                        on_click=lambda e, f=test_func, n=test_name, g=group_name: run_single_test(n, f, test_group=g, fast_mode=actions.user.ui_elements_get_state("fast_mode", True))
                    )
                )

            test_buttons.append(
                div(
                    flex_direction="column",
                    padding=8,
                    padding_top=4,
                    background_color="#1a1a1a",
                    border_radius=4
                )[
                    *test_items
                ]
            )

        groups.append(
            div(
                flex_direction="column",
                margin_bottom=16
            )[
                group_header,
                *test_buttons
            ]
        )

    return screen(align_items="flex_start", justify_content="flex_start")[
        window(
            title="Gamepad Rig Tests",
            on_close=lambda e: (
                e.prevent_default(),
                toggle_test_ui(show=False),
            ),
            padding=12,
            margin=10,
            background_color="#1a1a1a",
            overflow_y="auto",
            max_height=1000
        )[
            run_all_tests_button,
            *groups
        ]
    ]


def test_status_ui():
    screen, div, text, state = actions.user.ui_elements(["screen", "div", "text", "state"])

    current_test = state.get("current_test", None)
    if current_test is None:
        return screen()

    return screen(align_items="center", justify_content="flex_end")[
        div(
            padding=15,
            margin_bottom=250,
            background_color="#0088ffdd",
            border_radius=10
        )[
            text(f"Running: {current_test}", font_size=20, color="white", font_weight="bold")
        ]
    ]


def test_result_ui():
    screen, div, text, state, icon = actions.user.ui_elements(["screen", "div", "text", "state", "icon"])

    result = state.get("test_result", None)
    if result is None:
        return screen()

    is_success = result.get("success", False)

    bg_color = "#00ff00dd" if is_success else "#ff0000dd"
    icon_name = "check" if is_success else "close"
    label = "PASSED" if is_success else "FAILED"

    return screen(align_items="center", justify_content="flex_end")[
        div(
            padding=30,
            margin_bottom=100,
            background_color=bg_color,
            border_radius=15,
            flex_direction="row",
            align_items="center",
            gap=15
        )[
            icon(icon_name, color="white", size=48, stroke_width=3),
            text(label, font_size=48, color="white", font_weight="bold")
        ]
    ]


def test_summary_ui():
    screen, div, text, state = actions.user.ui_elements(["screen", "div", "text", "state"])

    summary = state.get("test_summary", None)
    if summary is None:
        return screen()

    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    total = summary.get("total", 0)
    all_passed = summary.get("all_passed", False)

    bg_color = "#00aa00dd" if all_passed else "#ff8800dd"

    return screen(align_items="center", justify_content="center")[
        div(
            padding=40,
            background_color=bg_color,
            border_radius=20,
            flex_direction="column",
            align_items="center",
            gap=10
        )[
            text("Test Run Complete", font_size=32, color="white", font_weight="bold"),
            text(f"{passed}/{total} Passed", font_size=24, color="white"),
            text(f"{failed} Failed", font_size=24, color="white") if failed > 0 else div()
        ]
    ]


# =========================================================================
# Entry points
# =========================================================================

def toggle_test_ui(show: bool = None):
    _test_runner_state["group_names"] = [name for name, _ in TEST_GROUPS]

    show = show if show is not None else not actions.user.ui_elements_get_trees()

    def on_mount():
        gamepad_api.connect_gamepad()
        _open_gamepad_tester()
        actions.user.ui_elements_show(test_result_ui)
        actions.user.ui_elements_show(test_status_ui)
        actions.user.ui_elements_show(test_summary_ui)

    def on_unmount():
        stop_all_tests()
        actions.user.ui_elements_hide(test_result_ui)
        actions.user.ui_elements_hide(test_status_ui)
        actions.user.ui_elements_hide(test_summary_ui)
        _close_gamepad_tester()
        gamepad_api.disconnect_gamepad()

    if show:
        actions.user.ui_elements_show(test_runner_ui, on_mount=on_mount, on_unmount=on_unmount)
    else:
        actions.user.ui_elements_hide(test_runner_ui)


def show_tests():
    toggle_test_ui(show=True)


def hide_tests():
    toggle_test_ui(show=False)
