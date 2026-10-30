import React from 'react';
import { Activity, Cpu, Sliders, LineChart, ShieldAlert, History, Radio } from 'lucide-react';
import { SystemHealth } from '../types';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  health: SystemHealth | null;
  isRunning: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  health,
  isRunning,
}) => {
  const tabs = [
    { id: 'overview', label: 'Overview & Grid', icon: Activity },
    { id: 'controls', label: 'Simulation Controls', icon: Sliders },
    { id: 'waveforms', label: 'Waveform Analysis', icon: LineChart },
    { id: 'diagnostics', label: 'Fault Diagnostics', icon: ShieldAlert },
    { id: 'history', label: 'Run History', icon: History },
  ];

  const isOnline = health?.matlab_connected && health?.model_loaded;

  return (
    <header className="sticky top-0 z-50 bg-grid-900/90 backdrop-blur-md border-b border-grid-800 px-4 lg:px-8 py-3 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center space-x-3">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/40 shadow-lg shadow-cyan-500/10">
              <Cpu className="w-5 h-5 text-cyan-400" />
              {isRunning && (
                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                </span>
              )}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold tracking-tight text-white text-base lg:text-lg">
                  SmartGrid<span className="text-cyan-400">.OS</span>
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-medium rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  MATLAB R2025a
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono hidden sm:block">
                Discrete Solver T<sub className="text-[9px]">s</sub>=50µs | main_model.slx
              </p>
            </div>
          </div>

          {/* Engine Status Badge (Mobile) */}
          <div className="flex md:hidden items-center space-x-1.5 px-2.5 py-1 rounded-full bg-grid-850 border border-grid-700 text-xs font-mono">
            <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 shadow-[0_0_8px_#00ff88]' : 'bg-rose-500'}`} />
            <span className={isOnline ? 'text-emerald-400' : 'text-rose-400'}>
              {isOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 sm:space-x-2 bg-grid-950/80 p-1 rounded-xl border border-grid-800/80 overflow-x-auto max-w-full">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 whitespace-nowrap ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-grid-850 border border-transparent'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Engine Status & Live Indicator (Desktop) */}
        <div className="hidden md:flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-grid-850/90 border border-grid-700 text-xs font-mono">
            <Radio className={`w-3.5 h-3.5 ${isRunning ? 'text-amber-400 animate-pulse' : isOnline ? 'text-emerald-400' : 'text-rose-400'}`} />
            <span className="text-slate-400">ENGINE:</span>
            <span className={isRunning ? 'text-amber-400 font-semibold' : isOnline ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
              {isRunning ? 'SOLVING' : isOnline ? 'READY' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
