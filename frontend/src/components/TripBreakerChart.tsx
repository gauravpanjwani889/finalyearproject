import React from 'react';
import ReactECharts from 'echarts-for-react';
import { ElectricalMetrics } from '../types';

interface TripBreakerChartProps {
  time: number[];
  trip: number[];
  metrics: ElectricalMetrics;
  height?: number;
}

export const TripBreakerChart: React.FC<TripBreakerChartProps> = ({
  time,
  trip,
  metrics,
  height = 240,
}) => {
  const isTripped = metrics.is_breaker_tripped;
  const tripTime = metrics.breaker_trip_time;
  const resetTime = metrics.breaker_reset_time;
  const faultOnset = metrics.fault_onset_time;
  const delayMs = metrics.fault_to_trip_delay_ms;
  const durationMs = metrics.trip_duration_ms;

  // Build shaded markArea for breaker trip duration
  const markAreaData =
    tripTime !== null && tripTime !== undefined
      ? [
          [
            {
              name: 'Breaker Open Interval',
              xAxis: tripTime,
              itemStyle: {
                color: 'rgba(239, 68, 68, 0.15)',
                borderWidth: 1,
                borderColor: 'rgba(239, 68, 68, 0.4)',
                borderType: 'dashed',
              },
              label: {
                color: '#fca5a5',
                fontSize: 10,
                fontFamily: 'monospace',
                position: 'insideTopCenter',
                formatter: durationMs ? `Tripped: ${durationMs.toFixed(1)} ms` : 'Breaker Tripped',
              },
            },
            {
              xAxis: resetTime || 1.0,
            },
          ],
        ]
      : [];

  const markLineData: any[] = [];
  if (faultOnset !== null && faultOnset !== undefined) {
    markLineData.push({
      xAxis: faultOnset,
      name: 'Fault Inception',
      lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' },
      label: {
        formatter: `Fault: ${faultOnset.toFixed(4)}s`,
        color: '#fbbf24',
        fontSize: 10,
        fontFamily: 'monospace',
        position: 'insideEndTop',
      },
    });
  }
  if (tripTime !== null && tripTime !== undefined) {
    markLineData.push({
      xAxis: tripTime,
      name: 'Trip Inception',
      lineStyle: { color: '#ef4444', width: 2, type: 'solid' },
      label: {
        formatter: `Trip: ${tripTime.toFixed(4)}s`,
        color: '#f87171',
        fontSize: 10,
        fontFamily: 'monospace',
        position: 'insideEndTop',
      },
    });
  }
  if (resetTime !== null && resetTime !== undefined && resetTime > (tripTime || 0)) {
    markLineData.push({
      xAxis: resetTime,
      name: 'Breaker Reset',
      lineStyle: { color: '#10b981', width: 1.5, type: 'dotted' },
      label: {
        formatter: `Reset: ${resetTime.toFixed(4)}s`,
        color: '#34d399',
        fontSize: 10,
        fontFamily: 'monospace',
        position: 'insideEndTop',
      },
    });
  }

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: 'CIRCUIT BREAKER PROTECTION TRIP TELEMETRY (ScopeData Channel 6)',
      left: 10,
      top: 6,
      textStyle: {
        color: '#e2e8f0',
        fontSize: 12,
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: '#ef4444',
          width: 1,
          type: 'dashed',
        },
      },
      backgroundColor: 'rgba(12, 18, 32, 0.95)',
      borderColor: '#ef4444',
      borderWidth: 1,
      padding: [8, 12],
      textStyle: {
        color: '#f1f5f9',
        fontSize: 12,
        fontFamily: 'monospace',
      },
      formatter: (params: any) => {
        if (!params || !params.length) return '';
        const tVal = Number(params[0].axisValue).toFixed(4);
        const val = Number(params[0].value);
        const stateStr = val > 0.5 ? 'TRIPPED / OPEN (1)' : 'CLOSED / NORMAL (0)';
        const stateColor = val > 0.5 ? '#ef4444' : '#10b981';

        return `<div style="font-weight:bold; margin-bottom:4px; color:#38bdf8">Timestamp: ${tVal} s</div>
          <div style="display:flex; justify-content:space-between; gap:16px;">
            <span>Breaker Contact:</span>
            <span style="font-weight:bold; color:${stateColor}; font-family:monospace">${stateStr}</span>
          </div>`;
      },
    },
    grid: {
      left: 70,
      right: 30,
      top: 40,
      bottom: 45,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: time,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#213354' } },
      axisTick: { lineStyle: { color: '#213354' } },
      axisLabel: {
        color: '#64748b',
        fontSize: 10,
        fontFamily: 'monospace',
        formatter: (val: string) => Number(val).toFixed(2),
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#16233b',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: -0.15,
      max: 1.15,
      interval: 1.0,
      axisLine: { show: true, lineStyle: { color: '#213354' } },
      axisTick: { show: true },
      axisLabel: {
        color: (val: number) => (val > 0.5 ? '#ef4444' : '#10b981'),
        fontSize: 10,
        fontWeight: 600,
        fontFamily: 'monospace',
        formatter: (val: number) => {
          if (val === 0) return 'CLOSED (0)';
          if (val === 1) return 'TRIPPED (1)';
          return '';
        },
      },
      splitLine: {
        lineStyle: {
          color: '#1e293b',
          type: 'solid',
        },
      },
    },
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0],
      },
      {
        type: 'slider',
        xAxisIndex: [0],
        bottom: 6,
        height: 16,
        borderColor: '#213354',
        fillerColor: 'rgba(239, 68, 68, 0.15)',
        textStyle: { color: '#64748b', fontSize: 10, fontFamily: 'monospace' },
        handleStyle: { color: '#ef4444', borderColor: '#f87171' },
      },
    ],
    series: [
      {
        name: 'Breaker Trip Signal',
        type: 'line',
        step: 'start',
        data: trip,
        showSymbol: false,
        lineStyle: {
          width: 2.5,
          color: '#ef4444',
        },
        itemStyle: {
          color: '#ef4444',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(239, 68, 68, 0.35)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.0)' },
            ],
          },
        },
        markArea: markAreaData.length ? { data: markAreaData } : undefined,
        markLine: markLineData.length ? { data: markLineData } : undefined,
      },
    ],
  };

  return (
    <div className="bg-grid-900 border border-grid-800 rounded-2xl p-4 shadow-xl">
      {/* Telemetry Status Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 mb-3">
        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Breaker Status</div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span
              className={`w-2 h-2 rounded-full ${
                isTripped ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'
              }`}
            />
            <span
              className={`text-xs font-mono font-bold ${
                isTripped ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {isTripped ? 'TRIPPED (OPEN)' : 'CLOSED (HEALTHY)'}
            </span>
          </div>
        </div>

        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Relay Detection</div>
          <div className="text-xs font-mono font-bold mt-0.5">
            {metrics.is_fault_detected ? (
              <span className="text-amber-400">FAULT DETECTED</span>
            ) : (
              <span className="text-slate-400">NO DISTURBANCE</span>
            )}
          </div>
        </div>

        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Fault Onset</div>
          <div className="text-xs font-mono font-bold text-amber-300 mt-0.5">
            {faultOnset !== null ? `${faultOnset.toFixed(4)} s` : 'N/A'}
          </div>
        </div>

        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Trip Time</div>
          <div className="text-xs font-mono font-bold text-rose-400 mt-0.5">
            {tripTime !== null ? `${tripTime.toFixed(4)} s` : 'None'}
          </div>
        </div>

        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Trip Delay</div>
          <div className="text-xs font-mono font-bold text-cyan-300 mt-0.5">
            {delayMs !== null ? `${delayMs.toFixed(2)} ms` : 'N/A'}
          </div>
        </div>

        <div className="bg-grid-950/70 border border-grid-800/80 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 font-mono uppercase">Trip Duration</div>
          <div className="text-xs font-mono font-bold text-emerald-300 mt-0.5">
            {durationMs !== null ? `${durationMs.toFixed(1)} ms` : 'N/A'}
          </div>
        </div>
      </div>

      <ReactECharts
        option={option}
        style={{ height: `${height}px`, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};
