import React, { useState } from 'react';
import { FaultType, SimulationParams, ParameterLimits, SimulationResponse } from '../types';
import {
  Sliders,
  Play,
  RotateCcw,
  Zap,
  ShieldAlert,
  HelpCircle,
  Cpu,
  Clock,
  Sparkles,
  AlertTriangle,
  Network,
  Activity,
  CheckCircle2,
  Lock,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface ControlsViewProps {
  params: SimulationParams;
  setParams: React.Dispatch<React.SetStateAction<SimulationParams>>;
  onRunSimulation: () => void;
  isRunning: boolean;
  runStatus: string;
  elapsedSec: number;
  parameterLimits: ParameterLimits | null;
  lastResponse?: SimulationResponse | null;
}

export const ControlsView: React.FC<ControlsViewProps> = ({
  params,
  setParams,
  onRunSimulation,
  isRunning,
  runStatus,
  elapsedSec,
  parameterLimits,
  lastResponse,
}) => {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedNetworkMode, setSelectedNetworkMode] = useState<'mode1' | 'mode2'>('mode1');
  const [activeTab, setActiveTab] = useState<'faults' | 'generator' | 'transformer' | 'load' | 'line'>('faults');

  const faultCategories = {
    symmetrical: [
      { type: 'NORMAL' as FaultType, label: 'NORMAL (Healthy Grid)', desc: 'Nominal operation without fault injection' },
      { type: 'ABC' as FaultType, label: 'ABC (3-Phase Symmetrical)', desc: 'Balanced 3-phase fault without ground' },
      { type: 'ABCG' as FaultType, label: 'ABCG (3-Phase Ground)', desc: 'Symmetrical 3-phase short to ground' },
    ],
    slg: [
      { type: 'AG' as FaultType, label: 'AG (Single Line-to-Ground)', desc: 'Phase A shorted to earth ground' },
      { type: 'BG' as FaultType, label: 'BG (Single Line-to-Ground)', desc: 'Phase B shorted to earth ground' },
      { type: 'CG' as FaultType, label: 'CG (Single Line-to-Ground)', desc: 'Phase C shorted to earth ground' },
    ],
    ll: [
      { type: 'AB' as FaultType, label: 'AB (Line-to-Line)', desc: 'Phase A shorted to Phase B' },
      { type: 'BC' as FaultType, label: 'BC (Line-to-Line)', desc: 'Phase B shorted to Phase C' },
      { type: 'CA' as FaultType, label: 'CA (Line-to-Line)', desc: 'Phase C shorted to Phase A' },
    ],
    dlg: [
      { type: 'ABG' as FaultType, label: 'ABG (Double Line-to-Ground)', desc: 'Phases A & B shorted to earth ground' },
      { type: 'BCG' as FaultType, label: 'BCG (Double Line-to-Ground)', desc: 'Phases B & C shorted to earth ground' },
      { type: 'CAG' as FaultType, label: 'CAG (Double Line-to-Ground)', desc: 'Phases C & A shorted to earth ground' },
    ],
  };

  // Quick Presets
  const applyPreset = (presetName: string) => {
    if (presetName === 'healthy') {
      setParams((prev) => ({
        ...prev,
        fault_type: 'NORMAL',
        fault_resistance: 0.001,
        ground_resistance: 0.01,
        gen_rated_mva: 10.0,
        gen_rated_kv: 11.0,
        gen_field_voltage_pu: 1.0,
        gen_mech_power_pu: 1.0,
        trafo_rated_mva: 5.0,
        trafo_primary_kv: 11.0,
        trafo_secondary_v: 415.0,
        load_active_power_mw: 500.0,
        load_power_factor: 1.0,
        load_reactive_power_mvar: 0.0,
        line_resistance: 0.001,
        line_inductance: 0.001,
        line_capacitance: 1e-6,
        pi_line_length_km: 100.0,
      }));
    } else if (presetName === 'bolted_ag') {
      setParams((prev) => ({
        ...prev,
        fault_type: 'AG',
        fault_resistance: 0.001,
        ground_resistance: 0.01,
      }));
    } else if (presetName === 'heavy_load_lagging') {
      setParams((prev) => ({
        ...prev,
        load_active_power_mw: 800.0,
        load_power_factor: 0.85,
      }));
    } else if (presetName === 'bolted_abc') {
      setParams((prev) => ({
        ...prev,
        fault_type: 'ABC',
        fault_resistance: 0.001,
        ground_resistance: 0.01,
      }));
    }
  };

  // Dynamic calculation of reactive power from active power and power factor
  const computedReactivePowerMvar = React.useMemo(() => {
    const p = params.load_active_power_mw ?? 500.0;
    const pf = params.load_power_factor ?? 1.0;
    if (pf >= 0.999) return params.load_reactive_power_mvar ?? 0.0;
    const phi = Math.acos(Math.max(0.1, Math.min(1.0, pf)));
    return Math.round(p * Math.tan(phi) * 100) / 100;
  }, [params.load_active_power_mw, params.load_power_factor, params.load_reactive_power_mvar]);

  const handleRun = () => {
    if (selectedNetworkMode === 'mode2') {
      setErrorMsg('Mode 2 (MATPOWER Power Flow) is disabled. MATPOWER is not installed on this MATLAB engine.');
      return;
    }
    if (params.fault_resistance <= 0 || params.ground_resistance <= 0) {
      setErrorMsg('Fault and ground resistances must be strictly positive.');
      return;
    }
    if ((params.fault_start_time ?? 0.2) >= (params.fault_stop_time ?? 0.4)) {
      setErrorMsg('Fault inception time must precede fault clearing time.');
      return;
    }
    setErrorMsg(null);
    onRunSimulation();
  };

  return (
    <div className="space-y-6">
      {/* SECTION 1: Network & Simulation Mode Selection */}
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
              <Network className="w-4 h-4 text-cyan-400" />
              <span>Section 1 — Network Architecture & Simulation Mode</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Select simulation solver framework. Dynamic transients run on Simulink; steady-state power flow requires MATPOWER.
            </p>
          </div>

          {/* Quick Presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono text-slate-400 flex items-center mr-1">
              <Sparkles className="w-3 h-3 text-amber-400 mr-1" /> Presets:
            </span>
            <button
              onClick={() => applyPreset('healthy')}
              className="px-2.5 py-1 rounded-lg bg-grid-800 hover:bg-grid-700 text-xs font-mono text-emerald-300 border border-emerald-500/30 transition-all"
            >
              Default Baseline
            </button>
            <button
              onClick={() => applyPreset('bolted_ag')}
              className="px-2.5 py-1 rounded-lg bg-grid-800 hover:bg-grid-700 text-xs font-mono text-amber-300 border border-amber-500/30 transition-all"
            >
              Bolted AG
            </button>
            <button
              onClick={() => applyPreset('heavy_load_lagging')}
              className="px-2.5 py-1 rounded-lg bg-grid-800 hover:bg-grid-700 text-xs font-mono text-purple-300 border border-purple-500/30 transition-all"
            >
              800MW / 0.85 PF
            </button>
            <button
              onClick={() => applyPreset('bolted_abc')}
              className="px-2.5 py-1 rounded-lg bg-grid-800 hover:bg-grid-700 text-xs font-mono text-rose-300 border border-rose-500/30 transition-all"
            >
              Symmetrical ABC
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Mode 1: Dynamic Fault Simulation (ACTIVE) */}
          <div
            onClick={() => setSelectedNetworkMode('mode1')}
            className={`cursor-pointer rounded-xl p-4 border transition-all ${
              selectedNetworkMode === 'mode1'
                ? 'bg-cyan-500/15 border-cyan-500/60 shadow-lg shadow-cyan-500/10 ring-1 ring-cyan-500/40'
                : 'bg-grid-850 border-grid-800 hover:border-grid-700'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                <span className="font-bold text-sm text-cyan-300">Mode 1 — Dynamic Fault Simulation</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                ACTIVE SOLVER
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Executes high-fidelity transient simulation on <code className="text-cyan-300 font-mono">matlab/main_model.slx</code>. Models synchronous generator dynamics, transformer saturation, 2 kHz PWM converter switching, and protection relay breaker actuation.
            </p>
            <div className="mt-3 pt-2 border-t border-grid-750/60 flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Model: main_model.slx</span>
              <span>Discrete T<sub>s</sub> = 50 µs</span>
            </div>
          </div>

          {/* Mode 2: MATPOWER IEEE Benchmark (PLANNED / DISABLED) */}
          <div
            onClick={() => setSelectedNetworkMode('mode2')}
            className={`cursor-pointer rounded-xl p-4 border transition-all relative overflow-hidden ${
              selectedNetworkMode === 'mode2'
                ? 'bg-rose-500/10 border-rose-500/40'
                : 'bg-grid-950/60 border-grid-800/80 opacity-75 hover:opacity-90'
            }`}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center space-x-2">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span className="font-bold text-sm text-slate-300">Mode 2 — IEEE Benchmark Power Flow</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                NOT INSTALLED
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Planned steady-state AC/DC power flow for IEEE 57-bus, 118-bus, and 300-bus grids via MATPOWER.
            </p>
            <div className="mt-2.5 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 font-mono">
              <strong>Technical Audit Note:</strong> MATPOWER functions (<code className="text-amber-200">runpf</code>, <code className="text-amber-200">case118</code>) were audited and verified missing from the MATLAB installation path. Steady-state bus flow cannot be simulated until MATPOWER is installed. Dynamic transient modeling on 118 buses requires a separate dynamic network model.
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Navigation Tabs for Configuration Sections */}
      <div className="flex items-center space-x-2 border-b border-grid-800 pb-2">
        {[
          { id: 'faults', label: 'Fault Configuration (12 Scenarios)' },
          { id: 'generator', label: 'Generator Controls' },
          { id: 'transformer', label: 'Transformer Controls' },
          { id: 'load', label: 'Load & Power Factor' },
          { id: 'line', label: 'Transmission Line' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                : 'text-slate-400 hover:text-slate-200 bg-grid-900 border border-grid-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Configuration Columns (2 Cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* TAB 1: FAULTS CONFIGURATION */}
          {activeTab === 'faults' && (
            <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-cyan-400" />
                  <span>Section 6 — Supported Fault Scenarios & Switching Timing</span>
                </h3>
                <span className="text-xs font-mono text-cyan-400">12 Verified Scenarios</span>
              </div>

              {/* Categorized Grid */}
              <div className="space-y-4">
                {/* Symmetrical */}
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2">
                    Symmetrical Three-Phase & Healthy Operation
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {faultCategories.symmetrical.map((opt) => (
                      <div
                        key={opt.type}
                        onClick={() => setParams((p) => ({ ...p, fault_type: opt.type }))}
                        className={`cursor-pointer rounded-xl p-3 border text-xs transition-all ${
                          params.fault_type === opt.type
                            ? 'bg-cyan-500/15 border-cyan-500/60 font-semibold text-cyan-200 shadow-sm'
                            : 'bg-grid-850 border-grid-800 hover:border-grid-700 text-slate-300'
                        }`}
                      >
                        <div className="font-bold mb-0.5">{opt.label}</div>
                        <div className="text-[10px] text-slate-400">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Single Line-to-Ground */}
                <div>
                  <div className="text-[11px] font-mono text-amber-400 uppercase tracking-wider mb-2">
                    Single Line-to-Ground Faults (SLG)
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {faultCategories.slg.map((opt) => (
                      <div
                        key={opt.type}
                        onClick={() => setParams((p) => ({ ...p, fault_type: opt.type }))}
                        className={`cursor-pointer rounded-xl p-3 border text-xs transition-all ${
                          params.fault_type === opt.type
                            ? 'bg-amber-500/15 border-amber-500/60 font-semibold text-amber-200 shadow-sm'
                            : 'bg-grid-850 border-grid-800 hover:border-grid-700 text-slate-300'
                        }`}
                      >
                        <div className="font-bold mb-0.5">{opt.label}</div>
                        <div className="text-[10px] text-slate-400">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Line-to-Line */}
                <div>
                  <div className="text-[11px] font-mono text-orange-400 uppercase tracking-wider mb-2">
                    Line-to-Line Faults (LL)
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {faultCategories.ll.map((opt) => (
                      <div
                        key={opt.type}
                        onClick={() => setParams((p) => ({ ...p, fault_type: opt.type }))}
                        className={`cursor-pointer rounded-xl p-3 border text-xs transition-all ${
                          params.fault_type === opt.type
                            ? 'bg-orange-500/15 border-orange-500/60 font-semibold text-orange-200 shadow-sm'
                            : 'bg-grid-850 border-grid-800 hover:border-grid-700 text-slate-300'
                        }`}
                      >
                        <div className="font-bold mb-0.5">{opt.label}</div>
                        <div className="text-[10px] text-slate-400">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Double Line-to-Ground */}
                <div>
                  <div className="text-[11px] font-mono text-rose-400 uppercase tracking-wider mb-2">
                    Double Line-to-Ground Faults (DLG)
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {faultCategories.dlg.map((opt) => (
                      <div
                        key={opt.type}
                        onClick={() => setParams((p) => ({ ...p, fault_type: opt.type }))}
                        className={`cursor-pointer rounded-xl p-3 border text-xs transition-all ${
                          params.fault_type === opt.type
                            ? 'bg-rose-500/15 border-rose-500/60 font-semibold text-rose-200 shadow-sm'
                            : 'bg-grid-850 border-grid-800 hover:border-grid-700 text-slate-300'
                        }`}
                      >
                        <div className="font-bold mb-0.5">{opt.label}</div>
                        <div className="text-[10px] text-slate-400">{opt.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Fault Impedance & Timing Controls */}
              <div className="pt-4 border-t border-grid-800 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Fault Resistance R<sub>f</sub> (Ω)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.0001"
                    max="100"
                    value={params.fault_resistance}
                    onChange={(e) => setParams((p) => ({ ...p, fault_resistance: parseFloat(e.target.value) || 0.001 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">Range: 0.0001 – 100 Ω</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Ground Resistance R<sub>g</sub> (Ω)</label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.0001"
                    max="100"
                    value={params.ground_resistance}
                    onChange={(e) => setParams((p) => ({ ...p, ground_resistance: parseFloat(e.target.value) || 0.01 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">For AG, BG, CG, DLG</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Fault Inception t<sub>start</sub> (s)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.15"
                    max="0.8"
                    value={params.fault_start_time ?? 0.2}
                    onChange={(e) => setParams((p) => ({ ...p, fault_start_time: parseFloat(e.target.value) || 0.2 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">&ge; 0.15s (after startup)</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Fault Clearing t<sub>stop</sub> (s)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.2"
                    max="0.95"
                    value={params.fault_stop_time ?? 0.4}
                    onChange={(e) => setParams((p) => ({ ...p, fault_stop_time: parseFloat(e.target.value) || 0.4 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">Breaker reset time</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: GENERATOR CONTROLS */}
          {activeTab === 'generator' && (
            <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span>Section 2 — Synchronous Machine & Excitation Settings</span>
              </h3>
              <p className="text-xs text-slate-400">
                Maps directly to <code className="text-cyan-400 font-mono">main_model/Synchronous Machine pu Standard</code> (SID=100) and excitation source blocks.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Rated Apparent Power (MVA)</label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    max="100"
                    value={params.gen_rated_mva ?? 10.0}
                    onChange={(e) => setParams((p) => ({ ...p, gen_rated_mva: parseFloat(e.target.value) || 10.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">Simulink base MVA [Default: 10.0 MVA]</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Rated Line Voltage (kV)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="33"
                    value={params.gen_rated_kv ?? 11.0}
                    onChange={(e) => setParams((p) => ({ ...p, gen_rated_kv: parseFloat(e.target.value) || 11.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">Stator rating [Default: 11.0 kV]</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Field Excitation Setpoint V<sub>f</sub> (pu)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.5"
                    max="1.5"
                    value={params.gen_field_voltage_pu ?? 1.0}
                    onChange={(e) => setParams((p) => ({ ...p, gen_field_voltage_pu: parseFloat(e.target.value) || 1.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">Maps to main_model/Constant1 (Vf) [Default: 1.0 pu]</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Mechanical Turbine Power P<sub>m</sub> (pu)</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.1"
                    max="1.5"
                    value={params.gen_mech_power_pu ?? 1.0}
                    onChange={(e) => setParams((p) => ({ ...p, gen_mech_power_pu: parseFloat(e.target.value) || 1.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">Maps to main_model/Constant (Pm) [Default: 1.0 pu]</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: TRANSFORMER CONTROLS */}
          {activeTab === 'transformer' && (
            <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span>Section 3 — Three-Phase Step-Down Transformer Settings</span>
              </h3>
              <p className="text-xs text-slate-400">
                Maps to <code className="text-cyan-400 font-mono">main_model/Three-Phase Transformer (Two Windings)</code> (SID=101).
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Nominal Power (MVA)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="50"
                    value={params.trafo_rated_mva ?? 5.0}
                    onChange={(e) => setParams((p) => ({ ...p, trafo_rated_mva: parseFloat(e.target.value) || 5.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">[Default: 5.0 MVA]</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Primary Winding (kV)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="33"
                    value={params.trafo_primary_kv ?? 11.0}
                    onChange={(e) => setParams((p) => ({ ...p, trafo_primary_kv: parseFloat(e.target.value) || 11.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">HV Side [Default: 11.0 kV]</span>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Secondary Winding (V)</label>
                  <input
                    type="number"
                    step="5"
                    min="100"
                    max="11000"
                    value={params.trafo_secondary_v ?? 415.0}
                    onChange={(e) => setParams((p) => ({ ...p, trafo_secondary_v: parseFloat(e.target.value) || 415.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">LV Side [Default: 415.0 V]</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: LOAD & POWER FACTOR */}
          {activeTab === 'load' && (
            <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Section 4 — Parallel RLC Load & Power Factor Controls</span>
              </h3>
              <p className="text-xs text-slate-400">
                Maps to <code className="text-cyan-400 font-mono">main_model/Three-Phase Parallel RLC Load</code> (SID=114).
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-mono text-slate-300">Active Load Demand P (MW)</label>
                  <input
                    type="number"
                    step="10"
                    min="0.1"
                    max="2000"
                    value={params.load_active_power_mw ?? 500.0}
                    onChange={(e) => setParams((p) => ({ ...p, load_active_power_mw: parseFloat(e.target.value) || 500.0 }))}
                    className="w-full px-3 py-2 rounded-xl bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[11px] text-slate-500">Three-phase active power demand</span>
                </div>

                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-300">Operational Power Factor (cos φ)</span>
                    <span className="text-cyan-400 font-bold">{params.load_power_factor ?? 1.0}</span>
                  </div>
                  <input
                    type="range"
                    min="0.50"
                    max="1.00"
                    step="0.01"
                    value={params.load_power_factor ?? 1.0}
                    onChange={(e) => setParams((p) => ({ ...p, load_power_factor: parseFloat(e.target.value) || 1.0 }))}
                    className="w-full accent-cyan-400 cursor-pointer"
                  />
                  <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>0.50 Lagging</span>
                    <span>Unity (1.00)</span>
                  </div>
                </div>
              </div>

              {/* Physical Power Factor Formula Card */}
              <div className="p-3 rounded-xl bg-grid-950 border border-grid-800 text-xs font-mono text-slate-300 flex items-center justify-between">
                <div>
                  <span className="text-slate-400">Derived Reactive Demand Q = P · tan(arccos(pf)):</span>
                  <div className="text-purple-400 font-bold text-sm mt-0.5">
                    {computedReactivePowerMvar} MVAR (Inductive)
                  </div>
                </div>
                <div className="text-right text-[11px] text-slate-400">
                  <span>Apparent S = </span>
                  <span className="text-cyan-300 font-bold">
                    {Math.round(Math.sqrt((params.load_active_power_mw ?? 500)**2 + computedReactivePowerMvar**2))} MVA
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: TRANSMISSION LINE */}
          {activeTab === 'line' && (
            <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                <span>Section 5 — Transmission Line Series Branch & Distributed PI Section</span>
              </h3>

              <div className="p-3 rounded-xl bg-grid-950 border border-grid-800 text-xs text-slate-400 leading-relaxed">
                <strong className="text-cyan-300">Physical Topology Distinction: </strong>
                The <code className="text-cyan-400 font-mono">Series RLC Branch (SID=2)</code> represents lumped line impedance between the step-down transformer and VSC bus. The <code className="text-purple-400 font-mono">PI Section Line (SID=4)</code> represents the distributed 100 km transmission corridor.
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Series Resistance R (Ω)</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0.0001"
                    max="10"
                    value={params.line_resistance ?? 0.001}
                    onChange={(e) => setParams((p) => ({ ...p, line_resistance: parseFloat(e.target.value) || 0.001 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">SID=2</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Series Inductance L (H)</label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0.00001"
                    max="0.1"
                    value={params.line_inductance ?? 0.001}
                    onChange={(e) => setParams((p) => ({ ...p, line_inductance: parseFloat(e.target.value) || 0.001 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">SID=2</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">Series Capacitance C (F)</label>
                  <input
                    type="number"
                    step="1e-7"
                    min="1e-9"
                    max="1e-3"
                    value={params.line_capacitance ?? 1e-6}
                    onChange={(e) => setParams((p) => ({ ...p, line_capacitance: parseFloat(e.target.value) || 1e-6 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-slate-500">SID=2</span>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-mono text-slate-300">PI Feeder Length (km)</label>
                  <input
                    type="number"
                    step="10"
                    min="1"
                    max="500"
                    value={params.pi_line_length_km ?? 100.0}
                    onChange={(e) => setParams((p) => ({ ...p, pi_line_length_km: parseFloat(e.target.value) || 100.0 }))}
                    className="w-full px-2.5 py-1.5 rounded-lg bg-grid-950 border border-grid-750 font-mono text-xs text-white"
                  />
                  <span className="text-[10px] text-purple-400">SID=4 (PI Line)</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* SECTION 7: SIMULATION EXECUTION & READBACK VERIFICATION (1 Col) */}
        <div className="space-y-6">
          <div className="bg-grid-900 border border-cyan-500/30 rounded-2xl p-5 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none" />

            <h3 className="text-sm font-semibold text-white flex items-center space-x-2 mb-3">
              <Play className="w-4 h-4 text-cyan-400 fill-current" />
              <span>Section 7 — Simulation Execution</span>
            </h3>

            <p className="text-xs text-slate-400 mb-4">
              Dispatches authenticated parameters to MATLAB, sets Simulink block parameters, executes solver, and verifies parameters via readback.
            </p>

            {/* Run Button */}
            <button
              onClick={handleRun}
              disabled={isRunning}
              className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm tracking-wide flex items-center justify-center space-x-2 transition-all shadow-lg ${
                isRunning
                  ? 'bg-amber-500/20 border border-amber-500/40 text-amber-300 cursor-not-allowed'
                  : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 shadow-cyan-500/25 active:scale-[0.99]'
              }`}
            >
              {isRunning ? (
                <>
                  <div className="w-4 h-4 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
                  <span>Solving Transient ({elapsedSec}s)...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>RUN MATLAB SIMULATION</span>
                </>
              )}
            </button>

            {/* Live Progress */}
            {isRunning && (
              <div className="mt-4 p-3 rounded-xl bg-grid-950 border border-amber-500/30 space-y-2 animate-in fade-in">
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-amber-400 flex items-center">
                    <Clock className="w-3.5 h-3.5 mr-1 animate-spin" />
                    Solver Active
                  </span>
                  <span className="text-slate-300 font-bold">{elapsedSec}s elapsed</span>
                </div>
                <p className="text-[11px] text-slate-400 font-mono">{runStatus}</p>
                <div className="w-full bg-grid-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-amber-400 h-1.5 rounded-full transition-all duration-300 animate-pulse"
                    style={{ width: `${Math.min(95, elapsedSec * 3)}%` }}
                  />
                </div>
              </div>
            )}

            {/* Telemetry Downsampling Option */}
            <div className="mt-5 pt-4 border-t border-grid-800 space-y-2">
              <label className="text-xs font-mono text-slate-300 flex items-center justify-between">
                <span>Decimated Points</span>
                <span className="text-cyan-400 font-bold">{params.downsample_points} pts</span>
              </label>
              <input
                type="range"
                min="200"
                max="2000"
                step="100"
                value={params.downsample_points}
                onChange={(e) =>
                  setParams((p) => ({ ...p, downsample_points: parseInt(e.target.value) || 1000 }))
                }
                className="w-full accent-cyan-400 cursor-pointer"
              />
              <p className="text-[10px] text-slate-500">
                Multi-phase peak-preserving decimation guarantees trip signal and phase symmetry are preserved.
              </p>
            </div>
          </div>

          {/* Parameter Readback Verification Display */}
          {lastResponse && lastResponse.readback_parameters && (
            <div className="bg-grid-900 border border-emerald-500/30 rounded-2xl p-4 shadow-xl space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold text-emerald-400">
                <CheckCircle2 className="w-4 h-4" />
                <span>Simulink Readback Verification</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-tight">
                Parameters below were read back directly from Simulink blocks using <code className="text-cyan-300 font-mono">get_param</code> after write.
              </p>
              <div className="max-h-48 overflow-y-auto space-y-1 font-mono text-[10px] text-slate-300 bg-grid-950 p-2 rounded-xl border border-grid-800">
                {Object.entries(lastResponse.readback_parameters).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between py-0.5 border-b border-grid-900">
                    <span className="text-slate-400 truncate max-w-[130px]">{key}:</span>
                    <span className="text-emerald-300 font-bold">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

