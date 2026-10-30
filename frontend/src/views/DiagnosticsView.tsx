import React from 'react';
import { SimulationResponse } from '../types';
import {
  ShieldAlert,
  Clock,
  Zap,
  Activity,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Gauge,
  Radio,
  Sliders,
} from 'lucide-react';

interface DiagnosticsViewProps {
  simulationResult: SimulationResponse | null;
}

export const DiagnosticsView: React.FC<DiagnosticsViewProps> = ({
  simulationResult,
}) => {
  if (!simulationResult) {
    return (
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-12 text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-grid-800 border border-grid-700 flex items-center justify-center text-slate-500">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold text-white">No Diagnostic Telemetry Available</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute a simulation to view verified protective relay timing, trip delays, and pre-fault vs. fault RMS stress metrics.
        </p>
      </div>
    );
  }

  const { metrics, params, warnings } = simulationResult;
  const isTripped = metrics.is_breaker_tripped;
  const isFaultDetected = metrics.is_fault_detected;

  // Voltage drop percentage
  const vDipPercent =
    metrics.rms_voltage_prefault > 0
      ? (
          ((metrics.rms_voltage_prefault - metrics.rms_voltage_fault) /
            metrics.rms_voltage_prefault) *
          100
        ).toFixed(1)
      : '0.0';

  // Current surge multiplier
  const iSurgeMultiplier =
    metrics.rms_current_prefault > 0
      ? (metrics.rms_current_fault / metrics.rms_current_prefault).toFixed(1)
      : '1.0';

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            <span>Protection & Fault Diagnostics</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Empirical evaluation of relay tripping logic, circuit breaker clearing interval, and electrical network stress.
          </p>
        </div>

        {/* Protection Health Tag */}
        <div className="flex items-center space-x-2">
          {isTripped ? (
            <div className="px-3 py-1.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-mono font-semibold flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span>BREAKER ACTUATED (TRIPPED)</span>
            </div>
          ) : isFaultDetected ? (
            <div className="px-3 py-1.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs font-mono font-semibold flex items-center space-x-1.5">
              <span>FAULT DETECTED (NO TRIP)</span>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-mono font-semibold flex items-center space-x-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>NORMAL GRID OPERATION</span>
            </div>
          )}
        </div>
      </div>

      {warnings && warnings.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-1 font-mono">
          <div className="font-semibold flex items-center space-x-1">
            <AlertTriangle className="w-4 h-4" />
            <span>Protection Relay Advisories:</span>
          </div>
          {warnings.map((w, idx) => (
            <p key={idx} className="pl-5 text-amber-200">
              • {w}
            </p>
          ))}
        </div>
      )}

      {/* Grid: 4 Core Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Scenario vs Detection */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-2">
          <span className="text-xs font-mono uppercase text-slate-400">Configured Scenario</span>
          <div className="text-xl font-bold font-mono text-cyan-300">{params.fault_type}</div>
          <p className="text-xs text-slate-400 font-mono">
            Relay Trigger:{' '}
            <span className={isFaultDetected ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
              {isFaultDetected ? 'DETECTED' : 'QUIET'}
            </span>
          </p>
          <div className="text-[11px] text-slate-500 pt-2 border-t border-grid-800">
            Rf = {params.fault_resistance} Ω | Rg = {params.ground_resistance} Ω
          </div>
        </div>

        {/* Fault Onset Time */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-2">
          <span className="text-xs font-mono uppercase text-slate-400">Fault Inception Time</span>
          <div className="text-xl font-bold font-mono text-amber-300">
            {metrics.fault_onset_time ? `${metrics.fault_onset_time} s` : 'None (Healthy)'}
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Relay evaluated at t &gt; 0.15s
          </p>
          <div className="text-[11px] text-slate-500 pt-2 border-t border-grid-800">
            Trigger: Imag &gt; 10A or Vmag &lt; 100V
          </div>
        </div>

        {/* Breaker Trip Latency */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-2">
          <span className="text-xs font-mono uppercase text-slate-400">Fault-to-Trip Delay</span>
          <div className="text-xl font-bold font-mono text-rose-300">
            {metrics.fault_to_trip_delay_ms !== null ? `${metrics.fault_to_trip_delay_ms} ms` : '—'}
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Tripped at: {metrics.breaker_trip_time ? `${metrics.breaker_trip_time} s` : 'N/A'}
          </p>
          <div className="text-[11px] text-slate-500 pt-2 border-t border-grid-800">
            Breaker Duration: {metrics.trip_duration_ms ? `${metrics.trip_duration_ms} ms` : '—'}
          </div>
        </div>

        {/* Current Surge Ratio */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-2">
          <span className="text-xs font-mono uppercase text-slate-400">Current Disturbance</span>
          <div className="text-xl font-bold font-mono text-white">
            {metrics.max_disturbance_magnitude}x
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Peak: <span className="text-rose-400 font-bold">{metrics.peak_current} A</span>
          </p>
          <div className="text-[11px] text-slate-500 pt-2 border-t border-grid-800">
            Min Voltage: <span className="text-amber-400 font-bold">{metrics.min_voltage} V</span>
          </div>
        </div>
      </div>

      {/* Two Column Section: RMS Window Comparison & Relay Logic Sequence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RMS Window Stress Comparison */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span>Pre-Fault vs. Fault Interval True RMS Metrics</span>
          </h3>

          <div className="space-y-4 font-mono text-xs">
            {/* Voltage RMS Card */}
            <div className="p-4 rounded-xl bg-grid-950 border border-grid-800 space-y-3">
              <div className="flex items-center justify-between text-slate-400">
                <span>Phase Voltage (3-Phase Average RMS)</span>
                <span className="text-rose-400 font-semibold">{vDipPercent}% Dip</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-slate-500 block text-[10px]">Pre-Fault [0.05s-0.18s]</span>
                  <span className="text-base font-bold text-slate-200">
                    {metrics.rms_voltage_prefault} V
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px]">Fault [0.21s-0.38s]</span>
                  <span className="text-base font-bold text-rose-400">
                    {metrics.rms_voltage_fault} V
                  </span>
                </div>
              </div>
            </div>

            {/* Current RMS Card */}
            <div className="p-4 rounded-xl bg-grid-950 border border-grid-800 space-y-3">
              <div className="flex items-center justify-between text-slate-400">
                <span>Phase Current (3-Phase Average RMS)</span>
                <span className="text-amber-400 font-semibold">{iSurgeMultiplier}x Surge</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-slate-500 block text-[10px]">Pre-Fault [0.05s-0.18s]</span>
                  <span className="text-base font-bold text-slate-200">
                    {metrics.rms_current_prefault} A
                  </span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-600" />
                <div className="text-right">
                  <span className="text-slate-500 block text-[10px]">Fault [0.21s-0.38s]</span>
                  <span className="text-base font-bold text-amber-400">
                    {metrics.rms_current_fault} A
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Protection Sequence Architecture */}
        <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span>Simulink Protection Subsystem Logic Verification</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-grid-950 border border-grid-800 flex items-start space-x-3">
              <span className="w-6 h-6 rounded-full bg-grid-800 text-cyan-400 flex items-center justify-center font-mono font-bold shrink-0 text-xs">
                1
              </span>
              <div>
                <p className="font-semibold text-slate-200">Phasor Sequence Decomposition</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  <code className="text-cyan-400 font-mono">main_model/Signal Processing</code> decomposes 3-phase waveforms into positive-sequence magnitude <code className="text-slate-300 font-mono">Vmag</code> and <code className="text-slate-300 font-mono">Imag</code>.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-grid-950 border border-grid-800 flex items-start space-x-3">
              <span className="w-6 h-6 rounded-full bg-grid-800 text-cyan-400 flex items-center justify-center font-mono font-bold shrink-0 text-xs">
                2
              </span>
              <div>
                <p className="font-semibold text-slate-200">Fault Detection Logic (SID=29)</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Evaluates <code className="text-amber-400 font-mono">Fault = (Imag &gt; 10A OR Vmag &lt; 100V) AND (t &gt; 0.15s)</code>. Startup blanking eliminates generator sync false alarms.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-grid-950 border border-grid-800 flex items-start space-x-3">
              <span className="w-6 h-6 rounded-full bg-grid-800 text-cyan-400 flex items-center justify-center font-mono font-bold shrink-0 text-xs">
                3
              </span>
              <div>
                <p className="font-semibold text-slate-200">Latching S-R Flip-Flop & Breaker (SID=45, SID=3)</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Fault assertion sets S-R flip-flop <code className="text-rose-400 font-mono">Trip = 1</code>, actuating the breaker. The reset port clears latch at <code className="text-slate-300 font-mono">t = 0.40s</code>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
