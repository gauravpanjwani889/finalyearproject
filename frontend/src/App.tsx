import React, { useState, useEffect, useRef } from 'react';
import {
  SimulationParams,
  SimulationResponse,
  SimulationHistoryItem,
  SystemHealth,
  ModelInfo,
  ParameterLimits,
  FaultType,
} from './types';
import {
  checkHealth,
  getModelInfo,
  getModelParameters,
  executeSimulation,
  getSimulationResult,
  getSimulationHistory,
} from './services/api';
import { Navbar } from './components/Navbar';
import { OverviewView } from './views/OverviewView';
import { ControlsView } from './views/ControlsView';
import { WaveformsView } from './views/WaveformsView';
import { DiagnosticsView } from './views/DiagnosticsView';
import { HistoryView } from './views/HistoryView';
import { AlertCircle, X } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [parameterLimits, setParameterLimits] = useState<ParameterLimits | null>(null);

  // Simulation State
  const [params, setParams] = useState<SimulationParams>({
    fault_type: 'NORMAL',
    fault_resistance: 0.001,
    ground_resistance: 0.01,
    line_resistance: 0.001,
    line_inductance: 0.001,
    line_capacitance: 1e-6,
    downsample_points: 1000,
  });

  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [history, setHistory] = useState<SimulationHistoryItem[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [runStatus, setRunStatus] = useState<string>('Ready');
  const [elapsedSec, setElapsedSec] = useState<number>(0);
  const [errorNotification, setErrorNotification] = useState<string | null>(null);

  const timerRef = useRef<any>(null);

  // Initial Load: Health, Model Info, Limits, History
  useEffect(() => {
    const initApp = async () => {
      try {
        const [h, info, limits, hist] = await Promise.allSettled([
          checkHealth(),
          getModelInfo(),
          getModelParameters(),
          getSimulationHistory(),
        ]);

        if (h.status === 'fulfilled') setHealth(h.value);
        if (info.status === 'fulfilled') setModelInfo(info.value);
        if (limits.status === 'fulfilled') setParameterLimits(limits.value);

        if (hist.status === 'fulfilled' && hist.value.length > 0) {
          setHistory(hist.value);
          // Auto-load most recent run if available
          try {
            const latest = await getSimulationResult(hist.value[0].run_id);
            setSimulationResult(latest);
            setParams(latest.params);
          } catch (e) {
            console.error('Failed to preload latest run:', e);
          }
        }
      } catch (err) {
        console.error('Initialization error:', err);
      }
    };

    initApp();

    // Periodic health heartbeat (every 10 seconds)
    const interval = setInterval(() => {
      checkHealth()
        .then(setHealth)
        .catch(() => setHealth((prev) => (prev ? { ...prev, matlab_connected: false } : null)));
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  // Timer while simulation is running
  useEffect(() => {
    if (isRunning) {
      setElapsedSec(0);
      timerRef.current = setInterval(() => {
        setElapsedSec((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRunning]);

  // Execute Simulation
  const handleRunSimulation = async (overrideParams?: SimulationParams) => {
    const targetParams = overrideParams || params;
    setIsRunning(true);
    setErrorNotification(null);
    setRunStatus('Acquiring persistent MATLAB Engine R2025a session...');

    // Dynamic status messages based on realistic solver stages
    const stageTimeout1 = setTimeout(() => {
      setRunStatus('Applying block parameters to main_model.slx...');
    }, 2000);

    const stageTimeout2 = setTimeout(() => {
      setRunStatus('Simulink discrete solver executing differential equations (Ts=50µs)...');
    }, 5000);

    const stageTimeout3 = setTimeout(() => {
      setRunStatus('Solver solving power electronics PWM switching & relay logic (~25–35s)...');
    }, 12000);

    try {
      const response = await executeSimulation(targetParams, (s) => setRunStatus(s));
      setSimulationResult(response);
      setRunStatus('Extracting ScopeData & computing Akagi Clarke powers...');

      // Update History
      try {
        const updatedHistory = await getSimulationHistory();
        setHistory(updatedHistory);
      } catch (e) {
        console.warn('Could not refresh history:', e);
      }
    } catch (err: any) {
      console.error('Simulation execution failed:', err);
      setErrorNotification(err.message || 'Simulink simulation failed');
    } finally {
      clearTimeout(stageTimeout1);
      clearTimeout(stageTimeout2);
      clearTimeout(stageTimeout3);
      setIsRunning(false);
      setRunStatus('Complete');
    }
  };

  const handleQuickRun = (faultType: FaultType) => {
    const updated: SimulationParams = {
      ...params,
      fault_type: faultType,
      fault_resistance: 0.001,
      ground_resistance: 0.01,
    };
    setParams(updated);
    handleRunSimulation(updated);
  };

  const handleSelectRun = async (runId: string) => {
    try {
      const run = await getSimulationResult(runId);
      setSimulationResult(run);
      setParams(run.params);
      setActiveTab('waveforms');
    } catch (e: any) {
      setErrorNotification(`Failed to load run ${runId}: ${e.message}`);
    }
  };

  const handleRefreshHistory = async () => {
    try {
      const updatedHistory = await getSimulationHistory();
      setHistory(updatedHistory);
    } catch (e: any) {
      setErrorNotification(`Failed to refresh history: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-grid-950 text-slate-100 flex flex-col font-sans">
      {/* Navigation Header */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        isRunning={isRunning}
      />

      {/* Error Alert Banner */}
      {errorNotification && (
        <div className="bg-rose-500/20 border-b border-rose-500/40 px-4 py-2.5 text-xs text-rose-200 flex items-center justify-between">
          <div className="flex items-center space-x-2 max-w-5xl mx-auto w-full">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span className="font-mono">{errorNotification}</span>
          </div>
          <button
            onClick={() => setErrorNotification(null)}
            className="text-rose-400 hover:text-white p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8">
        {activeTab === 'overview' && (
          <OverviewView
            simulationResult={simulationResult}
            health={health}
            modelInfo={modelInfo}
            isRunning={isRunning}
            onQuickRun={handleQuickRun}
            onNavigateToControls={() => setActiveTab('controls')}
            onNavigateToWaveforms={() => setActiveTab('waveforms')}
          />
        )}

        {activeTab === 'controls' && (
          <ControlsView
            params={params}
            setParams={setParams}
            onRunSimulation={() => handleRunSimulation()}
            isRunning={isRunning}
            runStatus={runStatus}
            elapsedSec={elapsedSec}
            parameterLimits={parameterLimits}
            lastResponse={simulationResult}
          />
        )}

        {activeTab === 'waveforms' && (
          <WaveformsView simulationResult={simulationResult} />
        )}

        {activeTab === 'diagnostics' && (
          <DiagnosticsView simulationResult={simulationResult} />
        )}

        {activeTab === 'history' && (
          <HistoryView
            history={history}
            currentRunId={simulationResult?.run_id}
            onSelectRun={handleSelectRun}
            onRefreshHistory={handleRefreshHistory}
            isLoading={isRunning}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-grid-800/80 bg-grid-900/60 py-4 px-4 lg:px-8 text-center text-xs font-mono text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            Smart Grid Stability Monitoring & Automated Fault Diagnostic Platform
          </span>
          <span className="text-slate-400">
            Authoritative Physics: MATLAB R2025a Update 1 / Simulink (main_model.slx)
          </span>
        </div>
      </footer>
    </div>
  );
};

export default App;
