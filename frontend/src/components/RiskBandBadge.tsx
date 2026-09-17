import type { RiskBand } from '../types/crypto';
import clsx from 'clsx';

interface RiskBandBadgeProps {
  band: RiskBand;
  score?: number;
  showScore?: boolean;
}

export function RiskBandBadge({ band, score, showScore = true }: RiskBandBadgeProps) {
  const styles: Record<RiskBand, { bg: string; text: string; border: string; glow: string }> = {
    critical: {
      bg: 'bg-[var(--band-critical-bg)]',
      text: 'text-[var(--band-critical)]',
      border: 'border-[var(--band-critical)]',
      glow: 'glow-critical',
    },
    high: {
      bg: 'bg-[var(--band-high-bg)]',
      text: 'text-[var(--band-high)]',
      border: 'border-[var(--band-high)]',
      glow: 'glow-high',
    },
    medium: {
      bg: 'bg-[var(--band-medium-bg)]',
      text: 'text-[var(--band-medium)]',
      border: 'border-[var(--band-medium)]',
      glow: '',
    },
    low: {
      bg: 'bg-[var(--band-low-bg)]',
      text: 'text-[var(--band-low)]',
      border: 'border-[var(--band-low)]',
      glow: '',
    },
  };

  const current = styles[band];

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[11px] font-mono uppercase tracking-wider',
        current.bg,
        current.text,
        current.border,
        band === 'critical' && current.glow
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current inline-block animate-pulse" />
      <span>{band}</span>
      {showScore && score !== undefined && (
        <span className="num-tabular font-bold border-l border-current/30 pl-1.5 ml-0.5">
          {score.toFixed(1)}
        </span>
      )}
    </span>
  );
}
