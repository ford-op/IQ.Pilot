# Copyright (c) 2026 IQ.Lvbs. All rights reserved.
"""Ford BluePilot lateral tuning on the comma 4 (the rows and their rules: ui/lib/ford_lateral_settings.py).
Only the selected primary control mode's rows show; tap the left or right third of a value to step it."""
import pyray as rl

from iqpilot.selfdrive.ui.lib import ford_lateral_settings as ford
from iqpilot.selfdrive.ui.mici.widgets.stock_button import LABEL_COLOR, BigButton, BigParamControl
from iqpilot.selfdrive.ui.ui_state import ui_state
from iqpilot.system.ui.lib.application import FontWeight, MousePos, gui_app
from iqpilot.system.ui.lib.multilang import tr
from iqpilot.system.ui.widgets.scroller import NavScroller


class FloatStepper(BigButton):
  def __init__(self, row: ford.FordRow):
    super().__init__(tr(row.title), "")
    self._row = row
    self.refresh()

  def refresh(self):
    self.set_value(f"{ford.read_float(self._row, ui_state.params):.2f}")

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if not self.enabled:
      return
    third = self._rect.width / 3.0
    if mouse_pos.x < self._rect.x + third:
      direction = -1
    elif mouse_pos.x > self._rect.x + 2.0 * third:
      direction = 1
    else:
      return
    self.set_value(f"{ford.step_float(self._row, ui_state.params, direction):.2f}")

  def _draw_content(self, btn_x: float, btn_y: float, btn_width: float, btn_height: float):
    super()._draw_content(btn_x, btn_y, btn_width, btn_height)
    font = gui_app.font(FontWeight.BOLD)
    color = LABEL_COLOR if self.enabled else rl.Color(255, 255, 255, int(255 * 0.35))
    mid = btn_y + btn_height / 2 - 24
    rl.draw_text_ex(font, "-", rl.Vector2(btn_x + 24, mid), 52, 0, color)
    rl.draw_text_ex(font, "+", rl.Vector2(btn_x + btn_width - 52, mid), 52, 0, color)


class FordLateralTuningMici(NavScroller):
  def __init__(self):
    super().__init__()
    ford.seed_unset_defaults(ui_state.params)
    self._rows = [(row, FloatStepper(row) if row.is_float else BigParamControl(tr(row.title), row.key))
                  for row in ford.TUNING_ROWS]
    self._scroller.add_widgets([widget for _, widget in self._rows])

  def _update_state(self):
    super()._update_state()
    mode = ford.primary_control(ui_state.params)
    for row, widget in self._rows:
      widget.set_visible(row.mode == mode)
      widget.set_enabled(ford.row_enabled(row, ui_state.params))

  def show_event(self):
    super().show_event()
    for _, widget in self._rows:
      widget.refresh()
