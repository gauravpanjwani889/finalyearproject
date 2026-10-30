export type FaultType =
  | 'NORMAL'
  | 'AG'
  | 'BG'
  | 'CG'
  | 'AB'
  | 'BC'
  | 'CA'
  | 'ABG'
  | 'BCG'
  | 'CAG'
  | 'ABC'
  | 'ABCG';

export interface SimulationParams {
  fault_type: FaultType;
  fault_resistance: number;
  ground_resistance: number;
  fault_start_time?: number;
  fault_stop_time?: number;
  gen_rated_mva?: number;
  gen_rated_kv?: number;
  gen_field_voltage_pu?: number;
  gen_mech_power_pu?: number;
  trafo_rated_mva?: number;
  trafo_primary_kv?: number;
  trafo_secondary_v?: number;
  load_active_power_mw?: number;
  load_power_factor?: number;
  load_reactive_power_mvar?: number;
  line_resistance?: number;
  line_inductance?: number;
  line_capacitance?: number;
  pi_line_length_km?: number;
  downsample_points: number;
  include_full_waveform?: boolean;
}

export interface WaveformData {
  time: number[];
  va: number[];
  vb: number[];
  vc: number[];
  ia: number[];
  ib: number[];
  ic: number[];
  trip: number[];
  vmag: number[];
  imag: number[];
  p_active: number[];
  q_reactive: number[];
}

export interface ElectricalMetrics {
  peak_current: number;
  min_voltage: number;
  rms_voltage_prefault: number;
  rms_voltage_fault: number;
  rms_current_prefault: number;
  rms_current_fault: number;
  thd_voltage_pct: number;
  fundamental_voltage_rms: number;
  fundamental_frequency_hz: number;
  fault_onset_time: number | null;
  breaker_trip_time: number | null;
  breaker_reset_time: number | null;
  fault_to_trip_delay_ms: number | null;
  trip_duration_ms: number | null;
  max_disturbance_magnitude: number;
  is_fault_detected: boolean;
  is_breaker_tripped: boolean;
  mean_active_power_kw: number;
  mean_reactive_power_kvar: number;
  power_factor: number;
}

export interface SimulationResponse {
  run_id: string;
  status: string;
  execution_duration_sec: number;
  params: SimulationParams;
  metrics: ElectricalMetrics;
  waveforms: WaveformData;
  total_samples: number;
  downsampled_samples: number;
  units: Record<string, string>;
  data_provenance: string;
  simulation_mode: string;
  applied_parameters: Record<string, any>;
  readback_parameters: Record<string, any>;
  warnings: string[];
}

export interface SimulationHistoryItem {
  run_id: string;
  status: string;
  fault_type: FaultType;
  execution_duration_sec: number;
  fault_resistance: number;
  ground_resistance: number;
  is_fault_detected: boolean;
  is_breaker_tripped: boolean;
  peak_current: number;
  min_voltage: number;
  power_factor: number;
  downsampled_samples: number;
  timestamp?: string;
}

export interface SystemHealth {
  status: string;
  matlab_connected: boolean;
  model_loaded: boolean;
  active_simulations: number;
  timestamp: string;
}

export interface ModelInfo {
  model_name: string;
  model_path: string;
  matlab_version: string;
  simulink_release: string;
  total_blocks: number;
  solver_mode: string;
  sample_time: number;
  fundamental_frequency: number;
  supported_fault_types: string[];
  signal_channels: Array<{
    index: string;
    name: string;
    unit: string;
    description: string;
  }>;
  measurement_location: string;
}

export interface ParameterLimits {
  fault_types: Array<{ type: FaultType; description: string }>;
  defaults: Record<string, number | string>;
  limits: Record<string, { min: number; max: number; unit: string }>;
}

