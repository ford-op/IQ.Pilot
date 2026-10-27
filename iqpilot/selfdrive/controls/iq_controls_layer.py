"""
Copyright © IQ.Lvbs, apart of Project Teal Lvbs, All Rights Reserved, licensed under https://konn3kt.com/tos
"""
import time

import iqpilot.cereal.messaging as messaging
from iqpilot.cereal import log, custom

from iqdbc.car import structs
from iqdbc.bluepilot_lateral.core.values_ext import BP_LATERAL_PARAMS
from iqpilot.common.constants import CV
from iqpilot.common.params import Params
from iqpilot.common.swaglog import cloudlog
from iqpilot.selfdrive.car.enhanced_stock_longitudinal_control import build_iq_control_params_from_plan
from iqpilot.selfdrive.iqmodeld.models.inference_state import InferenceStateBase
from iqpilot.selfdrive.controls.lib.helpers.blinker_pause import IQSignalPauseController
from iqpilot.selfdrive.controls.lib.iq_dynamic.radar_manager import RadarManager

_PARAM_REFRESH_S = 3.0
_LEAD_FIELDS = ("dRel", "yRel", "vRel", "aRel", "vLead", "dPath", "vLat", "vLeadK",
                "aLeadK", "fcw", "status", "aLeadTau", "modelProb", "radar", "radarTrackId")


