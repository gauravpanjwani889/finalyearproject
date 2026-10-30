import {
  SimulationParams,
  SimulationResponse,
  SimulationHistoryItem,
  SystemHealth,
  ModelInfo,
  ParameterLimits,
} from '../types';

const API_BASE = '/api';

export async function checkHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}

export async function getModelInfo(): Promise<ModelInfo> {
  const res = await fetch(`${API_BASE}/model/info`);
  if (!res.ok) {
    throw new Error(`Failed to fetch model info: ${res.statusText}`);
  }
  return res.json();
}

export async function getModelParameters(): Promise<ParameterLimits> {
  const res = await fetch(`${API_BASE}/model/parameters`);
  if (!res.ok) {
    throw new Error(`Failed to fetch model parameters: ${res.statusText}`);
  }
  return res.json();
}

export async function executeSimulation(
  params: SimulationParams,
  onStatusUpdate?: (status: string) => void
): Promise<SimulationResponse> {
  if (onStatusUpdate) {
    onStatusUpdate('Submitting parameters to Simulink solver...');
  }

  const res = await fetch(`${API_BASE}/simulation/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Simulation failed: HTTP ${res.status}`);
  }

  return res.json();
}

export async function getSimulationResult(runId: string): Promise<SimulationResponse> {
  const res = await fetch(`${API_BASE}/simulation/results/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve simulation run ${runId}: ${res.statusText}`);
  }
  return res.json();
}

export async function getSimulationHistory(): Promise<SimulationHistoryItem[]> {
  const res = await fetch(`${API_BASE}/simulation/history`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve simulation history: ${res.statusText}`);
  }
  return res.json();
}

export interface MlPrediction {
  fault_type: string;
  confidence: number;
  top3: { class: string; probability: number }[];
  probabilities: Record<string, number>;
  [key: string]: unknown;
}

export async function predictFault(w: {
  time: number[]; va: number[]; vb: number[]; vc: number[];
  ia: number[]; ib: number[]; ic: number[]; trip?: number[];
}): Promise<MlPrediction> {
  const res = await fetch(`${API_BASE}/ml/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(w),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `ML prediction failed: HTTP ${res.status}`);
  }
  return res.json();
}
