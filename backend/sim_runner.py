"""
Simulink Simulation Service.
Executes authoritative power system simulations on main_model.slx and extracts ScopeData telemetry.
"""

import asyncio
import logging
import math
import time
from typing import Dict, Any, Tuple
import numpy as np

from backend.config import (
    MODEL_NAME,
    BLOCK_FAULT,
    BLOCK_SERIES_RLC,
    BLOCK_TRANSFORMER,
    BLOCK_SYNCHRONOUS_MACHINE,
    BLOCK_LOAD,
    BLOCK_PI_LINE,
    BLOCK_GEN_PM,
    BLOCK_GEN_VF,
    TOTAL_EXPECTED_SAMPLES,
)
from backend.models import SimulationParams, FaultType
from backend.matlab_engine import MatlabSessionManager

logger = logging.getLogger("smart_grid.simulation")

# Fault block parameter mapping verified against spsThreePhaseFaultLib for all 12 configurations
FAULT_MAPPING = {
    FaultType.NORMAL: {
        "FaultA": "off", "FaultB": "off", "FaultC": "off", "GroundFault": "off",
    },
    FaultType.AG: {
        "FaultA": "on",  "FaultB": "off", "FaultC": "off", "GroundFault": "on",
    },
    FaultType.BG: {
        "FaultA": "off", "FaultB": "on",  "FaultC": "off", "GroundFault": "on",
    },
    FaultType.CG: {
        "FaultA": "off", "FaultB": "off", "FaultC": "on",  "GroundFault": "on",
    },
    FaultType.AB: {
        "FaultA": "on",  "FaultB": "on",  "FaultC": "off", "GroundFault": "off",
    },
    FaultType.BC: {
        "FaultA": "off", "FaultB": "on",  "FaultC": "on",  "GroundFault": "off",
    },
    FaultType.CA: {
        "FaultA": "on",  "FaultB": "off", "FaultC": "on",  "GroundFault": "off",
    },
    FaultType.ABG: {
        "FaultA": "on",  "FaultB": "on",  "FaultC": "off", "GroundFault": "on",
    },
    FaultType.BCG: {
        "FaultA": "off", "FaultB": "on",  "FaultC": "on",  "GroundFault": "on",
    },
    FaultType.CAG: {
        "FaultA": "on",  "FaultB": "off", "FaultC": "on",  "GroundFault": "on",
    },
    FaultType.ABC: {
        "FaultA": "on",  "FaultB": "on",  "FaultC": "on",  "GroundFault": "off",
    },
    FaultType.ABCG: {
        "FaultA": "on",  "FaultB": "on",  "FaultC": "on",  "GroundFault": "on",
    },
}

# Nominal baseline defaults for pristine model restoration
DEFAULTS = {
    "fault_type": FaultType.ABCG,
    "fault_resistance": "0.001",
    "ground_resistance": "0.01",
    "switch_times": "[0.2 0.4]",
    "gen_nominal": "[10e6 11000 50]",
    "gen_pm": "1",
    "gen_vf": "1",
    "trafo_nominal_power": "[ 5e6 , 50 ]",
    "trafo_winding1": "[ 11000 , 0.002 , 0.08 ]",
    "trafo_winding2": "[ 415 , 0.002 , 0.08 ]",
    "load_active": "500e6",
    "load_inductive": "0",
    "load_capacitive": "0",
    "series_r": "0.001",
    "series_l": "1e-3",
    "series_c": "1e-6",
    "pi_length": "100",
}


