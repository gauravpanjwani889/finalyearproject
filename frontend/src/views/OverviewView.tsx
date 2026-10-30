import React from 'react';
import {
  SimulationResponse,
  SystemHealth,
  ModelInfo,
  FaultType,
  SimulationParams,
} from '../types';
import { NetworkSchematic } from '../components/NetworkSchematic';
import { KpiCard } from '../components/KpiCard';
import { TripBreakerChart } from '../components/TripBreakerChart';
import {
  Activity,
  Zap,
  Gauge,
  Flame,
  Power,
  ShieldAlert,
  Play,
  RotateCcw,
  CheckCircle2,
  Clock,
  Layers,
} from 'lucide-react';

interface OverviewViewProps {
  simulationResult: SimulationResponse | null;
  health: SystemHealth | null;
  modelInfo: ModelInfo | null;
  isRunning: boolean;
  onQuickRun: (faultType: FaultType) => void;
  onNavigateToControls: () => void;
  onNavigateToWaveforms: () => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  simulationResult,
  health,
  modelInfo,
  isRunning,
  onQuickRun,
  onNavigateToControls,
  onNavigateToWaveforms,
}) => {
  const metrics = simulationResult?.metrics;
  const isTripped = metrics?.is_breaker_tripped ?? false;
  const isFaulted = metrics?.is_fault_detected ?? false;

  return (
    <div className="space-y-6">
      {/* Top Banner / System Provenance */}
      <div className="bg-gradient-to-r from-grid-900 via-grid-850 to-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-white tracking-tight">
                Industrial Grid Stability & Supervisory Control
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                ACTIVE SOLVER
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Engine: {modelInfo?.matlab_version || 'MATLAB R2025a Update 1'} | Solver: Discrete (Tustin T<sub className="text-[9px]">s</sub>=50µs) | Samples: 20,005 / run
            </p>
          </div>
        </div>

        {/* Quick Launch Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => onQuickRun('NORMAL')}
            disabled={isRunning}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-grid-800 hover:bg-grid-700 text-slate-200 border border-grid-700 text-xs font-medium transition-all disabled:opacity-50"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Test NORMAL</span>
          </button>
          <button
            onClick={() => onQuickRun('AG')}
            disabled={isRunning}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-medium transition-all disabled:opacity-50"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span>Inject AG Fault</span>
          </button>
          <button
            onClick={() => onQuickRun('ABC')}
            disabled={isRunning}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 text-xs font-medium transition-all disabled:opacity-50"
          >
            <Flame className="w-3.5 h-3.5 text-rose-400" />
            <span>Inject ABC Fault</span>
          </button>
          <button
            onClick={onNavigateToControls}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 text-slate-950 font-semibold text-xs hover:bg-cyan-400 shadow-md shadow-cyan-500/20 transition-all"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Custom Simulation</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KpiCard
          title="Breaker Status"
          value={metrics ? (isTripped ? 'TRIPPED' : 'CLOSED') : 'READY'}
          unit={metrics ? `Trip=${isTripped ? '1' : '0'}` : ''}
          icon={ShieldAlert}
          variant={isTripped ? 'rose' : isFaulted ? 'amber' : 'emerald'}
          subtitle={
            metrics?.breaker_trip_time
              ? `Actuated at ${metrics.breaker_trip_time} s`
              : 'Nominal 0 V latch'
          }
          badge={isTripped ? 'ISOLATED' : 'CLOSED (HEALTHY)'}
        />

        <KpiCard
          title="Peak Current"
          value={metrics?.peak_current ?? '—'}
          unit="A"
          icon={Flame}
          variant={metrics && metrics.peak_current > 100 ? 'rose' : 'cyan'}
          subtitle={
            metrics
              ? `Surge: ${metrics.max_disturbance_magnitude}x baseline`
              : 'Nominal ~10-20 A'
          }
        />

        <KpiCard
          title="Min Voltage"
          value={metrics?.min_voltage ?? '—'}
          unit="V"
          icon={Zap}
          variant={metrics && metrics.min_voltage < 100 ? 'rose' : 'cyan'}
          subtitle={
            metrics
              ? metrics.min_voltage < 100
                ? 'Undervoltage (<100V)'
                : 'Within tolerance'
              : 'Nominal ~230 V'
          }
        />

        <KpiCard
          title="Active Power P"
          value={metrics?.mean_active_power_kw ?? '—'}
          unit="kW"
          icon={Power}
          variant="slate"
          subtitle="Mean instantaneous va·ia+vb·ib+vc·ic"
        />

        <KpiCard
          title="Reactive Power Q"
          value={metrics?.mean_reactive_power_kvar ?? '—'}
          unit="kVAR"
          icon={Gauge}
          variant="slate"
          subtitle="Clarke α-β Akagi theory"
        />

        <KpiCard
          title="Power Factor"
          value={metrics?.power_factor ?? '—'}
          unit="cos φ"
          icon={Activity}
          variant={metrics && metrics.power_factor < 0.85 ? 'amber' : 'emerald'}
          subtitle="Operational P / S ratio"
        />
      </div>

      {/* Grid Network Topology Schematic */}
      <NetworkSchematic simulationResult={simulationResult} />

      {/* Circuit Breaker Protection Trip Visualization */}
      {simulationResult && (
        <TripBreakerChart
          time={simulationResult.waveforms.time}
          trip={simulationResult.waveforms.trip}
          metrics={simulationResult.metrics}
          height={200}
        />
      )}

      {/* Latest Run Provenance Card */}
      {simulationResult && (
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-4 lg:p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-grid-800 border border-grid-700 text-cyan-400">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-semibold text-slate-300">
                  Run ID: {simulationResult.run_id}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  Scenario: {simulationResult.params.fault_type}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Simulated {simulationResult.total_samples.toLocaleString()} raw time points in {simulationResult.execution_duration_sec}s | Rendered {simulationResult.downsampled_samples} points
              </p>
            </div>
          </div>

          <button
            onClick={onNavigateToWaveforms}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-grid-800 hover:bg-grid-750 text-cyan-400 border border-cyan-500/30 text-xs font-medium transition-all"
          >
            <Layers className="w-4 h-4" />
            <span>Inspect 9 Waveform Channels</span>
          </button>
        </div>
      )}
    </div>
  );
};
