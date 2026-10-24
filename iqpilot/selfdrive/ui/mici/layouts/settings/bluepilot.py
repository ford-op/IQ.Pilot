"""BluePilot lateral tuning on the small screen. Tap the left or right side of a value to step it."""
import pyray as rl

from iqpilot.common.params import Params, UnknownKeyName
from iqpilot.selfdrive.ui.mici.layouts.settings.iq_widgets import MappedParamToggle
from iqpilot.selfdrive.ui.mici.widgets.stock_button import LABEL_COLOR, BigButton, BigParamControl
from iqpilot.selfdrive.ui.ui_state import ui_state
from iqpilot.system.ui.lib.application import FontWeight, gui_app
from iqpilot.system.ui.lib.multilang import tr
from iqpilot.system.ui.widgets.scroller import NavScroller

from iqpilot.ui.layouts.settings.bluepilot_tuning import (
  ROWS,
  ChoiceSpec,
  FloatSpec,
  ToggleSpec,
  mode_matches,
  row_enabled,
  seed_unset_defaults,
)


def _snap(value: float, lo: float, hi: float, step: float) -> float:
  steps = round((value - lo) / step)
  snapped = lo + steps * step
  return min(hi, max(lo, round(snapped, 6)))


class _FloatStepper(BigButton):
  def __init__(self, spec: FloatSpec):
    super().__init__(tr(spec.title), "")
    self._spec = spec
    self._params = Params()
    self._sync()

  def _sync(self):
    try:
      raw = self._params.get(self._spec.key, return_default=True)
      value = float(raw)
    except (UnknownKeyName, TypeError, ValueError):
      value = self._spec.default
    self.set_value(f"{_snap(value, self._spec.lo, self._spec.hi, self._spec.step):.2f}")

  def _handle_mouse_release(self, mouse_pos):
    if not self.enabled:
      return
    third = self._rect.width / 3.0
    if mouse_pos.x < self._rect.x + third:
      delta = -self._spec.step
    elif mouse_pos.x > self._rect.x + 2.0 * third:
      delta = self._spec.step
    else:
      return
    try:
      current = float(self._params.get(self._spec.key, return_default=True))
    except (UnknownKeyName, TypeError, ValueError):
      current = self._spec.default
    nxt = _snap(current + delta, self._spec.lo, self._spec.hi, self._spec.step)
    try:
      self._params.put(self._spec.key, nxt)
    except UnknownKeyName:
      return
    self.set_value(f"{nxt:.2f}")

  def _draw_content(self, btn_x, btn_y, btn_width, btn_height):
    super()._draw_content(btn_x, btn_y, btn_width, btn_height)
    font = gui_app.font(FontWeight.BOLD)
    color = LABEL_COLOR if self.enabled else rl.Color(255, 255, 255, 80)
    mid = btn_y + btn_height / 2 - 24
    rl.draw_text_ex(font, "−", rl.Vector2(btn_x + 24, mid), 52, 0, color)
    rl.draw_text_ex(font, "+", rl.Vector2(btn_x + btn_width - 52, mid), 52, 0, color)


class BluePilotLayoutMici(NavScroller):
  def __init__(self):
    super().__init__()
    seed_unset_defaults(ui_state.params)
    self._bound = []
    for spec in ROWS:
      if isinstance(spec, ChoiceSpec):
        widget = MappedParamToggle(tr(spec.title), spec.key, [tr(choice) for choice in spec.choices], list(range(len(spec.choices))))
      elif isinstance(spec, ToggleSpec):
        widget = BigParamControl(tr(spec.title), spec.key)
      else:
        widget = _FloatStepper(spec)
      self._bound.append((spec, widget))
    self._scroller.add_widgets([widget for _, widget in self._bound])

  def _update_state(self):
    super()._update_state()
    for spec, widget in self._bound:
      widget.set_visible(mode_matches(spec, ui_state.params))
      widget.set_enabled(row_enabled(spec, ui_state.params))

  def show_event(self):
    super().show_event()
    for spec, widget in self._bound:
      if isinstance(spec, FloatSpec):
        widget._sync()
      elif hasattr(widget, "refresh"):
        widget.refresh()