class IQControlsLayer(InferenceStateBase):
  def __init__(self, CP: structs.CarParams, params: Params):
    InferenceStateBase.__init__(self)
    self.CP = CP
    self.params = params
    self.blinker_pause_lateral = IQSignalPauseController()

    cloudlog.info("IQ controls layer waiting for IQCarParams")
    self.CP_IQ = messaging.log_from_bytes(params.get("IQCarParams", block=True), custom.IQCarParams)
    cloudlog.info("IQ controls layer got IQCarParams")

    self.iq_sub_services = ['radarState', 'iqState', 'iqPlan', 'iqNavState']
    self.iq_pub_services = ['iqCarControl']
    self.radar_manager = RadarManager(CP, params)

    self._next_param_refresh = 0.0
    self._needs_iq_lead_data = CP.brand == "hyundai"
    self._maneuver_mode = params.get_bool("LateralManeuverMode")
    self._sync_set_speed = self._want_set_speed_to_limit()
    self._slc_limit_kph = None
    self._slc_limit_pending_kph = None

    # BluePilot: the Ford lateral reads its inputs and settings from IQCarControl (bluepilot_lateral HOSTS.md)
    self._bp_lateral_inputs = self.CP_IQ.lateralInputsRequired
    self._bp_lateral_params: list[dict] = []
    self._bp_unknown_keys_logged: set[str] = set()

  def _want_set_speed_to_limit(self) -> bool:
    try:
      return self.params.get_bool("SLCSetSpeedToLimit")
    except Exception:
      return False

  def refresh_iq_params(self, sm: messaging.SubMaster) -> None:
    now = time.monotonic()
    if now - self._next_param_refresh <= _PARAM_REFRESH_S:
      return
    self.blinker_pause_lateral.get_params()
    if self.CP.lateralTuning.which() == 'torque':
      self.lat_delay = sm["lateralDelay"].lateralDelay
    self._sync_set_speed = self._want_set_speed_to_limit()
    self.radar_manager.read_params()
    if self._bp_lateral_inputs:
      self._bp_lateral_params = self._read_bp_lateral_params()
    self._next_param_refresh = now

  def _read_bp_lateral_params(self) -> list[dict]:
    """BluePilot: every per-frame lateral setting as an IQCarControl.params entry, the value as bytes (bools
    "1"/"0", numbers as text). An unset key gets the registry default from params_keys.h."""
    entries = []
    for key in BP_LATERAL_PARAMS:
      try:
        value = self.params.get(key, return_default=True)
      except Exception:
        if key not in self._bp_unknown_keys_logged:
          cloudlog.warning(f"BluePilot lateral param {key} not registered in params_keys.h; skipping")
          self._bp_unknown_keys_logged.add(key)
        continue
      if value is None:
        continue
      encoded = (b"1" if value else b"0") if isinstance(value, bool) else str(value).encode()
      entries.append({"key": key, "value": encoded})
    return entries

  @staticmethod
  def _fill_lateral_inputs(li, sm: messaging.SubMaster) -> None:
    """BluePilot: this frame's model and vehicle-parameter inputs for the Ford lateral."""
    md = sm['modelV2']
    lp = sm['vehicleParameters']
    li.valid = bool(sm.seen['modelV2'] and sm.seen['vehicleParameters'] and
                    len(md.laneLines) >= 3 and len(md.laneLineProbs) >= 3 and len(md.laneLineStds) >= 3)
    if not li.valid:
      return
    li.pathYawRate = list(md.orientationRate.z)
    li.pathX = list(md.position.x)
    li.pathY = list(md.position.y)
    li.laneLineLeftX = list(md.laneLines[1].x)
    li.laneLineLeftY = list(md.laneLines[1].y)
    li.laneLineRightX = list(md.laneLines[2].x)
    li.laneLineRightY = list(md.laneLines[2].y)
    li.laneLineProbs = list(md.laneLineProbs)
    li.laneLineStds = list(md.laneLineStds)
    li.laneChangeState = int(md.meta.laneChangeState.raw)
    li.laneChangeDirection = int(md.meta.laneChangeDirection.raw)
    li.steerRatio = lp.steerRatio
    li.stiffnessFactor = lp.stiffnessFactor
    li.roll = lp.roll
    li.angleOffsetDeg = lp.angleOffsetDeg
    li.lateralDelay = sm['lateralDelay'].lateralDelay

  def iq_lateral_allowed(self, sm: messaging.SubMaster) -> bool:
    if self.blinker_pause_lateral.update(sm['carState']):
      return False

    aol = sm['iqState'].aol
    stock_active = bool(sm['selfdriveState'].active)
    if self._maneuver_mode:
      return stock_active or bool(aol.available and aol.active)
    if aol.available:
      return bool(aol.active)
    return stock_active

  @staticmethod
  def _lead_snapshot(ld: log.RadarState.LeadData) -> dict:
    return {field: getattr(ld, field) for field in _LEAD_FIELDS}

  def _compose_iq_carcontrol(self, sm: messaging.SubMaster) -> custom.IQCarControl:
    CC_IQ = custom.IQCarControl.new_message()
    lp = sm['vehicleParameters']
    CC_IQ.angleOffsetDeg = float(getattr(lp, 'angleOffsetDeg', 0.0))
    CC_IQ.aol = sm['iqState'].aol

    if self._needs_iq_lead_data:
      CC_IQ.leadOne = self._lead_snapshot(sm['radarState'].leadOne)
      CC_IQ.leadTwo = self._lead_snapshot(sm['radarState'].leadTwo)

    if self.CP.openpilotLongitudinalControl:
      cruise = getattr(sm['carState'], 'cruiseState', None)
      set_speed_ms = float(max(getattr(cruise, 'speedCluster', 0.0), getattr(cruise, 'speed', 0.0), 0.0))
      set_speed_kph = set_speed_ms * CV.MS_TO_KPH
      if self._sync_set_speed:
        slc_params, self._slc_limit_kph, self._slc_limit_pending_kph = build_iq_control_params_from_plan(
          self.CP, sm['iqPlan'], bool(sm['selfdriveState'].enabled), set_speed_kph,
          self._slc_limit_kph, self._slc_limit_pending_kph)
        CC_IQ.params = slc_params
      else:
        self._slc_limit_kph = self._slc_limit_pending_kph = None
      self.radar_manager.update(CC_IQ, sm, set_speed_kph)

    if self._bp_lateral_inputs:  # BluePilot
      self._fill_lateral_inputs(CC_IQ.lateralInputs, sm)
      if self._bp_lateral_params:
        CC_IQ.params = [{"key": p.key, "type": str(p.type), "value": bytes(p.value)} for p in CC_IQ.params] + self._bp_lateral_params
    return CC_IQ

  @staticmethod
  def _emit(CC_IQ: custom.IQCarControl, sm: messaging.SubMaster, pm: messaging.PubMaster) -> None:
    envelope = messaging.new_message('iqCarControl')
    envelope.valid = sm['carState'].canValid
    envelope.iqCarControl = CC_IQ
    pm.send('iqCarControl', envelope)

  def publish_iq_state(self, sm: messaging.SubMaster, pm: messaging.PubMaster) -> None:
    fresh = sm.updated['iqState'] or sm.updated['iqPlan'] or (self._needs_iq_lead_data and sm.updated['radarState'])
    if not fresh:
      return
    self._emit(self._compose_iq_carcontrol(sm), sm, pm)
