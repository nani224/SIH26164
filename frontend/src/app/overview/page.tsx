'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScan, fetchScanFindings } from '../../lib/api';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { CbomExportButton } from '../../components/CbomExportButton';
import { CoverageCertificateCard } from '../../components/CoverageCertificateCard';
import { AttestationModal } from '../../components/AttestationModal';
import { BenchmarkModal } from '../../components/BenchmarkModal';
import { DemoTourModal } from '../../components/DemoTourModal';
import { classifyAlgorithm } from '../../types/crypto';
import {
  ShieldAlert,
  AlertTriangle,
  FileCheck,
  Cpu,
  Layers,
  ArrowRight,
  TrendingUp,
  Activity,
  HardDrive,
  Network,
  Clock,
  ExternalLink,
  RefreshCw,
  Compass,
  Award,
  ShieldCheck,
} from 'lucide-react';
import Link from 'next/link';

export default function OverviewPage() {
  const router = useRouter();
  const { activeScanId, openDrawer } = useAppStore();

  const [isAttestationOpen, setIsAttestationOpen] = useState(false);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [isTourOpen, setIsTourOpen] = useState(false);

  const {
    data: scan,
    isLoading: scanLoading,
    error: scanError,
    refetch: refetchScan,
  } = useQuery({
    queryKey: ['scan', activeScanId],
    queryFn: () => fetchScan(activeScanId),
  });

  const {
    data: findingsData,
    isLoading: findingsLoading,
  } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  const findings = useMemo(() => findingsData?.items ?? [], [findingsData]);

  // Derive urgent counts
  const hndlCount = useMemo(() => findings.filter((f) => f.risk?.hndl).length, [findings]);
  const brokenCount = useMemo(() => findings.filter((f) => f.risk?.classicallyBroken).length, [findings]);
  const topRisks = useMemo(
    () =>
      findings
        .filter((f): f is typeof f & { risk: NonNullable<(typeof f)['risk']> } => f.risk != null)
        .sort((a, b) => b.risk.score - a.risk.score)
        .slice(0, 5),
    [findings]
  );

  if (scanLoading || findingsLoading) {
    return (
      <div className="space-y-6 font-mono animate-pulse">
        {/* Top Bar Skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4 min-h-[72px]">
          <div>
            <div className="h-3 w-48 bg-[var(--surface-raised)] rounded mb-2" />
            <div className="h-6 w-72 bg-[var(--surface-raised)] rounded" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-8 w-32 bg-[var(--surface-raised)] rounded" />
          </div>
        </div>

        {/* Primary Threat Bento Grid Skeleton */}
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 min-h-[110px]">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg h-[100px] flex flex-col justify-between">
              <div className="h-3 w-16 bg-[var(--surface-raised)] rounded" />
              <div className="h-8 w-12 bg-[var(--surface-raised)] rounded" />
              <div className="h-2 w-20 bg-[var(--surface-raised)] rounded" />
            </div>
          ))}
        </div>

        {/* Ingestion & Performance Telemetry Skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[var(--surface-raised)] border border-[var(--border-subtle)] p-4 rounded-lg min-h-[82px]">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-2.5 w-20 bg-[var(--surface-card)] rounded" />
              <div className="h-6 w-16 bg-[var(--surface-card)] rounded" />
            </div>
          ))}
        </div>

        {/* Lower section Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[350px]">
          <div className="lg:col-span-2 bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 h-[350px]">
            <div className="h-4 w-40 bg-[var(--surface-raised)] rounded mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-10 bg-[var(--surface-raised)] rounded" />
              ))}
            </div>
          </div>
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 h-[350px]">
            <div className="h-4 w-32 bg-[var(--surface-raised)] rounded mb-4" />
            <div className="h-48 bg-[var(--surface-raised)] rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (scanError || !scan) {
    return (
      <div className="space-y-6 font-mono p-8 text-center">
        <div className="max-w-md mx-auto p-6 rounded border border-[var(--band-critical)] bg-[var(--surface-card)] text-left">
          <div className="flex items-center gap-2 text-[var(--band-critical)] font-bold text-sm mb-2">
            <AlertTriangle className="w-5 h-5" />
            <span>Telemetry Link Disconnected</span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] mb-4">
            {scanError instanceof Error ? scanError.message : 'Unable to load scan details.'}
          </p>
          <button
            onClick={() => refetchScan()}
            className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] text-xs font-bold hover:opacity-90"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Top Bar with Target details and CBOM export */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Activity className="w-3.5 h-3.5" />
            <span>SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)]">
            {scan.target}
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Scan ID: {scan.id} · Completed in {scan.stats?.seconds ?? 0}s · Policy: {scan.policyId}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            id="open-tour-btn"
            onClick={() => setIsTourOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] hover:bg-[var(--surface-card-hover)] font-mono text-xs font-bold transition-colors"
          >
            <Compass className="w-3.5 h-3.5" />
            <span>DEMO TOUR</span>
          </button>
          <button
            id="open-attestation-btn"
            onClick={() => setIsAttestationOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--text-primary)] hover:bg-[var(--surface-card-hover)] font-mono text-xs font-bold transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-[var(--coverage-attributed)]" />
            <span>VERIFY ATTESTATION</span>
          </button>
          <button
            id="open-benchmark-btn"
            onClick={() => setIsBenchmarkOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--text-primary)] hover:bg-[var(--surface-card-hover)] font-mono text-xs transition-colors"
          >
            <Award className="w-3.5 h-3.5 text-[var(--crypto-shor)]" />
            <span>BENCHMARK</span>
          </button>
          <CbomExportButton scanId={scan.id} />
          <Link
            href="/mosca"
            className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5"
          >
            <span>MOSCA MATRIX</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Coverage Certificate & Mass Conservation Surface (v1.0 Milestone M1) */}
      <CoverageCertificateCard scanId={scan.id} />

      {/* Primary Threat Bento Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Critical */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Critical Risks</span>
          <div className="text-2xl font-bold text-[var(--band-critical)] mt-2 num-tabular">
            {scan.bands.critical}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Score ≥ 60</span>
        </div>

        {/* High */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">High Risks</span>
          <div className="text-2xl font-bold text-[var(--band-high)] mt-2 num-tabular">
            {scan.bands.high}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Score 35–59</span>
        </div>

        {/* Medium */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Medium Risks</span>
          <div className="text-2xl font-bold text-[var(--band-medium)] mt-2 num-tabular">
            {scan.bands.medium}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Score 15–34</span>
        </div>

        {/* Low */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Low / PQC</span>
          <div className="text-2xl font-bold text-[var(--band-low)] mt-2 num-tabular">
            {scan.bands.low}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Score &lt; 15</span>
        </div>

        {/* HNDL Exposed */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--crypto-shor)] font-semibold uppercase flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" />
            <span>HNDL Active</span>
          </span>
          <div className="text-2xl font-bold text-[var(--crypto-shor)] mt-2 num-tabular">
            {hndlCount}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Exposed to Store-Now</span>
        </div>

        {/* Classically Broken */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between relative overflow-hidden">
          <span className="text-[10px] text-[var(--crypto-broken)] font-semibold uppercase flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            <span>Broken Today</span>
          </span>
          <div className="text-2xl font-bold text-[var(--crypto-broken)] mt-2 num-tabular">
            {brokenCount}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">MD5, SHA-1, DES, RC4</span>
        </div>
      </div>

      {/* Ingestion & Performance Telemetry */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-[var(--surface-raised)] border border-[var(--border-subtle)] p-4 rounded-lg text-xs">
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Ingested Files</span>
          <div className="font-bold text-[var(--text-primary)] text-base mt-1 num-tabular">
            {(scan.stats?.files ?? 0).toLocaleString()}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Analyzed Volume</span>
          <div className="font-bold text-[var(--text-primary)] text-base mt-1 num-tabular">
            {((scan.stats?.bytes ?? 0) / (1024 * 1024)).toFixed(2)} MB
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Throughput</span>
          <div className="font-bold text-[var(--crypto-pqc)] text-base mt-1 num-tabular">
            {scan.stats?.mbPerSec ?? 0} MB/s
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Prefilter Skips</span>
          <div className="font-bold text-[var(--text-secondary)] text-base mt-1 num-tabular">
            {scan.stats?.skippedPrefilter ?? 0} files
          </div>
        </div>
      </div>

      {/* Top 5 Urgent Risks & Actionable Next Steps */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Urgent Findings List */}
        <div className="lg:col-span-2 bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3 mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[var(--crypto-shor)]" />
              <h2 className="text-sm font-bold text-[var(--text-primary)]">
                Highest Urgency Cryptographic Assets
              </h2>
            </div>
            <Link
              href="/inventory"
              className="text-xs text-[var(--crypto-pqc)] hover:underline flex items-center gap-1"
            >
              <span>Full Inventory</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="divide-y divide-[var(--border-subtle)]">
            {topRisks.map((f) => (
              <div
                key={f.id}
                onClick={() => openDrawer(f)}
                className="py-3 flex items-center justify-between gap-3 hover:bg-[var(--surface-raised)] px-2 rounded cursor-pointer transition-colors"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className="pt-0.5">
                    <RiskBandBadge band={f.risk.band} score={f.risk.score} size="sm" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-xs text-[var(--text-primary)]">
                        {f.displayName}
                      </span>
                      <CryptoBadge
                        cryptoClass={classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken)}
                        label={f.family ?? undefined}
                        size="sm"
                      />
                      {f.risk.hndl && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] font-bold">
                          HNDL
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                      {f.location.path}:{f.location.line} · {f.symbol}
                    </p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-xs font-bold text-[var(--text-primary)] num-tabular">
                    Score {f.risk.score.toFixed(1)}
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)]">
                    Margin: {f.risk.moscaMargin > 0 ? `+${f.risk.moscaMargin}y` : `${f.risk.moscaMargin}y`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Route Cards */}
        <div className="space-y-4">
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4">
            <h3 className="text-xs font-bold text-[var(--text-primary)] uppercase flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-[var(--crypto-pqc)]" />
              <span>Domain Visualizations</span>
            </h3>
            <p className="text-[11px] text-[var(--text-muted)] mb-3">
              Investigate cryptographic exposure across attack surfaces, system topology, and migration horizon.
            </p>
            <div className="space-y-2 text-xs">
              <Link
                href="/mosca"
                className="flex items-center justify-between p-2 rounded bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] border border-[var(--border-subtle)] transition-colors"
              >
                <span>Mosca Quantum Horizon Scatter</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              </Link>
              <Link
                href="/graph"
                className="flex items-center justify-between p-2 rounded bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] border border-[var(--border-subtle)] transition-colors"
              >
                <span>3D Spatial Estate Topology</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              </Link>
              <Link
                href="/heatmap"
                className="flex items-center justify-between p-2 rounded bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] border border-[var(--border-subtle)] transition-colors"
              >
                <span>Surface × Family Threat Matrix</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              </Link>
              <Link
                href="/certificates"
                className="flex items-center justify-between p-2 rounded bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] border border-[var(--border-subtle)] transition-colors"
              >
                <span>X.509 Certificate Expiry Horizon</span>
                <ArrowRight className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              </Link>
            </div>
          </div>

          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4">
            <h3 className="text-xs font-bold text-[var(--text-primary)] uppercase flex items-center gap-2 mb-2">
              <FileCheck className="w-4 h-4 text-[var(--crypto-safe-classical)]" />
              <span>Compliance & Reporting</span>
            </h3>
            <p className="text-[11px] text-[var(--text-muted)] mb-3">
              Standard-format CycloneDX 1.6 Cryptographic Bill of Materials (CBOM) export.
            </p>
            <CbomExportButton scanId={scan.id} />
          </div>
        </div>
      </div>

      {/* Proof & Tour Modals (M6) */}
      <AttestationModal
        isOpen={isAttestationOpen}
        onClose={() => setIsAttestationOpen(false)}
        scanId={scan.id}
      />
      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />
      <DemoTourModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onOpenAttestation={() => setIsAttestationOpen(true)}
        onOpenBenchmark={() => setIsBenchmarkOpen(true)}
      />
    </div>
  );
}
