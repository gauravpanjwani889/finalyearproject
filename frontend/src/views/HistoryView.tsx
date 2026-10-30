import React from 'react';
import { SimulationHistoryItem } from '../types';
import {
  History,
  Clock,
  RotateCcw,
  CheckCircle2,
  AlertOctagon,
  Eye,
  Download,
} from 'lucide-react';

interface HistoryViewProps {
  history: SimulationHistoryItem[];
  currentRunId?: string;
  onSelectRun: (runId: string) => void;
  onRefreshHistory: () => void;
  isLoading: boolean;
}

export const HistoryView: React.FC<HistoryViewProps> = ({
  history,
  currentRunId,
  onSelectRun,
  onRefreshHistory,
  isLoading,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-grid-900 border border-grid-800 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center space-x-2">
            <History className="w-5 h-5 text-cyan-400" />
            <span>Simulation Execution Log & History</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Audit trail of all transient simulations executed on MATLAB R2025a during this server lifecycle.
          </p>
        </div>

        <button
          onClick={onRefreshHistory}
          disabled={isLoading}
          className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-grid-800 hover:bg-grid-750 text-slate-200 border border-grid-700 text-xs font-mono transition-all disabled:opacity-50"
        >
          <RotateCcw className={`w-3.5 h-3.5 text-cyan-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh List</span>
        </button>
      </div>

      {/* History Table */}
      <div className="bg-grid-900 border border-grid-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-grid-950/80 text-slate-400 uppercase text-[11px] border-b border-grid-800">
              <tr>
                <th className="py-3.5 px-4 font-semibold">Run ID</th>
                <th className="py-3.5 px-4 font-semibold">Fault Type</th>
                <th className="py-3.5 px-4 font-semibold">Breaker State</th>
                <th className="py-3.5 px-4 font-semibold">Peak I (A)</th>
                <th className="py-3.5 px-4 font-semibold">Min V (V)</th>
                <th className="py-3.5 px-4 font-semibold">Power Factor</th>
                <th className="py-3.5 px-4 font-semibold">Duration (s)</th>
                <th className="py-3.5 px-4 font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-grid-800/60 text-slate-300">
              {history.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-slate-500">
                    No simulation runs recorded yet. Execute a simulation to see history.
                  </td>
                </tr>
              ) : (
                history.map((item) => {
                  const isCurrent = item.run_id === currentRunId;
                  return (
                    <tr
                      key={item.run_id}
                      className={`hover:bg-grid-850/60 transition-colors ${
                        isCurrent ? 'bg-cyan-500/10' : ''
                      }`}
                    >
                      <td className="py-3 px-4 font-semibold">
                        <div className="flex items-center space-x-1.5">
                          {isCurrent && (
                            <span className="w-2 h-2 rounded-full bg-cyan-400" />
                          )}
                          <span className="text-cyan-400">
                            {item.run_id.slice(0, 8)}...
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-grid-800 border border-grid-700 text-slate-200">
                          {item.fault_type}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        {item.is_breaker_tripped ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-rose-500/15 border border-rose-500/30 text-rose-300 flex items-center w-fit space-x-1">
                            <AlertOctagon className="w-3 h-3 text-rose-400" />
                            <span>TRIPPED</span>
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 flex items-center w-fit space-x-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>CLOSED</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4 font-semibold text-slate-200">
                        {item.peak_current} A
                      </td>

                      <td className="py-3 px-4 text-slate-300">
                        {item.min_voltage} V
                      </td>

                      <td className="py-3 px-4 text-slate-300">
                        {item.power_factor}
                      </td>

                      <td className="py-3 px-4 text-slate-400">
                        {item.execution_duration_sec}s
                      </td>

                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => onSelectRun(item.run_id)}
                          className="px-2.5 py-1 rounded-lg bg-grid-800 hover:bg-cyan-500/20 text-cyan-300 border border-grid-700 hover:border-cyan-500/40 text-[11px] font-medium transition-all inline-flex items-center space-x-1"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Load Result</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
