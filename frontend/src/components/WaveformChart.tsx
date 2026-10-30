import React from 'react';
import ReactECharts from 'echarts-for-react';

export interface SeriesConfig {
  name: string;
  data: number[];
  color: string;
  unit: string;
  yAxisIndex?: number;
  type?: 'line' | 'step';
}

interface WaveformChartProps {
  title: string;
  time: number[];
  series: SeriesConfig[];
  yAxisName?: string;
  yAxisName2?: string;
  height?: number;
  showFaultWindow?: boolean;
  tripTime?: number | null;
  faultOnset?: number | null;
}

export const WaveformChart: React.FC<WaveformChartProps> = ({
  title,
  time,
  series,
  yAxisName = '',
  yAxisName2 = '',
  height = 320,
  showFaultWindow = true,
  tripTime = null,
  faultOnset = null,
}) => {
  // Build markLines / markAreas for fault injection window [0.2, 0.4]s
  const markAreaData = showFaultWindow
    ? [
        [
          {
            name: 'Fault Window [0.2s - 0.4s]',
            xAxis: 0.2,
            itemStyle: {
              color: 'rgba(244, 63, 94, 0.08)',
              borderWidth: 1,
              borderColor: 'rgba(244, 63, 94, 0.25)',
              borderType: 'dashed',
            },
            label: {
              color: '#fda4af',
              fontSize: 10,
              fontFamily: 'monospace',
              position: 'insideTopLeft',
            },
          },
          {
            xAxis: 0.4,
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
        formatter: `Fault: ${faultOnset}s`,
        color: '#fbbf24',
        fontSize: 10,
        fontFamily: 'monospace',
      },
    });
  }
  if (tripTime !== null && tripTime !== undefined) {
    markLineData.push({
      xAxis: tripTime,
      name: 'Breaker Trip',
      lineStyle: { color: '#ef4444', width: 1.5, type: 'solid' },
      label: {
        formatter: `Trip: ${tripTime}s`,
        color: '#f87171',
        fontSize: 10,
        fontFamily: 'monospace',
      },
    });
  }

  const hasSecondaryY = series.some((s) => s.yAxisIndex === 1);

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: title,
      left: 10,
      top: 6,
      textStyle: {
        color: '#e2e8f0',
        fontSize: 13,
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: {
          color: '#38bdf8',
          width: 1,
          type: 'dashed',
        },
      },
      backgroundColor: 'rgba(12, 18, 32, 0.95)',
      borderColor: '#213354',
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
        let out = `<div style="font-weight:bold; margin-bottom:4px; color:#38bdf8">Time: ${tVal} s</div>`;
        params.forEach((item: any) => {
          const sConf = series.find((s) => s.name === item.seriesName);
          const u = sConf ? ` ${sConf.unit}` : '';
          const marker = `<span style="display:inline-block;margin-right:5px;border-radius:10px;width:9px;height:9px;background-color:${item.color};"></span>`;
          out += `<div style="display:flex; justify-content:space-between; gap:16px;">
            <span>${marker}${item.seriesName}:</span>
            <span style="font-weight:600; font-family:monospace">${Number(item.value).toFixed(2)}${u}</span>
          </div>`;
        });
        return out;
      },
    },
    legend: {
      top: 6,
      right: 40,
      textStyle: {
        color: '#94a3b8',
        fontSize: 11,
        fontFamily: 'monospace',
      },
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 8,
    },
    grid: {
      left: 55,
      right: hasSecondaryY ? 55 : 25,
      top: 45,
      bottom: 50,
      containLabel: true,
    },
    toolbox: {
      right: 10,
      top: 6,
      iconStyle: {
        borderColor: '#64748b',
      },
      feature: {
        dataZoom: { yAxisIndex: 'none' },
        restore: {},
        saveAsImage: {
          title: 'Save PNG',
          pixelRatio: 2,
          backgroundColor: '#0c1220',
        },
      },
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
    yAxis: [
      {
        type: 'value',
        name: yAxisName,
        nameTextStyle: {
          color: '#94a3b8',
          fontSize: 10,
          fontFamily: 'monospace',
          padding: [0, 0, 4, 0],
        },
        axisLine: { show: true, lineStyle: { color: '#213354' } },
        axisLabel: {
          color: '#64748b',
          fontSize: 10,
          fontFamily: 'monospace',
        },
        splitLine: {
          lineStyle: {
            color: '#16233b',
            type: 'dashed',
          },
        },
      },
      ...(hasSecondaryY
        ? [
            {
              type: 'value',
              name: yAxisName2,
              nameTextStyle: {
                color: '#94a3b8',
                fontSize: 10,
                fontFamily: 'monospace',
                padding: [0, 0, 4, 0],
              },
              axisLine: { show: true, lineStyle: { color: '#213354' } },
              axisLabel: {
                color: '#64748b',
                fontSize: 10,
                fontFamily: 'monospace',
              },
              splitLine: { show: false },
            },
          ]
        : []),
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        xAxisIndex: [0],
        bottom: 8,
        height: 18,
        borderColor: '#213354',
        fillerColor: 'rgba(6, 182, 212, 0.15)',
        textStyle: { color: '#64748b', fontSize: 10, fontFamily: 'monospace' },
        handleStyle: { color: '#06b6d4', borderColor: '#22d3ee' },
      },
    ],
    series: series.map((s, idx) => ({
      name: s.name,
      type: s.type || 'line',
      yAxisIndex: s.yAxisIndex || 0,
      data: s.data,
      showSymbol: false,
      step: s.type === 'step' ? 'start' : undefined,
      lineStyle: {
        width: s.type === 'step' ? 2 : 1.8,
        color: s.color,
      },
      itemStyle: {
        color: s.color,
      },
      markArea: idx === 0 && markAreaData.length ? { data: markAreaData } : undefined,
      markLine: idx === 0 && markLineData.length ? { data: markLineData } : undefined,
    })),
  };

  return (
    <div className="bg-grid-900 border border-grid-800 rounded-2xl p-4 shadow-xl relative">
      <ReactECharts
        option={option}
        style={{ height: `${height}px`, width: '100%' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  );
};
