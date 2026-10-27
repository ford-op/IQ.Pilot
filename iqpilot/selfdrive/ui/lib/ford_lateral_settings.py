# Copyright (c) 2026 IQ.Lvbs. All rights reserved.
"""Ford BluePilot lateral settings (iqdbc/bluepilot_lateral), shared by the big Vehicle panel and the comma 4 page.

Ranges and defaults come from the library's params/manifest.py; titles, steps and which rows depend on which
live here. The tuning rows apply while driving (the library reads them every frame); the lateral switch and
the pinion sensor apply the next time the car starts."""
from dataclasses import dataclass

from iqdbc.bluepilot_lateral.core.values_ext import FORD_PINION_GEOMETRY_INDEX
from iqdbc.bluepilot_lateral.params.manifest import SETTINGS as BP_LATERAL_SETTINGS
from iqpilot.common.params import UnknownKeyName
from iqpilot.system.ui.lib.multilang import tr_noop

CURVATURE, ANGLE = 0, 1  # FordPrefLateralControl
SETTINGS = {s.key: s for s in BP_LATERAL_SETTINGS}


@dataclass(frozen=True)
class FordRow:
  key: str
  title: str
  description: str
  mode: int  # shown only in this primary control mode
  needs: tuple[str, ...] = ()  # toggles that must be on for the row to be editable
  step: float = 0.05

  @property
  def is_float(self) -> bool:
    return SETTINGS[self.key].type is float

  @property
  def range(self) -> tuple[float, float]:
    return SETTINGS[self.key].range

  @property
  def default(self):
    return SETTINGS[self.key].default


TUNING_ROWS = (
  FordRow("enable_human_turn_detection_curv", tr_noop("Human Turn Detection"),
          tr_noop("Ease off while the driver is steering through a turn."), CURVATURE),
  FordRow("lane_change_factor_high_curv", tr_noop("Lane Change Factor"),
          tr_noop("Scales steering during a lane change. Values under 1.0 reduce it."), CURVATURE),
  FordRow("enable_lane_positioning_curv", tr_noop("Lane Positioning"),
          tr_noop("Nudge toward the lane center, with an optional in-lane offset."), CURVATURE),
  FordRow("custom_path_offset_curv", tr_noop("In-Lane Offset"),
          tr_noop("Meters of bias inside the lane. Negative is left."), CURVATURE, ("enable_lane_positioning_curv",)),
  FordRow("enable_lane_full_mode_curv", tr_noop("Lanefull Mode"),
          tr_noop("Center between the lane lines when they are confident, instead of following the model's path."),
          CURVATURE, ("enable_lane_positioning_curv",)),
  FordRow("LC_PID_gain_UI_curv", tr_noop("Centering Gain"),
          tr_noop("Gain for the lane centering controller."), CURVATURE, ("enable_lane_positioning_curv",), step=0.5),
  FordRow("custom_profile_curv", tr_noop("Custom Tuning Profile"),
          tr_noop("Use the predicted curvature blend ratios below instead of the built-in profile."), CURVATURE),
  FordRow("pc_blend_ratio_low_C_UI_curv", tr_noop("Predicted Blend, Low Curve"),
          tr_noop("How much predicted curvature is mixed in on gentle curves. 0 follows the plan, 1 follows the prediction."),
          CURVATURE, ("custom_profile_curv",)),
  FordRow("pc_blend_ratio_high_C_UI_curv", tr_noop("Predicted Blend, High Curve"),
          tr_noop("How much predicted curvature is mixed in on sharp curves. 0 follows the plan, 1 follows the prediction."),
          CURVATURE, ("custom_profile_curv",)),
  FordRow("FordLowSpeedFactor_ang", tr_noop("Low Speed Factor"),
          tr_noop("Scales low-speed steering. 1.0 is the default feel."), ANGLE, step=0.01),
  FordRow("FordHighSpeedFactor_ang", tr_noop("High Speed Factor"),
          tr_noop("Scales high-speed steering. 1.0 is the default feel."), ANGLE, step=0.01),
  FordRow("FordHighSpeedDampening_ang", tr_noop("High Speed Straight Factor"),
          tr_noop("Straight-road response at high speed. Lower it if the car oversteers, raise it if it understeers."),
          ANGLE, step=0.01),
  FordRow("lane_change_factor_high_ang", tr_noop("Lane Change Factor"),
          tr_noop("Scales steering during a lane change. Values over 1.0 boost it."), ANGLE),
  FordRow("enable_lane_positioning_ang", tr_noop("Lane Positioning"),
          tr_noop("Nudge toward the lane center, with an optional in-lane offset."), ANGLE),
  FordRow("custom_path_offset_ang", tr_noop("In-Lane Offset"),
          tr_noop("Meters of bias inside the lane. Negative is left."), ANGLE, ("enable_lane_positioning_ang",), step=0.01),
  FordRow("lane_centering_strength_ang", tr_noop("Lane Centering Strength"),
          tr_noop("How hard the lane-center trim pulls against the model's own path."), ANGLE, ("enable_lane_positioning_ang",)),
)


def seed_unset_defaults(params) -> None:
  # toggles read get_bool, which ignores the params_keys.h default: an unset default-on key would show off
  for setting in BP_LATERAL_SETTINGS:
    try:
      if setting.type is bool and setting.default and params.get(setting.key) is None:
        params.put_bool(setting.key, True)
    except UnknownKeyName:
      pass


def platform(params, cp) -> str:
  if bundle := params.get("CarPlatformBundle"):
    return bundle.get("platform", "")
  return cp.carFingerprint if cp else ""


def pinion_supported(params, cp) -> bool:
  return platform(params, cp) in FORD_PINION_GEOMETRY_INDEX


def bp_lateral_on(params) -> bool:
  return not params.get_bool("disable_BP_lat_UI")


def primary_control(params) -> int:
  try:
    return int(params.get("FordPrefLateralControl", return_default=True) or 0)
  except (TypeError, ValueError, UnknownKeyName):
    return CURVATURE


def row_enabled(row: FordRow, params) -> bool:
  return bp_lateral_on(params) and all(params.get_bool(key) for key in row.needs)


def read_float(row: FordRow, params) -> float:
  try:
    value = params.get(row.key, return_default=True)
    return float(row.default if value is None else value)
  except (TypeError, ValueError, UnknownKeyName):
    return float(row.default)


def step_float(row: FordRow, params, direction: int) -> float:
  """One step up (direction 1) or down (-1), snapped to the row's step and clamped to its range; written."""
  lo, hi = row.range
  steps = round((read_float(row, params) - lo) / row.step) + direction
  value = min(hi, max(lo, round(lo + steps * row.step, 6)))
  params.put(row.key, value)
  return value
