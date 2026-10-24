"""BluePilot lateral tuning on the main settings screen."""
from iqpilot.system.ui.iqwidgets.widgets.list_view import (
  IQListItem,
  multiple_button_item,
  option_item,
  toggle_item,
)
from iqpilot.system.ui.lib.multilang import tr
from iqpilot.system.ui.widgets import Widget
from iqpilot.system.ui.widgets.scroller_tici import Scroller
from iqpilot.selfdrive.ui.ui_state import ui_state

from iqpilot.ui.layouts.settings.bluepilot_tuning import (
  ROWS,
  SECTIONS,
  ChoiceSpec,
  FloatSpec,
  ToggleSpec,
  row_enabled,
  seed_unset_defaults,
)


def _title(text: str):
  return lambda text=text: tr(text)


def _float_item(spec: FloatSpec):
  scale = 100.0
  return option_item(
    title=_title(spec.title),
    description=_title(spec.description),
    param=spec.key,
    min_value=int(round(spec.lo * scale)),
    max_value=int(round(spec.hi * scale)),
    value_change_step=max(1, int(round(spec.step * scale))),
    use_float_scaling=True,
    enabled=lambda spec=spec: row_enabled(spec, ui_state.params),
    inline=False,
  )


def _row(spec):
  enabled = lambda spec=spec: row_enabled(spec, ui_state.params)
  if isinstance(spec, ToggleSpec):
    return toggle_item(
      title=_title(spec.title),
      description=_title(spec.description),
      param=spec.key,
      enabled=enabled,
    )
  if isinstance(spec, ChoiceSpec):
    return multiple_button_item(
      title=_title(spec.title),
      description=_title(spec.description),
      buttons=[_title(choice) for choice in spec.choices],
      param=spec.key,
      inline=False,
    )
  return _float_item(spec)


class BluePilotLayout(Widget):
  def __init__(self):
    super().__init__()
    seed_unset_defaults(ui_state.params)
    items = []
    pending = {name: [] for name, _ in SECTIONS}
    for spec in ROWS:
      row = _row(spec)
      if spec.group in pending:
        pending[spec.group].append(row)
      else:
        items.append(row)
    for name, title in SECTIONS:
      items.append(IQListItem(title=_title(title)))
      items.extend(pending[name])
    self._scroller = Scroller(items, line_separator=True, spacing=0)

  def _render(self, rect):
    self._scroller.render(rect)

  def show_event(self):
    self._scroller.show_event()
