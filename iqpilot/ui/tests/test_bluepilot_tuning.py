import re
from pathlib import Path

from iqpilot.ui.layouts.settings.bluepilot_tuning import (
  ROWS,
  ChoiceSpec,
  FloatSpec,
  ToggleSpec,
  is_angle,
  mode_matches,
  row_enabled,
  seed_unset_defaults,
)

_KEYS = Path(__file__).resolve().parents[2] / "common" / "params_keys.h"


class _Store:
  def __init__(self, **values):
    self.values = dict(values)

  def get(self, key, return_default=False):
    if key in self.values:
      return self.values[key]
    return 0 if return_default else None

  def get_bool(self, key):
    return bool(self.values.get(key, False))


def test_every_tuning_key_is_registered():
  text = _KEYS.read_text()
  for spec in ROWS:
    assert f'"{spec.key}"' in text


def test_float_defaults_match_registered_values_and_land_on_a_step():
  text = _KEYS.read_text()
  for spec in ROWS:
    if not isinstance(spec, FloatSpec):
      continue
    match = re.search(rf'\{{"{spec.key}", \{{PERSISTENT, FLOAT, "([^"]+)"\}}\}}', text)
    assert match, spec.key
    assert abs(float(match.group(1)) - spec.default) < 1e-6
    assert spec.lo <= spec.default <= spec.hi
    steps = round((spec.default - spec.lo) / spec.step)
    assert abs(spec.lo + steps * spec.step - spec.default) < 1e-6


def test_mode_and_dependencies_gate_the_rows():
  curv = _Store(FordPrefLateralControl=0)
  angle = _Store(FordPrefLateralControl=1, enable_lane_positioning_ang=True)
  assert not is_angle(curv)
  assert is_angle(angle)

  by_key = {spec.key: spec for spec in ROWS}
  assert mode_matches(by_key["FordLowSpeedFactor_ang"], angle)
  assert not mode_matches(by_key["FordLowSpeedFactor_ang"], curv)
  assert row_enabled(by_key["custom_path_offset_ang"], angle)
  assert not row_enabled(by_key["custom_path_offset_curv"], angle)

  bare = _Store(FordPrefLateralControl=0)
  armed = _Store(FordPrefLateralControl=0, enable_lane_positioning_curv=True, custom_profile_curv=True)
  assert not row_enabled(by_key["LC_PID_gain_UI_curv"], bare)
  assert row_enabled(by_key["LC_PID_gain_UI_curv"], armed)
  assert row_enabled(by_key["disable_BP_lat_UI"], angle)
  assert isinstance(by_key["FordPrefLateralControl"], ChoiceSpec)
  assert isinstance(by_key["enable_lane_full_mode_curv"], ToggleSpec)


class _MemoryParams:
  def __init__(self):
    self.files = {}

  def get(self, key, return_default=False):
    return self.files.get(key)

  def get_bool(self, key):
    return self.files.get(key) == "1"

  def put_bool(self, key, value):
    self.files[key] = "1" if value else "0"


def test_unset_human_turn_detection_is_seeded_on():
  params = _MemoryParams()
  assert params.get("enable_human_turn_detection_curv") is None
  seed_unset_defaults(params)
  assert params.get_bool("enable_human_turn_detection_curv")
  params.put_bool("enable_human_turn_detection_curv", False)
  seed_unset_defaults(params)
  assert not params.get_bool("enable_human_turn_detection_curv")
