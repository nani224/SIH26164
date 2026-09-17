import type { CryptoSemanticClass } from '../types/crypto';
import { AlertTriangle, ShieldCheck, ShieldAlert, Cpu, Lock } from 'lucide-react';
import clsx from 'clsx';

interface CryptoBadgeProps {
  semanticClass: CryptoSemanticClass;
  displayName: string;
  needsReview?: boolean;
  size?: 'sm' | 'md';
}

export function CryptoBadge({
  semanticClass,
  displayName,
  needsReview = false,
  size = 'md',
}: CryptoBadgeProps) {
  const isSm = size === 'sm';

  const badgeStyles: Record<CryptoSemanticClass, { container: string; text: string; icon: typeof Lock; label: string }> = {
    'shor': {
      container: 'bg-[var(--crypto-shor-bg)] border-[var(--crypto-shor-border)] text-[var(--crypto-shor)]',
      text: 'text-[var(--crypto-shor)]',
      icon: ShieldAlert,
      label: 'SHOR',
    },
    'classically-broken': {
      container: 'bg-[var(--crypto-broken-bg)] border-[var(--crypto-broken-border)] text-[var(--crypto-broken)] hatch-broken',
      text: 'text-[var(--crypto-broken)] font-bold',
      icon: AlertTriangle,
      label: 'BROKEN',
    },
    'grover': {
      container: 'bg-[var(--crypto-grover-bg)] border-[var(--crypto-grover-border)] text-[var(--crypto-grover)]',
      text: 'text-[var(--crypto-grover)]',
      icon: Lock,
      label: 'GROVER',
    },
    'quantum-safe-classical': {
      container: 'bg-[var(--crypto-safe-classical-bg)] border-[var(--crypto-safe-classical-border)] text-[var(--crypto-safe-classical)]',
      text: 'text-[var(--crypto-safe-classical)]',
      icon: ShieldCheck,
      label: 'CLASSICAL-SAFE',
    },
    'pqc': {
      container: 'bg-[var(--crypto-pqc-bg)] border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]',
      text: 'text-[var(--crypto-pqc)]',
      icon: Cpu,
      label: 'PQC',
    },
  };

  const current = badgeStyles[semanticClass];
  const Icon = current.icon;

  return (
    <div
      className={clsx(
        'inline-flex items-center gap-1.5 rounded border border-hairline font-mono transition-all',
        isSm ? 'px-1.5 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        current.container,
        needsReview && 'needs-review-dashed ring-1 ring-[var(--band-medium)] ring-offset-1 ring-offset-[var(--surface-base)]'
      )}
      title={`${displayName} — Semantic category: ${current.label}${needsReview ? ' (Low confidence: Needs analyst review)' : ''}`}
    >
      <Icon className={clsx('flex-shrink-0', isSm ? 'w-3 h-3' : 'w-3.5 h-3.5')} />
      <span className={clsx('tracking-wide', current.text)}>{displayName}</span>
      <span className="opacity-60 text-[10px] uppercase font-semibold">[{current.label}]</span>
      {needsReview && (
        <span
          className="ml-1 px-1 py-0.2 bg-[var(--band-medium)] text-[var(--surface-base)] rounded text-[9px] font-bold"
          title="Confidence < 0.75: Needs review"
        >
          REVIEW
        </span>
      )}
    </div>
  );
}
