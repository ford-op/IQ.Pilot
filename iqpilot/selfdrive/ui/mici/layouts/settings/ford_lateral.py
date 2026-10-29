# Copyright (c) 2026 IQ.Lvbs. All rights reserved.
"""Ford BluePilot lateral tuning on the comma 4 (the rows and their rules: ui/lib/ford_lateral_settings.py).
Only the selected primary control mode's rows show; tap a value to pick a new one from its list."""
from iqpilot.selfdrive.ui.lib import ford_lateral_settings as ford
from iqpilot.selfdrive.ui.mici.widgets.dialog import BigMultiOptionDialog
from iqpilot.selfdrive.ui.mici.widgets.stock_button import BigButton, BigParamControl, BigToggle
from iqpilot.selfdrive.ui.ui_state import ui_state
from iqpilot.system.ui.lib.application import gui_app
from iqpilot.system.ui.lib.multilang import tr
from iqpilot.system.ui.widgets.scroller import NavScroller


class _ValuePicker(BigMultiOptionDialog):
  """Opens on the current value. The stock dialog scrolls to its default in show_event, before its rows have
  positions, so it opens on the first value, and the selection is whichever row is centered: confirming
  straight away would save the range's minimum. Scroll once the first frame has laid the rows out."""
  def show_event(self):
    super().show_event()
    self._scroll_to_default = self._default_option is not None

  def _render(self, rect):
    super()._render(rect)
    if self._scroll_to_default:
      self._scroll_to_default = False
      self._on_option_selected(self._default_option)


class FloatSetting(BigButton):
  def __init__(self, row: ford.FordRow):
    super().__init__(tr(row.title), "")
    self._row = row
    self.set_click_callback(self._pick)
    self.refresh()

  def _current(self) -> str:
    return ford.format_value(ford.snap(self._row, ford.read_float(self._row, ui_state.params)))

  def refresh(self):
    self.set_value(self._current())

  def _pick(self):
    options = [ford.format_value(value) for value in ford.choices(self._row)]
    dialog = _ValuePicker(options, self._current(), right_btn="check",
                          right_btn_callback=lambda: self._apply(dialog.get_selected_option()))
    gui_app.push_widget(dialog)

  def _apply(self, option: str):
    ui_state.params.put(self._row.key, float(option))
    self.refresh()


class BluePilotLateralToggle(BigToggle):
  """On / off for BluePilot lateral. Stored inverted, as disable_BP_lat_UI, and read through its params_keys.h
  default (off), which BigParamControl's get_bool would miss."""
  def __init__(self):
    super().__init__(tr("BluePilot lateral"), initial_state=ford.bp_lateral_on(ui_state.params),
                     toggle_callback=lambda on: ford.set_bp_lateral(ui_state.params, on))

  def refresh(self):
    self.set_checked(ford.bp_lateral_on(ui_state.params))


class FordTuningButton(BigButton):
  """The Vehicle page's entry to the tuning page. It refreshes like the brand controls next to it."""
  def __init__(self):
    super().__init__(tr("lateral tuning"))
    self.set_click_callback(lambda: gui_app.push_widget(FordLateralTuningMici()))

  def refresh(self):
    pass


class FordLateralTuningMici(NavScroller):
  def __init__(self):
    super().__init__()
    ford.seed_unset_defaults(ui_state.params)
    self._rows = [(row, FloatSetting(row) if row.is_float else BigParamControl(tr(row.title), row.key))
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