class SimulationRunner:
    """Executes Simulink model runs with parameter configuration and ScopeData extraction."""

    def __init__(self, session_manager: MatlabSessionManager):
        self.session_manager = session_manager

    async def run_simulation(self, params: SimulationParams) -> Dict[str, Any]:
        """
        Asynchronously runs a single simulation with concurrency lock protection.
        Returns a dictionary containing time vector, raw signals array, and metadata.
        """
        async with self.session_manager.lock:
            eng = self.session_manager.engine
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self._run_simulation_sync, eng, params)
            return result

    def _run_simulation_sync(self, eng: Any, params: SimulationParams) -> Dict[str, Any]:
        """Synchronous simulation execution pipeline executed within threadpool."""
        t0 = time.time()
        logger.info(f"Applying parameters for fault scenario: {params.fault_type.value}...")

        applied_params: Dict[str, Any] = {}
        readback_params: Dict[str, Any] = {}

        # 1. Apply Fault Configuration
        fault_flags = FAULT_MAPPING.get(params.fault_type, FAULT_MAPPING[FaultType.ABC])
        for param_name, param_value in fault_flags.items():
            eng.set_param(BLOCK_FAULT, param_name, param_value, nargout=0)
            applied_params[f"fault_{param_name}"] = param_value
            readback_params[f"fault_{param_name}"] = eng.get_param(BLOCK_FAULT, param_name)

        # 2. Apply Fault & Ground Resistances and Timing
        rf_str = str(params.fault_resistance)
        rg_str = str(params.ground_resistance)
        trans_str = f"[{params.fault_start_time} {params.fault_stop_time}]"

        eng.set_param(BLOCK_FAULT, "FaultResistance", rf_str, nargout=0)
        eng.set_param(BLOCK_FAULT, "GroundResistance", rg_str, nargout=0)
        eng.set_param(BLOCK_FAULT, "SwitchTimes", trans_str, nargout=0)

        applied_params["fault_resistance"] = params.fault_resistance
        applied_params["ground_resistance"] = params.ground_resistance
        applied_params["fault_switch_times"] = [params.fault_start_time, params.fault_stop_time]

        readback_params["fault_resistance"] = float(eng.get_param(BLOCK_FAULT, "FaultResistance"))
        readback_params["ground_resistance"] = float(eng.get_param(BLOCK_FAULT, "GroundResistance"))
        readback_params["fault_switch_times"] = eng.get_param(BLOCK_FAULT, "SwitchTimes")

        # 3. Apply Generator Controls
        if params.gen_rated_mva is not None and params.gen_rated_kv is not None:
            gen_nom_str = f"[{params.gen_rated_mva * 1e6} {params.gen_rated_kv * 1e3} 50]"
            eng.set_param(BLOCK_SYNCHRONOUS_MACHINE, "NominalParameters", gen_nom_str, nargout=0)
            applied_params["gen_nominal"] = gen_nom_str
            readback_params["gen_nominal"] = eng.get_param(BLOCK_SYNCHRONOUS_MACHINE, "NominalParameters")

        if params.gen_mech_power_pu is not None:
            pm_str = str(params.gen_mech_power_pu)
            eng.set_param(BLOCK_GEN_PM, "Value", pm_str, nargout=0)
            applied_params["gen_mech_power_pu"] = params.gen_mech_power_pu
            readback_params["gen_mech_power_pu"] = float(eng.get_param(BLOCK_GEN_PM, "Value"))

        if params.gen_field_voltage_pu is not None:
            vf_str = str(params.gen_field_voltage_pu)
            eng.set_param(BLOCK_GEN_VF, "Value", vf_str, nargout=0)
            applied_params["gen_field_voltage_pu"] = params.gen_field_voltage_pu
            readback_params["gen_field_voltage_pu"] = float(eng.get_param(BLOCK_GEN_VF, "Value"))

        # 4. Apply Transformer Controls
        if params.trafo_rated_mva is not None:
            trafo_nom_str = f"[{params.trafo_rated_mva * 1e6} 50]"
            eng.set_param(BLOCK_TRANSFORMER, "NominalPower", trafo_nom_str, nargout=0)
            applied_params["trafo_nominal_power"] = trafo_nom_str
            readback_params["trafo_nominal_power"] = eng.get_param(BLOCK_TRANSFORMER, "NominalPower")

        if params.trafo_primary_kv is not None:
            w1_str = f"[{params.trafo_primary_kv * 1e3} 0.002 0.08]"
            eng.set_param(BLOCK_TRANSFORMER, "Winding1", w1_str, nargout=0)
            applied_params["trafo_winding1"] = w1_str
            readback_params["trafo_winding1"] = eng.get_param(BLOCK_TRANSFORMER, "Winding1")

        if params.trafo_secondary_v is not None:
            w2_str = f"[{params.trafo_secondary_v} 0.002 0.08]"
            eng.set_param(BLOCK_TRANSFORMER, "Winding2", w2_str, nargout=0)
            applied_params["trafo_winding2"] = w2_str
            readback_params["trafo_winding2"] = eng.get_param(BLOCK_TRANSFORMER, "Winding2")

        # 5. Apply Load & Power Factor Controls
        p_watts = (params.load_active_power_mw or 500.0) * 1e6
        if params.load_power_factor is not None and params.load_power_factor < 0.999:
            # Physical relation: Q = P * tan(arccos(pf))
            pf = max(0.1, min(1.0, params.load_power_factor))
            phi = math.acos(pf)
            q_vars = p_watts * math.tan(phi)
        elif params.load_reactive_power_mvar is not None:
            q_vars = params.load_reactive_power_mvar * 1e6
        else:
            q_vars = 0.0

        eng.set_param(BLOCK_LOAD, "ActivePower", str(p_watts), nargout=0)
        eng.set_param(BLOCK_LOAD, "InductivePower", str(q_vars), nargout=0)
        applied_params["load_active_power_mw"] = p_watts / 1e6
        applied_params["load_reactive_power_mvar"] = q_vars / 1e6
        applied_params["load_power_factor"] = params.load_power_factor
        readback_params["load_active_power_mw"] = float(eng.get_param(BLOCK_LOAD, "ActivePower")) / 1e6
        readback_params["load_inductive_power_mvar"] = float(eng.get_param(BLOCK_LOAD, "InductivePower")) / 1e6

        # 6. Apply Transmission Line Parameters (Series RLC Branch & PI Section Line)
        if params.line_resistance is not None:
            eng.set_param(BLOCK_SERIES_RLC, "Resistance", str(params.line_resistance), nargout=0)
            applied_params["series_line_resistance"] = params.line_resistance
            readback_params["series_line_resistance"] = float(eng.get_param(BLOCK_SERIES_RLC, "Resistance"))

        if params.line_inductance is not None:
            eng.set_param(BLOCK_SERIES_RLC, "Inductance", str(params.line_inductance), nargout=0)
            applied_params["series_line_inductance"] = params.line_inductance
            readback_params["series_line_inductance"] = float(eng.get_param(BLOCK_SERIES_RLC, "Inductance"))

        if params.line_capacitance is not None:
            eng.set_param(BLOCK_SERIES_RLC, "Capacitance", str(params.line_capacitance), nargout=0)
            applied_params["series_line_capacitance"] = params.line_capacitance
            readback_params["series_line_capacitance"] = float(eng.get_param(BLOCK_SERIES_RLC, "Capacitance"))

        if params.pi_line_length_km is not None:
            eng.set_param(BLOCK_PI_LINE, "Length", str(params.pi_line_length_km), nargout=0)
            applied_params["pi_line_length_km"] = params.pi_line_length_km
            readback_params["pi_line_length_km"] = float(eng.get_param(BLOCK_PI_LINE, "Length"))

        # 7. Clear any stale simulation artifacts in MATLAB workspace
        eng.eval("clear ScopeData simOut scopeObj;", nargout=0)

        # 8. Execute Simulation
        logger.info(f"Executing sim('{MODEL_NAME}')...")
        t_sim_start = time.time()
        try:
            eng.eval(f"simOut = sim('{MODEL_NAME}');", nargout=0)
        except Exception as e:
            logger.error(f"Simulink solver error: {e}")
            self._restore_defaults_sync(eng)
            raise RuntimeError(f"Simulink solver failed during simulation execution: {e}")
        sim_duration = time.time() - t_sim_start
        logger.info(f"Simulink solver completed in {sim_duration:.2f}s.")

        # 9. Extract ScopeData from Workspace
        try:
            eng.eval(
                "if exist('ScopeData','var'), scopeObj = ScopeData; "
                "elseif exist('simOut','var') && isa(simOut,'Simulink.SimulationOutput'), scopeObj = simOut.get('ScopeData'); "
                "else, error('ScopeData not found in MATLAB workspace'); end",
                nargout=0
            )
            raw_time = np.array(eng.eval("scopeObj.time")).flatten()
            raw_signals = np.array(eng.eval("scopeObj.signals.values"))
        except Exception as e:
            logger.error(f"Failed to extract ScopeData: {e}")
            self._restore_defaults_sync(eng)
            raise RuntimeError(f"ScopeData extraction failed: {e}")

        # 10. Validate Array Dimensions and Orientation
        if raw_signals.ndim == 2 and raw_signals.shape[0] != len(raw_time):
            raw_signals = raw_signals.T

        if raw_signals.shape[1] != 9:
            raise ValueError(f"Expected 9 signal channels in ScopeData, but found {raw_signals.shape[1]}")

        # 11. Restore in-memory model parameters to nominal defaults
        self._restore_defaults_sync(eng)

        # 12. Clear temporary workspace variables to ensure subsequent run hygiene
        eng.eval("clear ScopeData simOut scopeObj;", nargout=0)

        total_duration = time.time() - t0
        logger.info(f"Total simulation pipeline executed in {total_duration:.2f}s. Extracted {len(raw_time)} samples.")

        return {
            "time": raw_time,
            "signals": raw_signals,
            "sim_duration": sim_duration,
            "total_duration": total_duration,
            "num_samples": len(raw_time),
            "applied_parameters": applied_params,
            "readback_parameters": readback_params,
        }

    def _restore_defaults_sync(self, eng: Any) -> None:
        """Restores in-memory block parameters to avoid test pollution or unintended persistence."""
        try:
            default_flags = FAULT_MAPPING[DEFAULTS["fault_type"]]
            for p, v in default_flags.items():
                eng.set_param(BLOCK_FAULT, p, v, nargout=0)
            eng.set_param(BLOCK_FAULT, "FaultResistance", DEFAULTS["fault_resistance"], nargout=0)
            eng.set_param(BLOCK_FAULT, "GroundResistance", DEFAULTS["ground_resistance"], nargout=0)
            eng.set_param(BLOCK_FAULT, "SwitchTimes", DEFAULTS["switch_times"], nargout=0)

            eng.set_param(BLOCK_SYNCHRONOUS_MACHINE, "NominalParameters", DEFAULTS["gen_nominal"], nargout=0)
            eng.set_param(BLOCK_GEN_PM, "Value", DEFAULTS["gen_pm"], nargout=0)
            eng.set_param(BLOCK_GEN_VF, "Value", DEFAULTS["gen_vf"], nargout=0)

            eng.set_param(BLOCK_TRANSFORMER, "NominalPower", DEFAULTS["trafo_nominal_power"], nargout=0)
            eng.set_param(BLOCK_TRANSFORMER, "Winding1", DEFAULTS["trafo_winding1"], nargout=0)
            eng.set_param(BLOCK_TRANSFORMER, "Winding2", DEFAULTS["trafo_winding2"], nargout=0)

            eng.set_param(BLOCK_LOAD, "ActivePower", DEFAULTS["load_active"], nargout=0)
            eng.set_param(BLOCK_LOAD, "InductivePower", DEFAULTS["load_inductive"], nargout=0)

            eng.set_param(BLOCK_SERIES_RLC, "Resistance", DEFAULTS["series_r"], nargout=0)
            eng.set_param(BLOCK_SERIES_RLC, "Inductance", DEFAULTS["series_l"], nargout=0)
            eng.set_param(BLOCK_SERIES_RLC, "Capacitance", DEFAULTS["series_c"], nargout=0)

            eng.set_param(BLOCK_PI_LINE, "Length", DEFAULTS["pi_length"], nargout=0)
        except Exception as e:
            logger.warning(f"Could not restore default parameters: {e}")

