'use client';

import { ShieldAlert, KeyRound, RotateCcw, SlidersHorizontal, Lock } from 'lucide-react';
import { getActor, triggerOpenAuthSettings } from '../lib/auth';

export interface UnauthorizedStateProps {
  onRetry?: () => void;
  inline?: boolean;
  title?: string;
  message?: string;
  context?: string;
}

export function UnauthorizedState({
  onRetry,
  inline = false,
  title = 'API Authentication Required',
  message = 'The backend rejected the request with HTTP 401 Unauthorized because the bearer token is missing, invalid, or expired.',
  context,
}: UnauthorizedStateProps) {
  const actor = getActor();

  if (inline) {
    return (
      <div
        role="alert"
        aria-live="polite"
        className="p-4 rounded-lg border border-[var(--band-critical)] bg-[var(--surface-card)] text-[var(--text-primary)] font-mono text-xs space-y-3 shadow-md"
      >
        <div className="flex items-start gap-2.5">
          <div className="p-1.5 rounded bg-[var(--crypto-shor-bg)] text-[var(--band-critical)] flex-shrink-0">
            <Lock className="w-4 h-4" />
          </div>
          <div className="space-y-1 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-bold text-[var(--band-critical)] tracking-wide">
                401 UNAUTHORIZED
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)]">
                Bearer Auth Failed
              </span>
              {context && (
                <span className="text-[10px] text-[var(--text-muted)]">· {context}</span>
              )}
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[var(--border-subtle)] text-[11px]">
          <span className="text-[10px] text-[var(--text-muted)]">
            Actor: <code className="text-[var(--text-secondary)]">{actor}</code>
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => triggerOpenAuthSettings()}
              className="px-2.5 py-1 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity inline-flex items-center gap-1.5"
            >
              <KeyRound className="w-3 h-3" />
              <span>Configure Token</span>
            </button>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="px-2.5 py-1 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-colors inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <section
      role="region"
      aria-label="Authentication Required State"
      className="max-w-xl mx-auto my-8 p-6 sm:p-8 rounded-xl border border-[var(--band-critical)] bg-[var(--surface-card)] font-mono text-xs shadow-xl space-y-6 text-left"
    >
      {/* Header with pill and icon */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-[var(--band-critical)] bg-[var(--crypto-shor-bg)] text-[var(--band-critical)] text-[11px] font-bold">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>HTTP 401 · ACCESS REJECTED</span>
        </div>

        <h2 className="text-lg sm:text-xl font-bold text-[var(--text-primary)] tracking-tight">
          {title}
        </h2>

        {context && (
          <div className="text-[11px] text-[var(--crypto-pqc)] font-bold">
            Target View: {context}
          </div>
        )}
      </div>

      {/* Narrative & Guidance */}
      <div className="space-y-3 text-[12px] text-[var(--text-secondary)] leading-relaxed border-y border-[var(--border-subtle)] py-4">
        <p>{message}</p>
        <p className="text-[11px] text-[var(--text-muted)]">
          The ECDAT backend requires{' '}
          <code className="px-1 py-0.5 rounded bg-[var(--surface-raised)] text-[var(--crypto-pqc)]">
            Authorization: Bearer &lt;token&gt;
          </code>{' '}
          on all non-health routes and{' '}
          <code className="px-1 py-0.5 rounded bg-[var(--surface-raised)] text-[var(--crypto-pqc)]">
            X-ECDAT-Actor: &lt;operator&gt;
          </code>{' '}
          for audit validation.
        </p>
        <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px] flex items-center justify-between">
          <span className="text-[var(--text-muted)]">Current Operator Identity:</span>
          <code className="text-[var(--crypto-grover)] font-bold">{actor}</code>
        </div>
      </div>

      {/* Action CTA */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
        <button
          type="button"
          onClick={() => triggerOpenAuthSettings()}
          className="px-4 py-2 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity inline-flex items-center gap-2 text-xs"
        >
          <KeyRound className="w-3.5 h-3.5" />
          <span>Configure API Token</span>
        </button>

        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="px-4 py-2 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-colors inline-flex items-center gap-2 text-xs"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        )}
      </div>
    </section>
  );
}
