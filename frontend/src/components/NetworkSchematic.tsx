import React, { useState } from 'react';
import { SimulationResponse, FaultType } from '../types';
import { Zap, ShieldAlert, CheckCircle2, AlertOctagon, Info } from 'lucide-react';

interface NetworkSchematicProps {
  simulationResult: SimulationResponse | null;
  configuredFaultType?: FaultType;
}

export const NetworkSchematic: React.FC<NetworkSchematicProps> = ({
  simulationResult,
  configuredFaultType = 'NORMAL',
}) => {
  const [selectedBlock, setSelectedBlock] = useState<string | null>(null);

  const faultType = simulationResult?.params?.fault_type || configuredFaultType;
  const isTripped = simulationResult?.metrics?.is_breaker_tripped ?? false;
  const isFaulted = simulationResult?.metrics?.is_fault_detected ?? (faultType !== 'NORMAL');
  const tripTime = simulationResult?.metrics?.breaker_trip_time;
  const faultOnset = simulationResult?.metrics?.fault_onset_time;

  const blocksInfo: Record<string, { title: string; sid: string; desc: string; params: string[] }> = {
    generator: {
      title: 'Synchronous Machine',
      sid: 'SID=100 (spsSynchronousMachinepuStandardLib)',
      desc: 'Salient-pole machine serving as grid primary power generation source.',
      params: ['Nominal: 10 MVA, 11 kV, 50 Hz', 'R_s: 0.037875 pu, Pole Pairs: 20', 'P_mech: 1.0 pu, V_field: 1.0 pu'],
    },
    transformer: {
      title: 'Three-Phase Transformer',
      sid: 'SID=101 (spsThreePhaseTransformerTwoWindingsLib)',
      desc: 'Step-down substation transformer feeding the transmission corridor.',
      params: ['Nominal Power: 5 MVA, 50 Hz', 'Primary: 11 kV (Yg), R=0.002 pu, L=0.08 pu', 'Secondary: 415 V (Yg), R=0.002 pu, L=0.08 pu'],
    },
    series_rlc: {
      title: 'Series RLC Branch',
      sid: 'SID=2 (spsThreePhaseSeriesRLCBranchLib)',
      desc: 'Configurable line series impedance block.',
      params: [
        `Resistance R: ${simulationResult?.params?.line_resistance ?? 0.001} Ω`,
        `Inductance L: ${simulationResult?.params?.line_inductance ?? 0.001} H`,
        `Capacitance C: ${simulationResult?.params?.line_capacitance ?? 1e-6} F`,
      ],
    },
    vsc: {
      title: 'Series VSC Inverters (Back-to-Back)',
      sid: 'SID=179 & SID=180 (Universal Bridge IGBT/Diodes)',
      desc: 'Power electronics converters with DC-link capacitor and 2 kHz PWM carrier.',
      params: ['Device: IGBT/Diodes, 3 Arms', 'DC-Link Capacitor: 1 μF', 'Carrier Period: 500 μs (2 kHz PWM)'],
    },
    breaker: {
      title: 'Three-Phase Circuit Breaker',
      sid: 'SID=3 (spsThreePhaseBreakerLib)',
      desc: 'Protective isolation breaker commanded by S-R Flip-Flop relay logic.',
      params: [
        `State: ${isTripped ? 'OPEN / TRIPPED (Trip=1)' : 'CLOSED / NORMAL (Trip=0)'}`,
        `Actuation Time: ${tripTime ? `${tripTime} s` : 'N/A'}`,
        'R_on: 0.001 Ω, Snubber: 1 MΩ',
      ],
    },
    fault: {
      title: 'Three-Phase Fault Ingestion Block',
      sid: 'SID=6 (spsThreePhaseFaultLib)',
      desc: 'Programmatic short-circuit injector targeting phases A, B, C and Ground.',
      params: [
        `Selected Scenario: ${faultType}`,
        `Fault Resistance Rf: ${simulationResult?.params?.fault_resistance ?? 0.001} Ω`,
        `Ground Resistance Rg: ${simulationResult?.params?.ground_resistance ?? 0.01} Ω`,
        'Switching Time Interval: [0.20 s, 0.40 s]',
      ],
    },
    line: {
      title: 'Transmission Line (PI Section)',
      sid: 'SID=4 (spsThreePhasePISectionLineLib)',
      desc: 'Distributed parameter transmission corridor connecting substation to load.',
      params: ['Length: 100 km, Frequency: 50 Hz', 'R: [0.01273, 0.3864] Ω/km', 'L: [0.9337, 4.1264] mH/km', 'C: [12.74, 7.751] nF/km'],
    },
    load: {
      title: 'Three-Phase Parallel RLC Load',
      sid: 'SID=114 (spsThreePhaseParallelRLCLoadLib)',
      desc: 'Primary industrial load center.',
      params: ['Nominal Voltage: 11 kV, 50 Hz', 'Active Power: 500 MW (Constant Z)'],
    },
    protection: {
      title: 'Protection & Relay Subsystem',
      sid: 'SID=29, SID=45, SID=79 (Sequence Analyzer & S-R Latch)',
      desc: 'Dual-threshold protection relay monitoring positive sequence phasors.',
      params: [
        'Overcurrent Threshold: Imag > 10.0 A',
        'Undervoltage Threshold: Vmag < 100.0 V',
        'Startup Blanking Gating: t > 0.15 s',
        `Fault Inception Detected: ${faultOnset ? `${faultOnset} s` : 'None'}`,
      ],
    },
  };

  return (
    <div className="bg-grid-900 border border-grid-800 rounded-2xl p-4 lg:p-6 shadow-2xl relative">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-base font-semibold text-white flex items-center space-x-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <span>Simulink Authoritative Grid Topology</span>
            <span className="text-xs font-mono font-normal text-slate-400">
              (main_model.slx / 73 Blocks)
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Interactive single-line electrical topology representing the genuine Simscape Specialized Power Systems model.
          </p>
        </div>

        {/* Live Status Tag */}
        <div className="flex items-center space-x-2">
          {isTripped ? (
            <span className="flex items-center space-x-1 px-3 py-1 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-400 text-xs font-mono font-medium animate-pulse">
              <AlertOctagon className="w-3.5 h-3.5" />
              <span>BREAKER TRIPPED (OPEN)</span>
            </span>
          ) : isFaulted ? (
            <span className="flex items-center space-x-1 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-400 text-xs font-mono font-medium">
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>FAULT DETECTED ({faultType})</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>GRID NORMAL (HEALTHY)</span>
            </span>
          )}
        </div>
      </div>

      {/* SVG Single-Line Schematic */}
      <div className="w-full overflow-x-auto bg-grid-950/80 rounded-xl border border-grid-800/80 p-4">
        <svg
          viewBox="0 0 980 260"
          className="w-full min-w-[850px] h-auto select-none font-sans"
        >
          <defs>
            {/* Linear Gradients */}
            <linearGradient id="busGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00f0ff" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.8" />
            </linearGradient>
            <linearGradient id="faultGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ff0055" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.9" />
            </linearGradient>
          </defs>

          {/* Background grid markings */}
          <pattern id="gridPattern" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#16233b" strokeWidth="0.5" />
          </pattern>
          <rect width="980" height="260" fill="url(#gridPattern)" rx="10" />

          {/* Main Power Transmission Trunk Lines */}
          <line x1="85" y1="120" x2="180" y2="120" stroke="#00f0ff" strokeWidth="3" strokeDasharray={isTripped ? "4,4" : "none"} />
          <line x1="230" y1="120" x2="310" y2="120" stroke="#00f0ff" strokeWidth="3" />
          <line x1="360" y1="120" x2="430" y2="120" stroke="#00f0ff" strokeWidth="3" />
          
          {/* Circuit Breaker Section */}
          <line x1="430" y1="120" x2="475" y2="120" stroke={isTripped ? "#ef4444" : "#00f0ff"} strokeWidth="3" />
          <line x1="535" y1="120" x2="620" y2="120" stroke={isTripped ? "#ef4444" : "#00f0ff"} strokeWidth="3" />
          
          {/* Downstream Transmission Line & Load */}
          <line x1="680" y1="120" x2="770" y2="120" stroke="#00f0ff" strokeWidth="3" />
          <line x1="830" y1="120" x2="900" y2="120" stroke="#00f0ff" strokeWidth="3" />

          {/* Fault Branch Drop Line */}
          <line x1="725" y1="120" x2="725" y2="180" stroke={isFaulted ? "#ff0055" : "#475569"} strokeWidth="2.5" strokeDasharray="3,3" />

          {/* 1. Synchronous Generator (SID=100) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('generator')}
          >
            <circle cx="55" cy="120" r="30" fill="#0f172a" stroke="#00f0ff" strokeWidth="2.5" />
            <text x="55" y="117" textAnchor="middle" fill="#00f0ff" fontSize="13" fontWeight="bold">GEN</text>
            <text x="55" y="132" textAnchor="middle" fill="#94a3b8" fontSize="10" fontFamily="monospace">11 kV</text>
            <text x="55" y="165" textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="600">Sync Machine</text>
            <text x="55" y="178" textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">10 MVA</text>
          </g>

          {/* 2. Step-Down Transformer (SID=101) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('transformer')}
          >
            <circle cx="195" cy="120" r="16" fill="none" stroke="#38bdf8" strokeWidth="2.5" />
            <circle cx="215" cy="120" r="16" fill="none" stroke="#38bdf8" strokeWidth="2.5" />
            <text x="205" y="152" textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="600">Transformer</text>
            <text x="205" y="165" textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">11kV / 415V</text>
          </g>

          {/* 3. Series RLC Branch (SID=2) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('series_rlc')}
          >
            <rect x="310" y="105" width="50" height="30" rx="6" fill="#0f172a" stroke="#818cf8" strokeWidth="2" />
            <text x="335" y="124" textAnchor="middle" fill="#818cf8" fontSize="11" fontWeight="bold">R-L-C</text>
            <text x="335" y="152" textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="600">Series Line</text>
            <text x="335" y="165" textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">Branch</text>
          </g>

          {/* 4. Dual Series VSC Inverters (SID=179, SID=180) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('vsc')}
          >
            <rect x="385" y="70" width="45" height="35" rx="6" fill="#0f172a" stroke="#06b6d4" strokeWidth="2" />
            <text x="407" y="92" textAnchor="middle" fill="#06b6d4" fontSize="10" fontWeight="bold">VSC 1/2</text>
            <text x="407" y="58" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace">2 kHz PWM</text>
          </g>

          {/* 5. Three-Phase Circuit Breaker (SID=3) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('breaker')}
          >
            <rect
              x="475"
              y="100"
              width="60"
              height="40"
              rx="8"
              fill={isTripped ? "#450a0a" : "#064e3b"}
              stroke={isTripped ? "#ef4444" : "#10b981"}
              strokeWidth="2.5"
            />
            {isTripped ? (
              // Open switch visual
              <g>
                <circle cx="488" cy="120" r="4" fill="#ef4444" />
                <circle cx="522" cy="120" r="4" fill="#ef4444" />
                <line x1="488" y1="120" x2="515" y2="108" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
                <text x="505" y="158" textAnchor="middle" fill="#ef4444" fontSize="11" fontWeight="bold">TRIPPED</text>
                <text x="505" y="170" textAnchor="middle" fill="#fca5a5" fontSize="9" fontFamily="monospace">OPEN (1)</text>
              </g>
            ) : (
              // Closed switch visual
              <g>
                <circle cx="488" cy="120" r="4" fill="#10b981" />
                <circle cx="522" cy="120" r="4" fill="#10b981" />
                <line x1="488" y1="120" x2="522" y2="120" stroke="#10b981" strokeWidth="3" />
                <text x="505" y="158" textAnchor="middle" fill="#10b981" fontSize="11" fontWeight="bold">CLOSED</text>
                <text x="505" y="170" textAnchor="middle" fill="#a7f3d0" fontSize="9" fontFamily="monospace">NORMAL (0)</text>
              </g>
            )}
          </g>

          {/* 6. PI Section Line (SID=4) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('line')}
          >
            <rect x="620" y="105" width="60" height="30" rx="6" fill="#0f172a" stroke="#38bdf8" strokeWidth="2" />
            <text x="650" y="124" textAnchor="middle" fill="#38bdf8" fontSize="11" fontWeight="bold">100 km</text>
            <text x="650" y="152" textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="600">PI Section</text>
            <text x="650" y="165" textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">Transmission</text>
          </g>

          {/* 7. Three-Phase Fault Block (SID=6) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('fault')}
          >
            <rect
              x="695"
              y="180"
              width="60"
              height="40"
              rx="8"
              fill={isFaulted ? "#3b0717" : "#0f172a"}
              stroke={isFaulted ? "#f43f5e" : "#475569"}
              strokeWidth="2.5"
            />
            <text
              x="725"
              y="198"
              textAnchor="middle"
              fill={isFaulted ? "#f43f5e" : "#94a3b8"}
              fontSize="10"
              fontWeight="bold"
            >
              FAULT
            </text>
            <text
              x="725"
              y="212"
              textAnchor="middle"
              fill={isFaulted ? "#fca5a5" : "#64748b"}
              fontSize="9"
              fontFamily="monospace"
            >
              {faultType}
            </text>
            {/* Ground symbol */}
            <line x1="725" y1="220" x2="725" y2="232" stroke={isFaulted ? "#f43f5e" : "#475569"} strokeWidth="2" />
            <line x1="717" y1="232" x2="733" y2="232" stroke={isFaulted ? "#f43f5e" : "#475569"} strokeWidth="2" />
            <line x1="720" y1="236" x2="730" y2="236" stroke={isFaulted ? "#f43f5e" : "#475569"} strokeWidth="1.5" />
            <line x1="723" y1="240" x2="727" y2="240" stroke={isFaulted ? "#f43f5e" : "#475569"} strokeWidth="1" />
          </g>

          {/* 8. Parallel RLC Load (SID=114) */}
          <g
            className="cursor-pointer transition-transform hover:scale-105"
            onClick={() => setSelectedBlock('load')}
          >
            <rect x="770" y="105" width="60" height="30" rx="6" fill="#0f172a" stroke="#a855f7" strokeWidth="2" />
            <text x="800" y="124" textAnchor="middle" fill="#a855f7" fontSize="11" fontWeight="bold">LOAD</text>
            <text x="800" y="152" textAnchor="middle" fill="#cbd5e1" fontSize="10" fontWeight="600">Parallel RLC</text>
            <text x="800" y="165" textAnchor="middle" fill="#64748b" fontSize="9" fontFamily="monospace">500 MW</text>
          </g>

          {/* 9. Protection & Measurement Subsystem Link */}
          <g
            className="cursor-pointer"
            onClick={() => setSelectedBlock('protection')}
          >
            <rect x="440" y="20" width="130" height="42" rx="8" fill="#0c1220" stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="3,3" />
            <text x="505" y="38" textAnchor="middle" fill="#f59e0b" fontSize="10" fontWeight="bold">Protection Subsystem</text>
            <text x="505" y="52" textAnchor="middle" fill="#94a3b8" fontSize="9" fontFamily="monospace">Relay + S-R Latch</text>
            {/* Control arrow to breaker */}
            <line x1="505" y1="62" x2="505" y2="100" stroke="#f59e0b" strokeWidth="1.5" markerEnd="url(#arrow)" />
          </g>

          {/* Arrow definition */}
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />
            </marker>
          </defs>
        </svg>
      </div>

      {/* Interactive Detail Box for Clicked Component */}
      {selectedBlock && blocksInfo[selectedBlock] && (
        <div className="mt-4 p-4 rounded-xl bg-grid-950 border border-cyan-500/30 text-xs animate-in fade-in">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Info className="w-4 h-4 text-cyan-400" />
              <span className="font-semibold text-white text-sm">
                {blocksInfo[selectedBlock].title}
              </span>
              <span className="px-2 py-0.5 rounded bg-grid-800 text-cyan-400 font-mono text-[10px]">
                {blocksInfo[selectedBlock].sid}
              </span>
            </div>
            <button
              onClick={() => setSelectedBlock(null)}
              className="text-slate-400 hover:text-white font-mono text-xs px-2 py-0.5"
            >
              ✕ Close
            </button>
          </div>
          <p className="text-slate-300 mb-2">{blocksInfo[selectedBlock].desc}</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {blocksInfo[selectedBlock].params.map((param, i) => (
              <div key={i} className="p-2 rounded bg-grid-900 border border-grid-800 font-mono text-[11px] text-slate-300">
                {param}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
