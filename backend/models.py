"""
Pydantic Data Models for Simulation Requests, Responses, and Electrical Telemetry.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FaultType(str, Enum):
    NORMAL = "NORMAL"
    AG = "AG"
    BG = "BG"
    CG = "CG"
    AB = "AB"
    BC = "BC"
    CA = "CA"
    ABG = "ABG"
    BCG = "BCG"
    CAG = "CAG"
    ABC = "ABC"
    ABCG = "ABCG"


class SimulationParams(BaseModel):
    # --- 1. Fault Configuration ---
    fault_type: FaultType = Field(
        default=FaultType.ABC,
        description="Electrical fault type: NORMAL, AG, BG, CG, AB, BC, CA, ABG, BCG, CAG, ABC, ABCG"
    )
    fault_resistance: float = Field(
        default=0.001,
        ge=0.0001,
        le=100.0,
        description="Fault resistance Rf in Ohms"
    )
    ground_resistance: float = Field(
        default=0.01,
        ge=0.0001,
        le=100.0,
        description="Ground resistance Rg in Ohms (for ground-involving faults)"
    )
    fault_start_time: float = Field(
        default=0.2,
        ge=0.15,
        le=0.8,
        description="Fault inception time in seconds (must be >= 0.15s after startup transient)"
    )
    fault_stop_time: float = Field(
        default=0.4,
        ge=0.2,
        le=0.95,
        description="Fault clearing / breaker reset time in seconds"
    )

    # --- 2. Generator Controls ---
    gen_rated_mva: Optional[float] = Field(
        default=10.0,
        ge=1.0,
        le=100.0,
        description="Generator rated apparent power in MVA"
    )
    gen_rated_kv: Optional[float] = Field(
        default=11.0,
        ge=1.0,
        le=33.0,
        description="Generator rated line-to-line voltage in kV"
    )
    gen_field_voltage_pu: Optional[float] = Field(
        default=1.0,
        ge=0.5,
        le=1.5,
        description="Generator field excitation voltage setpoint Vf in per-unit"
    )
    gen_mech_power_pu: Optional[float] = Field(
        default=1.0,
        ge=0.1,
        le=1.5,
        description="Generator mechanical turbine power Pm setpoint in per-unit"
    )

    # --- 3. Transformer Controls ---
    trafo_rated_mva: Optional[float] = Field(
        default=5.0,
        ge=0.5,
        le=50.0,
        description="Step-down transformer rated apparent power in MVA"
    )
    trafo_primary_kv: Optional[float] = Field(
        default=11.0,
        ge=1.0,
        le=33.0,
        description="Transformer primary winding nominal voltage in kV"
    )
    trafo_secondary_v: Optional[float] = Field(
        default=415.0,
        ge=100.0,
        le=11000.0,
        description="Transformer secondary winding nominal voltage in Volts"
    )

    # --- 4. Load & Power Factor Controls ---
    load_active_power_mw: Optional[float] = Field(
        default=500.0,
        ge=0.1,
        le=2000.0,
        description="Three-phase parallel load active power P in MW"
    )
    load_power_factor: Optional[float] = Field(
        default=1.0,
        ge=0.5,
        le=1.0,
        description="Operational load power factor (calculates reactive demand Q = P * tan(acos(pf)))"
    )
    load_reactive_power_mvar: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1500.0,
        description="Three-phase parallel load inductive reactive power Q in MVAR (overridden if pf < 1.0)"
    )

    # --- 5. Transmission Line Controls ---
    line_resistance: Optional[float] = Field(
        default=0.001,
        ge=0.0001,
        le=10.0,
        description="Series RLC branch lumped resistance in Ohms"
    )
    line_inductance: Optional[float] = Field(
        default=0.001,
        ge=1e-5,
        le=0.1,
        description="Series RLC branch lumped inductance in Henrys"
    )
    line_capacitance: Optional[float] = Field(
        default=1e-6,
        ge=1e-9,
        le=1e-3,
        description="Series RLC branch lumped capacitance in Farads"
    )
    pi_line_length_km: Optional[float] = Field(
        default=100.0,
        ge=1.0,
        le=500.0,
        description="Three-phase PI section transmission line length in km"
    )

    # --- 6. Telemetry Decimation Controls ---
    downsample_points: int = Field(
        default=1000,
        ge=100,
        le=20005,
        description="Target number of peak-preserving waveform points returned for browser rendering"
    )
    include_full_waveform: bool = Field(
        default=False,
        description="Whether to include all 20,005 full-resolution points in response"
    )


class WaveformData(BaseModel):
    time: List[float]
    va: List[float]
    vb: List[float]
    vc: List[float]
    ia: List[float]
    ib: List[float]
    ic: List[float]
    trip: List[float]
    vmag: List[float]
    imag: List[float]
    p_active: List[float]
    q_reactive: List[float]


class ElectricalMetrics(BaseModel):
    peak_current: float = Field(description="Maximum instantaneous phase current magnitude in Amperes")
    min_voltage: float = Field(description="Minimum positive sequence voltage magnitude in Volts")
    rms_voltage_prefault: float = Field(description="Average phase RMS voltage before fault inception in Volts")
    rms_voltage_fault: float = Field(description="Average phase RMS voltage during fault interval in Volts")
    rms_current_prefault: float = Field(description="Average phase RMS current before fault inception in Amperes")
    rms_current_fault: float = Field(description="Average phase RMS current during fault interval in Amperes")
    thd_voltage_pct: float = Field(default=0.0, description="Total Harmonic Distortion (THD) of bus voltage in percent")
    fundamental_voltage_rms: float = Field(default=0.0, description="RMS amplitude of 50 Hz fundamental voltage component in Volts")
    fundamental_frequency_hz: float = Field(default=50.0, description="Grid fundamental frequency in Hz")
    fault_onset_time: Optional[float] = Field(None, description="Time of fault inception in seconds")
    breaker_trip_time: Optional[float] = Field(None, description="Timestamp when circuit breaker tripped in seconds")
    breaker_reset_time: Optional[float] = Field(None, description="Timestamp when circuit breaker reset/closed in seconds")
    fault_to_trip_delay_ms: Optional[float] = Field(None, description="Delay between fault onset and trip actuation in ms")
    trip_duration_ms: Optional[float] = Field(None, description="Total duration breaker remained open in ms")
    max_disturbance_magnitude: float = Field(description="Maximum instantaneous current surge relative to pre-fault baseline")
    is_fault_detected: bool = Field(description="Whether protection relay detected a fault condition")
    is_breaker_tripped: bool = Field(description="Whether circuit breaker latched open (Trip = 1)")
    mean_active_power_kw: float = Field(description="Mean instantaneous 3-phase active power in kW")
    mean_reactive_power_kvar: float = Field(description="Mean instantaneous 3-phase reactive power in kVAR")
    power_factor: float = Field(description="Computed operational power factor (P / S)")


class SimulationResponse(BaseModel):
    run_id: str
    status: str
    execution_duration_sec: float
    params: SimulationParams
    metrics: ElectricalMetrics
    waveforms: WaveformData
    total_samples: int
    downsampled_samples: int
    units: Dict[str, str]
    data_provenance: str
    simulation_mode: str = Field(default="Mode 1 — Dynamic Simulink Transient Simulation")
    applied_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters written to MATLAB Simulink blocks")
    readback_parameters: Dict[str, Any] = Field(default_factory=dict, description="Verified parameters read back from Simulink blocks via get_param")
    warnings: List[str] = Field(default_factory=list)


class ModelInfoResponse(BaseModel):
    model_name: str
    model_path: str
    matlab_version: str
    simulink_release: str
    total_blocks: int
    solver_mode: str
    sample_time: float
    fundamental_frequency: float
    supported_fault_types: List[str]
    signal_channels: List[Dict[str, str]]
    measurement_location: str


class HealthResponse(BaseModel):
    status: str
    matlab_connected: bool
    model_loaded: bool
    active_simulations: int
    timestamp: str

