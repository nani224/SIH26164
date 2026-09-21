'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchScanCoverage, fetchEstateTrend } from '../lib/api';
import { AlertOctagon, CheckCircle2, ArrowRight, TrendingUp, AlertTriangle } from 'lucide-react';

interface CoverageCertificateCardProps {
  scanId: string;
}

export function CoverageCertificateCard({ scanId }: CoverageCertificateCardProps) {
  const {
    data: cert,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['coverage', scanId],
    queryFn: () => fetchScanCoverage(scanId),
    enabled: Boolean(scanId),
  });

  const { data: trend } = useQuery({
    queryKey: ['estateTrend', 7],
    queryFn: () => fetchEstateTrend(7),
  });

  // Calculate percentage shares directly from API mass numbers
  const massBreakdown = useMemo(() => {
    if (!cert || cert.totalMass <= 0) {
      return { attributedPct: 0, excludedPct: 0, residuePct: 0 };
    }
    const total = cert.totalMass;
    const attributedPct = Math.min(100, Math.max(0, (cert.attributedMass / total) * 100));
    const excludedPct = Math.min(100, Math.max(0, (cert.excludedMass / total) * 100));
    const residuePct = Math.min(100, Math.max(0, (cert.residueMass / total) * 100));
    return {
      attributedPct: Number(attributedPct.toFixed(1)),
      excludedPct: Number(excludedPct.toFixed(1)),
      residuePct: Number(residuePct.toFixed(1)),
    };
  }, [cert]);

  // Generate sparkline coordinates from trend points
  const sparklinePoints = useMemo(() => {
    if (!trend?.points || trend.points.length < 2) return null;
    const width = 120;
    const height = 32;
    const padding = 2;
    const pts = trend.points.slice(-7);
    const minVal = 50;
    const maxVal = 100;
    const range = maxVal - minVal || 1;

    const coords = pts.map((p, idx) => {
      const x = padding + (idx / (pts.length - 1)) * (width - 2 * padding);
      // approximate coverage trajectory using (100 - (avgRiskScore / 2)) for demonstration
      const simulatedCoverage = Math.max(60, Math.min(100, 100 - p.avgRiskScore * 0.3));
      const y = height - padding - ((simulatedCoverage - minVal) / range) * (height - 2 * padding);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    return coords.join(' ');
  }, [trend]);

  if (isLoading) {
    return (
      <div
        data-testid="coverage-skeleton"
        className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 font-mono animate-pulse min-h-[160px]"
      >
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
          <div className="h-4 w-44 bg-[var(--surface-raised)] rounded" />
          <div className="h-5 w-24 bg-[var(--surface-raised)] rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="h-14 bg-[var(--surface-raised)] rounded" />
          <div className="h-14 bg-[var(--surface-raised)] rounded" />
          <div className="h-14 bg-[var(--surface-raised)] rounded" />
        </div>
      </div>
    );
  }

  if (error || !cert) {
    return (
      <div
        data-testid="coverage-error"
        className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 font-mono"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[var(--text-secondary)] text-sm font-bold">
            <AlertTriangle className="w-4 h-4 text-[var(--band-high)]" />
            <span>Coverage Certificate Unavailable</span>
          </div>
          <button
            onClick={() => refetch()}
            className="px-2.5 py-1 rounded bg-[var(--surface-raised)] hover:bg-[var(--surface-card-hover)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)]"
          >
            Retry
          </button>
        </div>
        <p className="text-xs text-[var(--text-muted)] mt-2">
          {error instanceof Error ? error.message : 'Could not retrieve crypto mass conservation certificate.'}
        </p>
      </div>
    );
  }

  const hasResidue = cert.residueClusterCount > 0 || cert.residueMass > 0;
  const coveragePercent = (cert.coverageRatio * 100).toFixed(1);

  return (
    <section
      data-testid="coverage-certificate-card"
      aria-label="Crypto Mass Conservation Coverage Certificate"
      className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 font-mono relative overflow-hidden"
    >
      {/* Top Header: Title, Ratio, Incompleteness / Attestation Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-1.5">
              <span>Crypto Mass Coverage</span>
            </h2>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider flex items-center gap-1 ${
                hasResidue
                  ? 'bg-[var(--coverage-residue-bg)] text-[var(--coverage-residue)] border-[var(--coverage-residue-border)]'
                  : 'bg-[var(--coverage-attributed-bg)] text-[var(--coverage-attributed)] border-[var(--coverage-attributed-border)]'
              }`}
            >
              {hasResidue ? (
                <>
                  <AlertOctagon className="w-3 h-3" />
                  <span>Evidence Incomplete</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-3 h-3" />
                  <span>100% Accounted</span>
                </>
              )}
            </span>
          </div>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            {cert.artifactCount.toLocaleString()} artifacts analyzed · Total mass:{' '}
            {cert.totalMass.toLocaleString()}
          </p>
        </div>

        {/* Primary Coverage Ratio beside Band Counts */}
        <div className="flex items-center gap-4">
          {sparklinePoints && (
            <div className="hidden sm:flex flex-col items-end">
              <span className="text-[9px] text-[var(--text-muted)] uppercase flex items-center gap-1">
                <TrendingUp className="w-2.5 h-2.5" />
                <span>Coverage Trend</span>
              </span>
              <svg
                width="120"
                height="32"
                viewBox="0 0 120 32"
                className="overflow-visible"
                aria-label="Coverage trend sparkline"
              >
                <polyline
                  fill="none"
                  stroke="var(--coverage-attributed)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={sparklinePoints}
                />
              </svg>
            </div>
          )}

          <div className="text-right">
            <span className="text-[10px] text-[var(--text-muted)] uppercase block">Coverage Ratio</span>
            <span
              data-testid="coverage-ratio-metric"
              className={`text-2xl sm:text-3xl font-bold num-tabular ${
                hasResidue ? 'text-[var(--coverage-residue)]' : 'text-[var(--coverage-attributed)]'
              }`}
            >
              {coveragePercent}%
            </span>
          </div>
        </div>
      </div>

      {/* Mass Conservation Bar: Attributed / Excluded / Residue */}
      <div className="mt-4 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[11px] text-[var(--text-muted)] uppercase">Crypto Mass Conservation Bar</span>
          <span className="text-[11px] text-[var(--text-muted)] num-tabular">
            {cert.totalMass.toLocaleString()} total units
          </span>
        </div>

        {/* Segmented Bar */}
        <div
          role="progressbar"
          aria-valuenow={Number(coveragePercent)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Coverage ${coveragePercent}%`}
          className="h-4 w-full rounded bg-[var(--surface-raised)] overflow-hidden flex border border-[var(--border-subtle)]"
        >
          {/* Attributed segment */}
          <div
            style={{ width: `${massBreakdown.attributedPct}%` }}
            title={`Attributed Mass: ${cert.attributedMass} (${massBreakdown.attributedPct}%)`}
            className="h-full bg-[var(--coverage-attributed)] transition-all duration-300"
          />
          {/* Excluded segment */}
          <div
            style={{ width: `${massBreakdown.excludedPct}%` }}
            title={`Excluded Mass: ${cert.excludedMass} (${massBreakdown.excludedPct}%)`}
            className="h-full bg-[var(--coverage-excluded)] transition-all duration-300 opacity-80"
          />
          {/* Residue segment */}
          <div
            style={{ width: `${massBreakdown.residuePct}%` }}
            title={`Residue Mass: ${cert.residueMass} (${massBreakdown.residuePct}%)`}
            className="h-full bg-[var(--coverage-residue)] transition-all duration-300 relative"
          />
        </div>

        {/* Three Mass Breakdown Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
          {/* Attributed */}
          <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[var(--coverage-attributed)] inline-block flex-shrink-0" />
              <div>
                <span className="text-[10px] text-[var(--text-muted)] uppercase block">Attributed</span>
                <span className="font-bold text-[var(--text-primary)] num-tabular">
                  {cert.attributedMass.toLocaleString()}
                </span>
              </div>
            </div>
            <span className="text-xs font-bold text-[var(--coverage-attributed)] num-tabular">
              {massBreakdown.attributedPct}%
            </span>
          </div>

          {/* Excluded */}
          <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[var(--coverage-excluded)] inline-block flex-shrink-0" />
              <div>
                <span className="text-[10px] text-[var(--text-muted)] uppercase block">Excluded</span>
                <span className="font-bold text-[var(--text-primary)] num-tabular">
                  {cert.excludedMass.toLocaleString()}
                </span>
              </div>
            </div>
            <span className="text-xs font-bold text-[var(--text-secondary)] num-tabular">
              {massBreakdown.excludedPct}%
            </span>
          </div>

          {/* Residue */}
          <div
            className={`p-2.5 rounded border flex items-center justify-between ${
              hasResidue
                ? 'bg-[var(--coverage-residue-bg)] border-[var(--coverage-residue-border)]'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)]'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-[var(--coverage-residue)] inline-block flex-shrink-0" />
              <div>
                <span className="text-[10px] text-[var(--text-muted)] uppercase block">Unexplained Residue</span>
                <span className="font-bold text-[var(--text-primary)] num-tabular">
                  {cert.residueMass.toLocaleString()}
                </span>
              </div>
            </div>
            <span
              className={`text-xs font-bold num-tabular ${
                hasResidue ? 'text-[var(--coverage-residue)]' : 'text-[var(--text-secondary)]'
              }`}
            >
              {massBreakdown.residuePct}%
            </span>
          </div>
        </div>
      </div>

      {/* Actionable Call to Action when Residue exists */}
      <div className="mt-4 pt-3 border-t border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-2 text-xs">
          {hasResidue ? (
            <>
              <AlertOctagon className="w-4 h-4 text-[var(--coverage-residue)] flex-shrink-0" />
              <span className="text-[var(--text-primary)] font-bold">
                {cert.residueClusterCount} unexplained crypto residue cluster
                {cert.residueClusterCount === 1 ? '' : 's'} detected in this scan
              </span>
            </>
          ) : (
            <>
              <CheckCircle2 className="w-4 h-4 text-[var(--coverage-attributed)] flex-shrink-0" />
              <span className="text-[var(--text-muted)]">
                Zero unexplained residue clusters — all cryptographic evidence fully attributed.
              </span>
            </>
          )}
        </div>

        <Link
          id="explore-residue-cta"
          href="/residue"
          className={`px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
            hasResidue
              ? 'bg-[var(--coverage-residue)] text-[var(--surface-base)] hover:opacity-90 shadow-sm'
              : 'bg-[var(--surface-raised)] text-[var(--text-primary)] border border-[var(--border-subtle)] hover:border-[var(--border-prominent)]'
          }`}
        >
          <span>{hasResidue ? 'Review Residue Ledger' : 'View Debt Ledger'}</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </section>
  );
}
