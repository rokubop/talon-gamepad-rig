"""The controller as Windows sees it, shown while the tests run. Reads what
gamepad_rig_test records; no actions of its own.

Adapted from talonhub/community's plugin/gamepad/gamepad_tester.py (d600a04d):

MIT License. Copyright (c) 2021 Jeff Knaus, Ryan Hileman, Zach Dwiel,
Michael Arntzenius, and others. Permission is hereby granted, free of
charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject
to the following conditions: The above copyright notice and this permission
notice shall be included in all copies or substantial portions of the
Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from talon import ui
from talon.canvas import Canvas, MouseEvent
from talon.skia.canvas import Canvas as SkiaCanvas
from talon.types import Point2d, Rect

from . import gamepad_rig_test as rec

canvas: Canvas | None = None
last_mouse_pos: Point2d | None = None

BACKGROUND_COLOR = "fffafa"
BORDER_COLOR = "000000"
FONT_SIZE = 16
WIDTH = 900
HEIGHT = 800
CIRCLE_RADIUS = 100
BUTTON_OFFSET = CIRCLE_RADIUS / 2
BUTTON_RADIUS = BUTTON_OFFSET / 2
ROW_OFFSET = CIRCLE_RADIUS * 1.25
BUTTON_FLAT_WIDTH = BUTTON_RADIUS * 3
BUTTON_FLAT_HEIGHT = BUTTON_RADIUS
TRIGGER_HEIGHT = CIRCLE_RADIUS
BUTTON_OFFSETS = [(0, -1), (1, 0), (0, 1), (-1, 0)]


def _pressed(button_id: str) -> bool:
    return rec.buttons.get(button_id, False)


def render_round_button(c: SkiaCanvas, x: float, y: float, is_pressed: bool):
    c.paint.style = c.paint.Style.FILL if is_pressed else c.paint.Style.STROKE
    c.draw_circle(x, y, BUTTON_RADIUS)


def render_square_button(c: SkiaCanvas, x: float, y: float, is_pressed: bool):
    c.paint.style = c.paint.Style.FILL if is_pressed else c.paint.Style.STROKE
    c.draw_rect(Rect(x - BUTTON_RADIUS, y - BUTTON_RADIUS, BUTTON_RADIUS * 2, BUTTON_RADIUS * 2))


def render_flat_button(c: SkiaCanvas, x: float, y: float, is_pressed: bool):
    c.paint.style = c.paint.Style.FILL if is_pressed else c.paint.Style.STROKE
    c.draw_rect(Rect(x - BUTTON_FLAT_WIDTH / 2, y - BUTTON_FLAT_HEIGHT / 2,
                     BUTTON_FLAT_WIDTH, BUTTON_FLAT_HEIGHT))


def render_buttons(c: SkiaCanvas, x: float, y: float, use_circle: bool, button_ids: list[str]):
    c.paint.style = c.paint.Style.STROKE
    c.draw_circle(x, y, CIRCLE_RADIUS)
    for i, button_id in enumerate(button_ids):
        offset_x, offset_y = BUTTON_OFFSETS[i]
        button_x = x + offset_x * BUTTON_OFFSET
        button_y = y + offset_y * BUTTON_OFFSET
        if use_circle:
            render_round_button(c, button_x, button_y, _pressed(button_id))
        else:
            render_square_button(c, button_x, button_y, _pressed(button_id))


def render_trigger(c: SkiaCanvas, x: float, y: float, value: float):
    c.paint.style = c.paint.Style.STROKE
    c.draw_rect(Rect(x - BUTTON_FLAT_WIDTH / 2, y - TRIGGER_HEIGHT,
                     BUTTON_FLAT_WIDTH, TRIGGER_HEIGHT))
    c.paint.style = c.paint.Style.FILL
    height = value * TRIGGER_HEIGHT
    c.draw_rect(Rect(x - BUTTON_FLAT_WIDTH / 2, y - height, BUTTON_FLAT_WIDTH, height))
    text = str(round(value * 100))
    text_rect = c.paint.measure_text(text)[1]
    c.draw_text(text, x - text_rect.x - text_rect.width / 2,
                y - TRIGGER_HEIGHT - text_rect.height)


def render_stick(c: SkiaCanvas, x: float, y: float, is_pressed: bool,
                 value_x: float, value_y: float):
    if is_pressed:
        c.paint.style = c.paint.Style.FILL
        c.draw_circle(x, y, CIRCLE_RADIUS)
        return
    c.paint.style = c.paint.Style.STROKE
    c.draw_circle(x, y, CIRCLE_RADIUS)
    c.draw_line(x - CIRCLE_RADIUS, y, x + CIRCLE_RADIUS, y)
    c.draw_line(x, y - CIRCLE_RADIUS, x, y + CIRCLE_RADIUS)
    dot_x = x + value_x * CIRCLE_RADIUS
    dot_y = y + value_y * CIRCLE_RADIUS
    c.draw_line(x, y, dot_x, dot_y)
    c.paint.style = c.paint.Style.FILL
    c.draw_circle(dot_x, dot_y, 5)
    text = f"{round(value_x * 100)}, {round(value_y * 100)}"
    text_rect = c.paint.measure_text(text)[1]
    c.draw_text(text, x - text_rect.x - text_rect.width / 2,
                y - CIRCLE_RADIUS - text_rect.height)


def render_footer(c: SkiaCanvas, x: float, y: float):
    text = "Closes when the tests finish. Drag to move."
    text_rect = c.paint.measure_text(text)[1]
    c.draw_text(text, x - text_rect.x - text_rect.width / 2, y - 2 * text_rect.height)


def on_draw(c: SkiaCanvas):
    c.paint.textsize = FONT_SIZE
    c.paint.style = c.paint.Style.FILL
    c.paint.color = BACKGROUND_COLOR
    c.draw_rect(c.rect)

    c.paint.color = BORDER_COLOR
    y_center = c.rect.center.y + ROW_OFFSET * 0.75
    offset = CIRCLE_RADIUS * 2.5

    y = y_center - ROW_OFFSET * 2.5
    render_trigger(c, c.rect.center.x - offset, y, rec.triggers["l2"])
    render_trigger(c, c.rect.center.x + offset, y, rec.triggers["r2"])

    y = y_center - ROW_OFFSET * 2.15
    render_flat_button(c, c.rect.center.x - offset, y, _pressed("l1"))
    render_flat_button(c, c.rect.center.x + offset, y, _pressed("r1"))

    y = y_center - ROW_OFFSET
    render_buttons(c, c.rect.center.x - offset, y, False,
                   ["dpad_up", "dpad_right", "dpad_down", "dpad_left"])
    render_buttons(c, c.rect.center.x + offset, y, True, ["north", "east", "south", "west"])

    offset = CIRCLE_RADIUS * 0.75
    y = y_center - ROW_OFFSET / 3
    render_round_button(c, c.rect.center.x - offset, y, _pressed("select"))
    render_round_button(c, c.rect.center.x + offset, y, _pressed("start"))

    offset = CIRCLE_RADIUS * 1.5
    y = y_center + ROW_OFFSET
    render_stick(c, c.rect.center.x - offset, y, _pressed("l3"), *rec.sticks["left"])
    render_stick(c, c.rect.center.x + offset, y, _pressed("r3"), *rec.sticks["right"])

    render_footer(c, c.rect.center.x, c.rect.bot)


def on_mouse(e: MouseEvent):
    global last_mouse_pos
    if e.event == "mousedown" and e.button == 0:
        last_mouse_pos = e.gpos
    elif e.event == "mousemove" and last_mouse_pos:
        dx = e.gpos.x - last_mouse_pos.x
        dy = e.gpos.y - last_mouse_pos.y
        last_mouse_pos = e.gpos
        if canvas is not None:
            canvas.move(canvas.rect.x + dx, canvas.rect.y + dy)
    elif e.event == "mouseup" and e.button == 0:
        last_mouse_pos = None


def showing() -> bool:
    return canvas is not None


def show():
    global canvas
    if canvas is not None:
        return
    screen = ui.main_screen()
    x, y = screen.rect.center.x, screen.rect.center.y
    canvas = Canvas.from_rect(Rect(x - WIDTH / 2, y - HEIGHT / 2, WIDTH, HEIGHT))
    canvas.draggable = True
    canvas.blocks_mouse = True
    canvas.register("draw", on_draw)
    canvas.register("mouse", on_mouse)


def hide():
    global canvas
    if canvas is not None:
        canvas.unregister("draw", on_draw)
        canvas.unregister("mouse", on_mouse)
        canvas.close()
        canvas = None
