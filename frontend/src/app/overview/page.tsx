'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../lib/store';
import { mockScans, mockFindings } from '../../mocks/data';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { CbomExportButton } from '../../components/CbomExportButton';
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
} from 'lucide-react';
import Link from 'next/link';

export default function OverviewPage() {
  const router = useRouter();
  const { activeScanId, openDrawer } = useAppStore();
  const scan = mockScans.find((s) => s.id === activeScanId) || mockScans[0];

  // Derive urgent counts
  const hndlCount = useMemo(() => mockFindings.filter((f) => f.risk.hndl).length, []);
  const brokenCount = useMemo(() => mockFindings.filter((f) => f.risk.classicallyBroken).length, []);
  const topRisks = useMemo(
    () => [...mockFindings].sort((a, b) => b.risk.score - a.risk.score).slice(0, 5),
    []
  );

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
            Scan ID: {scan.id} · Completed in {scan.stats.seconds}s · Policy: {scan.policyId}
          </p>
        </div>
        <div className="flex items-center gap-2">
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

      {/* Primary Threat Bento Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Critical */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3.5 rounded-lg flex flex-col justify-between">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Critical Risks</span>
          <div className="text-2xl font-bold text-[var(--band-critical)] mt-2 num-tabular">
            {scan.bands.critical}
          </div>
          <span className="text-[10px] text-[var(--text-muted)] mt-1">Score $\ge 60$</span>
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
            {scan.stats.files.toLocaleString()}
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Analyzed Volume</span>
          <div className="font-bold text-[var(--text-primary)] text-base mt-1 num-tabular">
            {(scan.stats.bytes / 1024 / 1024).toFixed(2)} MB
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Scanner Speed</span>
          <div className="font-bold text-[var(--crypto-pqc)] text-base mt-1 num-tabular">
            {scan.stats.mbPerSec.toFixed(1)} MB/s
          </div>
        </div>
        <div>
          <span className="text-[10px] text-[var(--text-muted)] uppercase">Prefilter Skips</span>
          <div className="font-bold text-[var(--text-muted)] text-base mt-1 num-tabular">
            {scan.stats.skippedPrefilter} Non-crypto
          </div>
        </div>
      </div>

      {/* Two Column Layout: Top-5 Urgent Risks + Direct Console Links */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Top Urgent Risks */}
        <div className="lg:col-span-2 bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
            <span className="font-bold text-xs text-[var(--text-primary)] uppercase flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[var(--crypto-shor)]" />
              <span>Highest Priority Cryptographic Findings (Click to Inspect)</span>
            </span>
            <Link
              href="/inventory"
              className="text-xs text-[var(--crypto-pqc)] hover:underline flex items-center gap-1"
            >
              <span>View All 10,000+</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-2">
            {topRisks.map((f) => {
              const cls = classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken);
              return (
                <div
                  key={f.id}
                  onClick={() => openDrawer(f)}
                  className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--border-focus)] transition-all cursor-pointer flex items-center justify-between gap-3 text-xs"
                >
                  <div className="flex items-center gap-3">
                    <CryptoBadge
                      semanticClass={cls}
                      displayName={f.displayName}
                      needsReview={f.risk.needsReview}
                      size="sm"
                    />
                    <div className="truncate max-w-sm">
                      <div className="text-[var(--text-primary)] font-semibold truncate">
                        {f.location.path}:{f.location.line}
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] truncate">
                        {f.risk.reason}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <RiskBandBadge band={f.risk.band} score={f.risk.score} />
                      <div className="text-[10px] text-[var(--text-muted)] mt-0.5 num-tabular">
                        M = {f.risk.moscaMargin}y
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Col: Interactive Modules Launcher */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-3 text-xs">
          <div className="font-bold uppercase tracking-wider text-[var(--text-primary)] border-b border-[var(--border-subtle)] pb-2 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-[var(--crypto-pqc)]" />
            <span>Interactive Analysis Tools</span>
          </div>

          <div className="space-y-2">
            <Link
              href="/mosca"
              className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--crypto-pqc)] transition-colors block group"
            >
              <div className="flex items-center justify-between text-[var(--text-primary)] font-bold">
                <span className="text-[var(--crypto-pqc)]">Mosca Quantum Matrix</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                Draggable CRQC horizon line ($Z$), dynamic re-banding, and quantum migration urgency.
              </p>
            </Link>

            <Link
              href="/inventory"
              className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--crypto-safe-classical)] transition-colors block group"
            >
              <div className="flex items-center justify-between text-[var(--text-primary)] font-bold">
                <span className="text-[var(--crypto-safe-classical)]">High-Density Inventory</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                Virtualized 60 fps catalog with multi-facet filters across 10,000+ discoveries.
              </p>
            </Link>

            <Link
              href="/graph"
              className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--crypto-grover)] transition-colors block group"
            >
              <div className="flex items-center justify-between text-[var(--text-primary)] font-bold">
                <span className="text-[var(--crypto-grover)]">3D Crypto Estate Graph</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                Spatial node clustering (System $\to$ File $\to$ Asset) with risk bloom shaders.
              </p>
            </Link>

            <Link
              href="/plan"
              className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--crypto-pqc)] transition-colors block group"
            >
              <div className="flex items-center justify-between text-[var(--text-primary)] font-bold">
                <span className="text-[var(--crypto-pqc)]">Remediation Migration Plan</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </div>
              <p className="text-[11px] text-[var(--text-muted)] mt-1">
                System-grouped target transitions with wire-size and CPU op latency deltas.
              </p>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
