"""
FastAPI Route Endpoints for Simulation Orchestration, Model Inspection, and Telemetry.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status

from backend.config import (
    MODEL_NAME,
    MODEL_PATH,
    POWERGUI_SAMPLE_TIME,
    SIMULATION_STOP_TIME,
    TOTAL_EXPECTED_SAMPLES,
)
from backend.models import (
    SimulationParams,
    SimulationResponse,
    ModelInfoResponse,
    HealthResponse,
    FaultType,
)
from backend.matlab_engine import MatlabSessionManager
from backend.sim_runner import SimulationRunner, FAULT_MAPPING
from backend.analytics import (
    compute_true_powers,
    calculate_electrical_metrics,
    decimate_waveforms,
)

logger = logging.getLogger("smart_grid.api")
router = APIRouter()

# In-memory run history cache (holds recent completed simulation results)
SIMULATION_STORE: Dict[str, SimulationResponse] = {}


@router.get("/health", response_model=HealthResponse, tags=["System Health"])
async def get_health():
    """Health check endpoint reflecting MATLAB Engine connectivity and model state."""
    manager = await MatlabSessionManager.get_instance()
    return HealthResponse(
        status="ONLINE" if manager.is_connected else "INITIALIZING",
        matlab_connected=manager.is_connected,
        model_loaded=manager.is_model_loaded,
        active_simulations=1 if manager.lock.locked() else 0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/model/info", response_model=ModelInfoResponse, tags=["Model Inspection"])
async def get_model_info():
    """Returns technical metadata, solver parameters, and block configuration."""
    manager = await MatlabSessionManager.get_instance()
    return ModelInfoResponse(
        model_name=MODEL_NAME,
        model_path=str(MODEL_PATH),
        matlab_version=manager.matlab_version,
        simulink_release="R2025a Update 1",
        total_blocks=73,
        solver_mode="Discrete (Tustin/Backward Euler)",
        sample_time=POWERGUI_SAMPLE_TIME,
        fundamental_frequency=50.0,
        supported_fault_types=[ft.value for ft in FaultType],
        signal_channels=[
            {"index": "0", "name": "Va", "unit": "V", "description": "Phase A Line-to-Line Voltage"},
            {"index": "1", "name": "Vb", "unit": "V", "description": "Phase B Line-to-Line Voltage"},
            {"index": "2", "name": "Vc", "unit": "V", "description": "Phase C Line-to-Line Voltage"},
            {"index": "3", "name": "Ia", "unit": "A", "description": "Phase A Line Current"},
            {"index": "4", "name": "Ib", "unit": "A", "description": "Phase B Line Current"},
            {"index": "5", "name": "Ic", "unit": "A", "description": "Phase C Line Current"},
            {"index": "6", "name": "Trip", "unit": "Binary [0,1]", "description": "Circuit Breaker Status (0=Closed, 1=Open)"},
            {"index": "7", "name": "Vmag", "unit": "V", "description": "Positive-Sequence Voltage Magnitude"},
            {"index": "8", "name": "Imag", "unit": "A", "description": "Positive-Sequence Current Magnitude"},
        ],
        measurement_location="Bus 2: 415V Low-Voltage Bus at Series VSC 1 Converter Terminals (PWM carrier harmonics: 2 kHz, THD ~16%)",
    )


@router.get("/model/parameters", tags=["Model Inspection"])
async def get_model_parameters():
    """Returns supported parameter boundaries and nominal defaults for grid simulations."""
    return {
        "fault_types": [
            {"type": "NORMAL", "description": "Healthy transmission line operation (no fault injection)"},
            {"type": "AG", "description": "Single Line-to-Ground fault (Phase A to Ground)"},
            {"type": "BG", "description": "Single Line-to-Ground fault (Phase B to Ground)"},
            {"type": "CG", "description": "Single Line-to-Ground fault (Phase C to Ground)"},
            {"type": "AB", "description": "Line-to-Line fault (Phase A to Phase B)"},
            {"type": "BC", "description": "Line-to-Line fault (Phase B to Phase C)"},
            {"type": "CA", "description": "Line-to-Line fault (Phase C to Phase A)"},
            {"type": "ABG", "description": "Double Line-to-Ground fault (Phases A & B to Ground)"},
            {"type": "BCG", "description": "Double Line-to-Ground fault (Phases B & C to Ground)"},
            {"type": "CAG", "description": "Double Line-to-Ground fault (Phases C & A to Ground)"},
            {"type": "ABC", "description": "Symmetrical Three-Phase fault (Phases A, B, C)"},
            {"type": "ABCG", "description": "Symmetrical Three-Phase-to-Ground fault (Phases A, B, C to Ground)"},
        ],
        "defaults": {
            "fault_type": "ABC",
            "fault_resistance": 0.001,
            "ground_resistance": 0.01,
            "fault_start_time": 0.2,
            "fault_stop_time": 0.4,
            "gen_rated_mva": 10.0,
            "gen_rated_kv": 11.0,
            "gen_field_voltage_pu": 1.0,
            "gen_mech_power_pu": 1.0,
            "trafo_rated_mva": 5.0,
            "trafo_primary_kv": 11.0,
            "trafo_secondary_v": 415.0,
            "load_active_power_mw": 500.0,
            "load_power_factor": 1.0,
            "load_reactive_power_mvar": 0.0,
            "line_resistance": 0.001,
            "line_inductance": 0.001,
            "line_capacitance": 1e-6,
            "pi_line_length_km": 100.0,
            "downsample_points": 1000,
        },
        "limits": {
            "fault_resistance": {"min": 0.0001, "max": 100.0, "unit": "Ohms"},
            "ground_resistance": {"min": 0.0001, "max": 100.0, "unit": "Ohms"},
            "fault_start_time": {"min": 0.15, "max": 0.8, "unit": "s"},
            "fault_stop_time": {"min": 0.20, "max": 0.95, "unit": "s"},
            "gen_rated_mva": {"min": 1.0, "max": 100.0, "unit": "MVA"},
            "gen_rated_kv": {"min": 1.0, "max": 33.0, "unit": "kV"},
            "gen_field_voltage_pu": {"min": 0.5, "max": 1.5, "unit": "pu"},
            "gen_mech_power_pu": {"min": 0.1, "max": 1.5, "unit": "pu"},
            "trafo_rated_mva": {"min": 0.5, "max": 50.0, "unit": "MVA"},
            "trafo_primary_kv": {"min": 1.0, "max": 33.0, "unit": "kV"},
            "trafo_secondary_v": {"min": 100.0, "max": 11000.0, "unit": "V"},
            "load_active_power_mw": {"min": 0.1, "max": 2000.0, "unit": "MW"},
            "load_power_factor": {"min": 0.5, "max": 1.0, "unit": "pf"},
            "load_reactive_power_mvar": {"min": 0.0, "max": 1500.0, "unit": "MVAR"},
            "line_resistance": {"min": 0.0001, "max": 10.0, "unit": "Ohms"},
            "line_inductance": {"min": 1e-5, "max": 0.1, "unit": "Henrys"},
            "line_capacitance": {"min": 1e-9, "max": 1e-3, "unit": "Farads"},
            "pi_line_length_km": {"min": 1.0, "max": 500.0, "unit": "km"},
        },
    }


@router.post("/simulation/run", response_model=SimulationResponse, tags=["Simulation Execution"])
async def run_simulation(params: SimulationParams):
    """
    Executes an authoritative Simulink model simulation on MATLAB R2025a,
    extracts the ScopeData signals, performs electrical analysis, and returns telemetry.
    """
    manager = await MatlabSessionManager.get_instance()
    runner = SimulationRunner(manager)

    run_id = str(uuid.uuid4())
    logger.info(f"Initiating simulation run [{run_id}] with fault={params.fault_type.value}...")

    try:
        raw_output = await runner.run_simulation(params)
    except Exception as e:
        logger.error(f"Simulation run [{run_id}] failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation execution error: {str(e)}",
        )

    time_vec = raw_output["time"]
    signals = raw_output["signals"]

    # 1. Compute Authentic Physical Powers
    va, vb, vc = signals[:, 0], signals[:, 1], signals[:, 2]
    ia, ib, ic = signals[:, 3], signals[:, 4], signals[:, 5]
    p_inst, q_inst = compute_true_powers(va, vb, vc, ia, ib, ic)

    # 2. Compute Validated Electrical Metrics
    metrics = calculate_electrical_metrics(time_vec, signals, p_inst, q_inst)

    # 3. Waveform Decimation for Web Rendering
    waveforms = decimate_waveforms(
        time_vec,
        signals,
        p_inst,
        q_inst,
        target_points=params.downsample_points,
        include_full=params.include_full_waveform,
    )

    warnings_list = []
    if metrics.is_fault_detected and not metrics.is_breaker_tripped:
        warnings_list.append("Fault detected by relay logic, but circuit breaker trip did not latch.")
    if params.fault_type == FaultType.NORMAL and metrics.is_breaker_tripped:
        warnings_list.append("Circuit breaker tripped under nominal conditions. Verify threshold settings.")

    response = SimulationResponse(
        run_id=run_id,
        status="SUCCESS",
        execution_duration_sec=round(raw_output["total_duration"], 2),
        params=params,
        metrics=metrics,
        waveforms=waveforms,
        total_samples=len(time_vec),
        downsampled_samples=len(waveforms.time),
        units={
            "time": "s",
            "voltage": "V",
            "current": "A",
            "active_power": "kW",
            "reactive_power": "kVAR",
            "trip": "binary",
        },
        data_provenance=f"MATLAB R2025a Update 1 / Simulink Discrete Solver ({MODEL_NAME}.slx)",
        simulation_mode="Mode 1 — Dynamic Simulink Transient Simulation",
        applied_parameters=raw_output.get("applied_parameters", {}),
        readback_parameters=raw_output.get("readback_parameters", {}),
        warnings=warnings_list,
    )

    # Cache result in in-memory store
    SIMULATION_STORE[run_id] = response

    # ML fault diagnosis on full-resolution signals
    try:
        import numpy as _np
        from fault_ml import api_router as _mlr
        _mlr.ML_STORE[run_id] = _mlr._get().predict_run(_np.asarray(time_vec), _np.asarray(signals)[:, :7])
    except Exception as _e:
        logger.warning(f'ML prediction skipped for run [{run_id}]: {_e}')

    return response



@router.get("/simulation/results/{run_id}", response_model=SimulationResponse, tags=["Simulation Results"])
async def get_simulation_result(run_id: str):
    """Retrieves cached telemetry and waveforms from a prior simulation run."""
    if run_id not in SIMULATION_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run with ID '{run_id}' not found in cache.",
        )
    return SIMULATION_STORE[run_id]


@router.get("/simulation/history", tags=["Simulation Results"])
async def get_simulation_history():
    """Retrieves summary list of all cached simulation runs."""
    return [
        {
            "run_id": r_id,
            "status": resp.status,
            "fault_type": resp.params.fault_type,
            "execution_duration_sec": resp.execution_duration_sec,
            "fault_resistance": resp.params.fault_resistance,
            "ground_resistance": resp.params.ground_resistance,
            "is_fault_detected": resp.metrics.is_fault_detected,
            "is_breaker_tripped": resp.metrics.is_breaker_tripped,
            "peak_current": resp.metrics.peak_current,
            "min_voltage": resp.metrics.min_voltage,
            "power_factor": resp.metrics.power_factor,
            "downsampled_samples": resp.downsampled_samples,
        }
        for r_id, resp in reversed(list(SIMULATION_STORE.items()))
    ]

