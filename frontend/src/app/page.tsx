'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchScans } from '../lib/api';
import { UnauthorizedState } from '../components/UnauthorizedState';
import { isUnauthorizedError } from '../lib/auth';
import { ArrowRight, Sparkles } from 'lucide-react';

export default function HomePage() {
  const { data: scans, error: scansError, refetch } = useQuery({
    queryKey: ['scans'],
    queryFn: fetchScans,
  });
  const scan = scans?.[0];

  if (isUnauthorizedError(scansError)) {
    return (
      <UnauthorizedState
        onRetry={() => refetch()}
        context="Cipher Observatory Home"
      />
    );
  }

  return (
    <div className="space-y-8 py-4">
      {/* Top Banner */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-prominent)] rounded-xl p-6 sm:p-8 relative overflow-hidden">
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-mono border border-[var(--crypto-pqc-border)] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)]">
            <Sparkles className="w-3.5 h-3.5" />
            <span>NTRO PS SIH26164 · MILESTONE 1 COMPLETE</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-mono font-bold tracking-tight text-[var(--text-primary)]">
            CIPHER OBSERVATORY
          </h1>

          <p className="text-sm sm:text-base text-[var(--text-secondary)] leading-relaxed">
            Enterprise Cryptographic Discovery & Analysis Tool (ECDAT). Signals-intelligence console
            evaluating classical vulnerability, Mosca quantum horizons ($X + Y &gt; Z$), and NIST FIPS post-quantum replacements.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-3 font-mono text-xs">
            <Link
              href="/specimen"
              className="px-4 py-2 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity inline-flex items-center gap-2"
            >
              <span>EXPLORE DESIGN SPECIMEN</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <span className="text-[var(--text-muted)] font-mono text-xs">
              Review Loop F1 tokens, contrast pass, and live Mosca slider
            </span>
          </div>
        </div>
      </div>

      {/* Metric Bento Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg">
          <div className="text-[11px] text-[var(--text-muted)] uppercase">Critical Risks</div>
          <div className="text-3xl font-bold text-[var(--band-critical)] mt-2 num-tabular">
            {scan?.bands?.critical ?? 6}
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] mt-1">
            Immediate Shor / Broken
          </div>
        </div>

        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg">
          <div className="text-[11px] text-[var(--text-muted)] uppercase">High Risks</div>
          <div className="text-3xl font-bold text-[var(--band-high)] mt-2 num-tabular">
            {scan?.bands?.high ?? 8}
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] mt-1">
            Migration horizon close
          </div>
        </div>

        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg">
          <div className="text-[11px] text-[var(--text-muted)] uppercase">Files Ingested</div>
          <div className="text-3xl font-bold text-[var(--text-primary)] mt-2 num-tabular">
            {scan?.stats?.files?.toLocaleString() ?? '1,420'}
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] mt-1">
            {((scan?.stats?.bytes ?? 28450190) / 1024 / 1024).toFixed(1)} MB analyzed
          </div>
        </div>

        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg">
          <div className="text-[11px] text-[var(--text-muted)] uppercase">Throughput</div>
          <div className="text-3xl font-bold text-[var(--crypto-pqc)] mt-2 num-tabular">
            {(scan?.stats?.mbPerSec ?? 5.9).toFixed(1)} <span className="text-xs">MB/s</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] mt-1">
            Deterministic AST scan
          </div>
        </div>
      </div>
    </div>
  );
}
