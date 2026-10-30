import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: LucideIcon;
  variant?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate';
  subtitle?: string;
  badge?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  unit,
  icon: Icon,
  variant = 'cyan',
  subtitle,
  badge,
}) => {
  const variantStyles = {
    cyan: {
      border: 'border-cyan-500/30',
      bg: 'bg-gradient-to-br from-cyan-950/40 via-grid-900 to-grid-900',
      iconBg: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400',
      valueColor: 'text-cyan-300',
      glow: 'shadow-cyan-500/5',
    },
    emerald: {
      border: 'border-emerald-500/30',
      bg: 'bg-gradient-to-br from-emerald-950/40 via-grid-900 to-grid-900',
      iconBg: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
      valueColor: 'text-emerald-300',
      glow: 'shadow-emerald-500/5',
    },
    amber: {
      border: 'border-amber-500/30',
      bg: 'bg-gradient-to-br from-amber-950/40 via-grid-900 to-grid-900',
      iconBg: 'bg-amber-500/15 border-amber-500/30 text-amber-400',
      valueColor: 'text-amber-300',
      glow: 'shadow-amber-500/5',
    },
    rose: {
      border: 'border-rose-500/30',
      bg: 'bg-gradient-to-br from-rose-950/40 via-grid-900 to-grid-900',
      iconBg: 'bg-rose-500/15 border-rose-500/30 text-rose-400',
      valueColor: 'text-rose-300',
      glow: 'shadow-rose-500/5',
    },
    slate: {
      border: 'border-grid-750',
      bg: 'bg-grid-900',
      iconBg: 'bg-grid-800 border-grid-700 text-slate-300',
      valueColor: 'text-slate-100',
      glow: 'shadow-transparent',
    },
  };

  const style = variantStyles[variant];

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border ${style.border} ${style.bg} p-5 shadow-xl ${style.glow} transition-all duration-300 hover:scale-[1.01]`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
            {title}
          </p>
          <div className="flex items-baseline space-x-2">
            <span className={`text-2xl lg:text-3xl font-bold font-mono tracking-tight ${style.valueColor}`}>
              {value}
            </span>
            {unit && (
              <span className="text-xs font-mono font-medium text-slate-400">
                {unit}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 font-mono pt-1">
              {subtitle}
            </p>
          )}
        </div>

        <div className={`p-3 rounded-xl border ${style.iconBg} shadow-inner`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {badge && (
        <div className="mt-3 pt-3 border-t border-grid-800/80 flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-400">Status</span>
          <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${style.iconBg}`}>
            {badge}
          </span>
        </div>
      )}
    </div>
  );
};
