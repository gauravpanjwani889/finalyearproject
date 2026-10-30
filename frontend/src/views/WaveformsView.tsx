import React, { useState, useMemo } from 'react';
import { SimulationResponse } from '../types';
import { WaveformChart, SeriesConfig } from '../components/WaveformChart';
import { TripBreakerChart } from '../components/TripBreakerChart';
import {
  LineChart,
  Layers,
  Zap,
  Activity,
  Gauge,
  Power,
  ShieldAlert,
  Download,
  Maximize2,
  Info,
  Radio,
  Sliders,
  ZoomIn,
} from 'lucide-react';

interface WaveformsViewProps {
  simulationResult: SimulationResponse | null;
}

type TimeWindow = 'all' | 'startup' | 'steady' | 'fault';

export const WaveformsView: React.FC<WaveformsViewProps> = ({
  simulationResult,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'voltages' | 'currents' | 'trip' | 'powers'>('all');
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('all');

  if (!simulationResult) {
    return (
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-12 text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-grid-800 border border-grid-700 flex items-center justify-center text-slate-500">
          <LineChart className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold text-white">No Simulation Results In Memory</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute a simulation from the Simulation Controls or click a quick scenario on the Overview page to generate authentic MATLAB waveforms.
        </p>
      </div>
    );
  }

  const { waveforms, metrics, units } = simulationResult;

  // Compute sliced arrays for High-Resolution Zoomed Views
  const { filteredIndices, windowLabel } = useMemo(() => {
    const rawT = waveforms.time;
    if (timeWindow === 'all') {
      return { filteredIndices: rawT.map((_, i) => i), windowLabel: 'Full Simulation [0.0s – 1.0s]' };
    }
    if (timeWindow === 'startup') {
      const idxs: number[] = [];
      rawT.forEach((t, i) => {
        if (t <= 0.155) idxs.push(i);
      });
      return { filteredIndices: idxs, windowLabel: 'Startup Dynamic Window [0.0s – 0.15s] (Rotor Sync & Inverter Energization)' };
    }
    if (timeWindow === 'steady') {
      const idxs: number[] = [];
      rawT.forEach((t, i) => {
        if (t >= 0.145 && t <= 0.205) idxs.push(i);
      });
      return { filteredIndices: idxs, windowLabel: 'Steady-State Pre-Fault Window [0.15s – 0.20s] (Pure 50 Hz Fundamental + PWM Harmonics)' };
    }
    // fault
    const idxs: number[] = [];
    rawT.forEach((t, i) => {
      if (t >= 0.18 && t <= 0.45) idxs.push(i);
    });
    return { filteredIndices: idxs, windowLabel: 'Fault & Circuit Breaker Actuation Window [0.18s – 0.45s]' };
  }, [timeWindow, waveforms.time]);

  // Sliced Waveforms
  const slicedTime = filteredIndices.map((i) => waveforms.time[i]);
  const slicedVa = filteredIndices.map((i) => waveforms.va[i]);
  const slicedVb = filteredIndices.map((i) => waveforms.vb[i]);
  const slicedVc = filteredIndices.map((i) => waveforms.vc[i]);
  const slicedIa = filteredIndices.map((i) => waveforms.ia[i]);
  const slicedIb = filteredIndices.map((i) => waveforms.ib[i]);
  const slicedIc = filteredIndices.map((i) => waveforms.ic[i]);
  const slicedTrip = filteredIndices.map((i) => waveforms.trip[i]);
  const slicedVmag = filteredIndices.map((i) => waveforms.vmag[i]);
  const slicedImag = filteredIndices.map((i) => waveforms.imag[i]);
  const slicedP = filteredIndices.map((i) => waveforms.p_active[i]);
  const slicedQ = filteredIndices.map((i) => waveforms.q_reactive[i]);

  const faultOnset = metrics.fault_onset_time;
  const tripTime = metrics.breaker_trip_time;

  // 1. Three-Phase Voltages (Va, Vb, Vc)
  const voltageSeries: SeriesConfig[] = [
    { name: 'Phase A (Va)', data: slicedVa, color: '#fbbf24', unit: 'V' },
    { name: 'Phase B (Vb)', data: slicedVb, color: '#34d399', unit: 'V' },
    { name: 'Phase C (Vc)', data: slicedVc, color: '#f43f5e', unit: 'V' },
  ];

  // 2. Three-Phase Currents (Ia, Ib, Ic)
  const currentSeries: SeriesConfig[] = [
    { name: 'Phase A (Ia)', data: slicedIa, color: '#fbbf24', unit: 'A' },
    { name: 'Phase B (Ib)', data: slicedIb, color: '#34d399', unit: 'A' },
    { name: 'Phase C (Ic)', data: slicedIc, color: '#f43f5e', unit: 'A' },
  ];

  // 3. Sequence Magnitudes (Vmag, Imag)
  const sequenceSeries: SeriesConfig[] = [
    { name: 'Sequence Voltage (Vmag)', data: slicedVmag, color: '#38bdf8', unit: 'V', yAxisIndex: 0 },
    { name: 'Sequence Current (Imag)', data: slicedImag, color: '#f97316', unit: 'A', yAxisIndex: 1 },
  ];

  // 4. Instantaneous Physical Powers
  const powerSeries: SeriesConfig[] = [
    { name: 'Active Power p(t)', data: slicedP, color: '#06b6d4', unit: 'kW', yAxisIndex: 0 },
    { name: 'Reactive Power q(t)', data: slicedQ, color: '#a855f7', unit: 'kVAR', yAxisIndex: 1 },
  ];

  // CSV Export
  const downloadCsv = () => {
    let csv = 'time_s,va_V,vb_V,vc_V,ia_A,ib_A,ic_A,trip,vmag_V,imag_A,p_active_kW,q_reactive_kVAR\n';
    for (let i = 0; i < waveforms.time.length; i++) {
      csv += `${waveforms.time[i]},${waveforms.va[i]},${waveforms.vb[i]},${waveforms.vc[i]},${waveforms.ia[i]},${waveforms.ib[i]},${waveforms.ic[i]},${waveforms.trip[i]},${waveforms.vmag[i]},${waveforms.imag[i]},${waveforms.p_active[i]},${waveforms.q_reactive[i]}\n`;
    }
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation_${simulationResult.params.fault_type}_${simulationResult.run_id.slice(0, 8)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Filter Tabs & Zoom Mode */}
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-4 lg:p-5 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                <LineChart className="w-5 h-5 text-cyan-400" />
                <span>Multi-Channel Waveform Explorer</span>
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {slicedTime.length} POINTS ({windowLabel})
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Authoritative 9-channel electrical waveforms extracted from Simulink <code className="text-cyan-400 font-mono">ScopeData</code>.
            </p>
          </div>

          {/* View Channels & CSV Download */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center space-x-1 bg-grid-950 p-1 rounded-xl border border-grid-800">
              {(['all', 'voltages', 'currents', 'trip', 'powers'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium capitalize transition-all ${
                    activeTab === tab
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            <button
              onClick={downloadCsv}
              className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-grid-800 hover:bg-grid-750 text-slate-200 border border-grid-700 text-xs font-mono transition-all"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* High-Resolution Time Zoom Window Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-grid-800/80">
          <div className="flex items-center space-x-2">
            <ZoomIn className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-semibold text-slate-300">Waveform Window:</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'all', label: 'Full View (0.0s – 1.0s)', desc: 'Complete 1-second simulation' },
              { id: 'startup', label: 'Startup Transient (0.0s – 0.15s)', desc: 'Rotor synchronization swing' },
              { id: 'steady', label: 'Steady-State Zoom (0.15s – 0.20s)', desc: 'High-res 50 Hz sinusoidal' },
              { id: 'fault', label: 'Fault & Breaker (0.18s – 0.45s)', desc: 'Fault onset and breaker trip' },
            ].map((mode) => (
              <button
                key={mode.id}
                onClick={() => setTimeWindow(mode.id as TimeWindow)}
                title={mode.desc}
                className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${
                  timeWindow === mode.id
                    ? 'bg-cyan-600 text-white font-bold shadow-md shadow-cyan-900/30'
                    : 'bg-grid-950/80 text-slate-400 hover:text-slate-200 border border-grid-800'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Measurement Location & Physical Distortion Physics Note */}
      <div className="p-4 rounded-xl bg-grid-900/90 border border-grid-800 text-xs text-slate-300 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2 font-semibold text-cyan-300">
            <Radio className="w-4 h-4" />
            <span>Measurement Location: Low-Voltage Inverter Terminal Bus (Three-Phase V-I Measurement SID=7)</span>
          </div>
          <div className="flex items-center space-x-3 text-[11px] font-mono">
            <span className="text-amber-400">Fundamental: {metrics.fundamental_voltage_rms.toFixed(1)} V RMS (50 Hz)</span>
            <span className="text-purple-400">THD: {metrics.thd_voltage_pct.toFixed(2)}% (2 kHz PWM carrier)</span>
          </div>
        </div>
        <p className="text-slate-400 leading-relaxed">
          <strong className="text-slate-200">Waveform Physics Explanation:</strong> The measured voltage waveform exhibits authentic physical high-frequency ripple because the measurement block is installed directly at the AC terminal of the <span className="text-cyan-400 font-mono">Series VSC 1</span> back-to-back converter operating at a <span className="text-purple-400 font-mono">2.0 kHz PWM carrier</span>. Furthermore, between <span className="text-amber-400 font-mono">0.0s and 0.15s</span>, the synchronous machine undergoes physical mechanical rotor acceleration and excitation stabilization. Switching to the <strong className="text-cyan-300 font-mono">"Steady-State Zoom [0.15s – 0.20s]"</strong> window isolates the pure balanced three-phase 50 Hz sinusoidal waveforms.
        </p>
      </div>

      {/* Waveform Charts Grid */}
      <div className="space-y-6">
        {/* 1. Dedicated Circuit Breaker Trip Graph */}
        {(activeTab === 'all' || activeTab === 'trip') && (
          <TripBreakerChart
            time={slicedTime}
            trip={slicedTrip}
            metrics={metrics}
            height={220}
          />
        )}

        {/* 2. Three-Phase Voltages */}
        {(activeTab === 'all' || activeTab === 'voltages') && (
          <WaveformChart
            title={`Three-Phase Line-to-Line Voltages (Va, Vb, Vc) [V] — ${windowLabel}`}
            time={slicedTime}
            series={voltageSeries}
            yAxisName="Voltage (V)"
            height={320}
            tripTime={tripTime}
            faultOnset={faultOnset}
          />
        )}

        {/* 3. Three-Phase Currents */}
        {(activeTab === 'all' || activeTab === 'currents') && (
          <WaveformChart
            title={`Three-Phase Line Currents (Ia, Ib, Ic) [A] — ${windowLabel}`}
            time={slicedTime}
            series={currentSeries}
            yAxisName="Current (A)"
            height={320}
            tripTime={tripTime}
            faultOnset={faultOnset}
          />
        )}

        {/* 4. Sequence Magnitudes */}
        {(activeTab === 'all' || activeTab === 'voltages' || activeTab === 'currents') && (
          <WaveformChart
            title={`Positive Sequence Phasor Magnitudes: Vmag & Imag — ${windowLabel}`}
            time={slicedTime}
            series={sequenceSeries}
            yAxisName="Vmag (V)"
            yAxisName2="Imag (A)"
            height={280}
            tripTime={tripTime}
            faultOnset={faultOnset}
          />
        )}

        {/* 5. Physical Instantaneous Powers */}
        {(activeTab === 'all' || activeTab === 'powers') && (
          <WaveformChart
            title={`Instantaneous 3-Phase Active Power p(t) & Clarke Reactive Power q(t) — ${windowLabel}`}
            time={slicedTime}
            series={powerSeries}
            yAxisName="Active P (kW)"
            yAxisName2="Reactive Q (kVAR)"
            height={280}
            tripTime={tripTime}
            faultOnset={faultOnset}
          />
        )}
      </div>
    </div>
  );
};

