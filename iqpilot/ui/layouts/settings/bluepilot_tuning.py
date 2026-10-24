"""BluePilot Ford lateral tuning. Shared by the big settings panel and the small-screen list.

Ranges match bp-dev's lateral menu. Defaults match the values registered in params_keys.h.
"""
from dataclasses import dataclass

from iqpilot.common.params import UnknownKeyName
from iqpilot.system.ui.lib.multilang import tr_noop


@dataclass(frozen=True)
class ToggleSpec:
  key: str
  title: str
  description: str
  group: str  # shared, curv, angle
  needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChoiceSpec:
  key: str
  title: str
  description: str
  choices: tuple[str, ...]
  group: str = "shared"
  needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class FloatSpec:
  key: str
  title: str
  description: str
  lo: float
  hi: float
  step: float
  default: float
  group: str
  needs: tuple[str, ...] = ()


# needs: lane_curv / lane_ang / profile. A row is editable only when its group matches the
# selected actuator and every listed dependency is on.
ROWS: tuple[ToggleSpec | ChoiceSpec | FloatSpec, ...] = (
  ToggleSpec(
    "disable_BP_lat_UI",
    tr_noop("Disable BluePilot Lateral"),
    tr_noop("Send the stock curvature-only command. Leave this off to use BluePilot's four path signals."),
    "shared",
  ),
  ChoiceSpec(
    "FordPrefLateralControl",
    tr_noop("Primary Control"),
    tr_noop("Curvature sends offset, angle, curvature, and curvature rate. Angle uses path angle as the actuator."),
    (tr_noop("Curvature"), tr_noop("Angle")),
  ),
  ToggleSpec(
    "FordPrefSteerAngleCurvature",
    tr_noop("Use Pinion Yaw Sensor"),
    tr_noop("Measure the turn from the steering pinion instead of the yaw sensor. Applies the next time the car starts."),
    "shared",
  ),
  ToggleSpec(
    "enable_human_turn_detection_curv",
    tr_noop("Human Turn Detection"),
    tr_noop("Ease off while the driver is steering through a turn."),
    "curv",
  ),
  FloatSpec(
    "lane_change_factor_high_curv",
    tr_noop("Lane Change Factor"),
    tr_noop("Scales steering during a lane change. Values under 1.0 reduce it."),
    0.5, 1.0, 0.05, 0.85, "curv",
  ),
  ToggleSpec(
    "enable_lane_positioning_curv",
    tr_noop("Lane Positioning"),
    tr_noop("Nudge toward the lane center, with an optional in-lane offset."),
    "curv",
  ),
  FloatSpec(
    "custom_path_offset_curv",
    tr_noop("In-Lane Offset"),
    tr_noop("Meters of bias inside the lane. Negative is left."),
    -0.5, 0.5, 0.05, 0.0, "curv", ("lane_curv",),
  ),
  ToggleSpec(
    "enable_lane_full_mode_curv",
    tr_noop("Lanefull Mode"),
    tr_noop("Use the full lane-positioning path instead of the lighter trim."),
    "curv", ("lane_curv",),
  ),
  ToggleSpec(
    "custom_profile_curv",
    tr_noop("Custom Tuning Profile"),
    tr_noop("Use the blend ratios and centering gain below instead of the built-in profile."),
    "curv",
  ),
  FloatSpec(
    "pc_blend_ratio_low_C_UI_curv",
    tr_noop("Predicted Blend, Low Curve"),
    tr_noop("How much predicted curvature is mixed in on gentle curves. 0 follows the plan, 1 follows the prediction."),
    0.0, 1.0, 0.05, 0.4, "curv", ("profile",),
  ),
  FloatSpec(
    "pc_blend_ratio_high_C_UI_curv",
    tr_noop("Predicted Blend, High Curve"),
    tr_noop("How much predicted curvature is mixed in on sharp curves. 0 follows the plan, 1 follows the prediction."),
    0.0, 1.0, 0.05, 0.4, "curv", ("profile",),
  ),
  FloatSpec(
    "LC_PID_gain_UI_curv",
    tr_noop("Centering Gain"),
    tr_noop("Gain for the curvature centering controller. Used with lane positioning and the custom profile."),
    0.0, 50.0, 0.5, 3.0, "curv", ("lane_curv", "profile"),
  ),
  FloatSpec(
    "FordLowSpeedFactor_ang",
    tr_noop("Low Speed Factor"),
    tr_noop("Scales low-speed steering in angle mode. 1.0 is the default feel."),
    0.5, 1.5, 0.01, 1.0, "angle",
  ),
  FloatSpec(
    "FordHighSpeedFactor_ang",
    tr_noop("High Speed Factor"),
    tr_noop("Scales high-speed steering in angle mode. 1.0 is the default feel."),
    0.5, 1.5, 0.01, 1.0, "angle",
  ),
  FloatSpec(
    "FordHighSpeedDampening_ang",
    tr_noop("High Speed Straight Factor"),
    tr_noop("Straight-road response at high speed. Lower it if the car wanders, raise it if it feels lazy."),
    0.25, 1.25, 0.01, 1.0, "angle",
  ),
  FloatSpec(
    "lane_change_factor_high_ang",
    tr_noop("Lane Change Factor"),
    tr_noop("Scales steering during a lane change. Values over 1.0 boost it."),
    0.85, 1.5, 0.05, 1.0, "angle",
  ),
  ToggleSpec(
    "enable_lane_positioning_ang",
    tr_noop("Lane Positioning"),
    tr_noop("Nudge toward the lane center while angle control is active."),
    "angle",
  ),
  FloatSpec(
    "custom_path_offset_ang",
    tr_noop("In-Lane Offset"),
    tr_noop("Meters of bias inside the lane. Negative is left."),
    -0.5, 0.5, 0.01, 0.0, "angle", ("lane_ang",),
  ),
  FloatSpec(
    "lane_centering_strength_ang",
    tr_noop("Lane Centering Strength"),
    tr_noop("How hard the lane-center trim pulls against the model's own path."),
    0.0, 1.0, 0.05, 0.25, "angle", ("lane_ang",),
  ),
)

SECTIONS = (
  ("curv", tr_noop("Curvature")),
  ("angle", tr_noop("Angle")),
)


def is_angle(params) -> bool:
  try:
    return int(params.get("FordPrefLateralControl", return_default=True) or 0) == 1
  except (TypeError, ValueError):
    return False


def _flag(params, key: str) -> bool:
  try:
    return bool(params.get_bool(key))
  except Exception:
    return False


def mode_matches(spec, params) -> bool:
  angle = is_angle(params)
  if spec.group == "angle":
    return angle
  if spec.group == "curv":
    return not angle
  return True


def row_enabled(spec, params) -> bool:
  if not mode_matches(spec, params):
    return False
  if "lane_curv" in spec.needs and not _flag(params, "enable_lane_positioning_curv"):
    return False
  if "lane_ang" in spec.needs and not _flag(params, "enable_lane_positioning_ang"):
    return False
  if "profile" in spec.needs and not _flag(params, "custom_profile_curv"):
    return False
  return True


def seed_unset_defaults(params) -> None:
  # get_bool ignores the registered default, so an unset key would show this toggle off
  # while the controller still treats it as on.
  try:
    missing = params.get("enable_human_turn_detection_curv") is None
  except UnknownKeyName:
    return
  if missing:
    try:
      params.put_bool("enable_human_turn_detection_curv", True)
    except UnknownKeyName:
      return
