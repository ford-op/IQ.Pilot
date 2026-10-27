"""The host's own names, for the tests that touch them: its CarControl / CarParams extension structs, the
field its safety bits ride in, its adapter (hosts/), and its libsafety setters. Detected from the host's
opendbc, so the same tests run on every host (HOSTS.md, "Running the tests")."""
from ...car import structs

if hasattr(structs, "CarControlSP"):  # sunnypilot
  from ..hosts.sunnypilot.lateral import BluePilotLateral, params_from_cc_sp as params_from_cc
  from ..hosts.sunnypilot.safety_param import init_ford_safety_param_sp as init_ford_safety_param

  NAME = "sunnypilot"
  CarControlX = structs.CarControlSP
  CarParamsX = structs.CarParamsSP
  SAFETY_PARAM_FIELD = "safetyParam"
  SET_SAFETY_PARAM = "set_current_safety_param_sp"
  SET_CONTROLS_ALLOWED_LAT = "set_controls_allowed_lateral"
elif hasattr(structs, "IQCarControl"):  # IQ.Pilot
  from ..hosts.iqpilot.lateral import BluePilotLateral, params_from_cc_iq as params_from_cc
  from ..hosts.iqpilot.safety_param import init_ford_safety_param_iq as init_ford_safety_param

  NAME = "iqpilot"
  CarControlX = structs.IQCarControl
  CarParamsX = structs.IQCarParams
  SAFETY_PARAM_FIELD = "iqSafetyFlags"
  SET_SAFETY_PARAM = "set_current_safety_param_iq"
  SET_CONTROLS_ALLOWED_LAT = "set_controls_allowed_lat"
else:
  raise ImportError("unknown host: add it to tests/host.py and hosts/")

__all__ = ["BluePilotLateral", "params_from_cc", "init_ford_safety_param"]


def set_safety_param(safety, param: int) -> None:
  """libsafety: the second safety param, the one ford_bp_init reads (current_safety_param_sp / _iq)."""
  getattr(safety, SET_SAFETY_PARAM)(param)


def set_controls_allowed_lat(safety, allowed: bool) -> None:
  """libsafety: the host's lateral-only engagement (sunnypilot MADS, IQ.Pilot AOL)."""
  getattr(safety, SET_CONTROLS_ALLOWED_LAT)(allowed)
