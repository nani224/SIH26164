'use client';

import { useState, useMemo, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchTargets, fetchTargetDrift } from '../../lib/api';
import { useAppStore } from '../../lib/store';
import type { Finding, RiskBand, DriftChangedItem } from '../../types/crypto';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import {
  GitCompare,
  PlusCircle,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Layers,
  Search,
  ExternalLink,
  Filter,
  Shield,
  Clock,
  Sparkles,
  ChevronRight,
} from 'lucide-react';

function DriftContent() {
  const searchParams = useSearchParams();
  const initialTargetId = searchParams.get('targetId');
  const { openDrawer } = useAppStore();

  const [selectedTargetId, setSelectedTargetId] = useState<string>(initialTargetId || '');
  const [activeTab, setActiveTab] = useState<'all' | 'added' | 'resolved' | 'changed'>('all');
  const [searchFilter, setSearchFilter] = useState('');

  // Fetch targets for dropdown
  const { data: targets = [], isLoading: targetsLoading } = useQuery({
    queryKey: ['targets'],
    queryFn: fetchTargets,
  });

  // Default to first target if not selected
  const activeTargetId = selectedTargetId || targets[0]?.id || '';
  const currentTarget = targets.find((t) => t.id === activeTargetId);

  // Fetch drift for selected target
  const {
    data: drift,
    isLoading: driftLoading,
    refetch: refetchDrift,
  } = useQuery({
    queryKey: ['drift', activeTargetId],
    queryFn: () => fetchTargetDrift(activeTargetId),
    enabled: Boolean(activeTargetId),
  });

  const added = useMemo(() => drift?.added ?? [], [drift]);
  const resolved = useMemo(() => drift?.resolved ?? [], [drift]);
  const changed = useMemo(() => drift?.changed ?? [], [drift]);
  const summary = drift?.summary ?? {
    addedCount: added.length,
    resolvedCount: resolved.length,
    changedCount: changed.length,
    netRiskDelta: 0,
  };

  // Filtered items based on search
  const filteredAdded = useMemo(() => {
    if (!searchFilter.trim()) return added;
    const q = searchFilter.toLowerCase();
    return added.filter(
      (f) =>
        f.displayName.toLowerCase().includes(q) ||
        f.family?.toLowerCase().includes(q) ||
        f.location?.path.toLowerCase().includes(q)
    );
  }, [added, searchFilter]);

  const filteredResolved = useMemo(() => {
    if (!searchFilter.trim()) return resolved;
    const q = searchFilter.toLowerCase();
    return resolved.filter(
      (f) =>
        f.displayName.toLowerCase().includes(q) ||
        f.family?.toLowerCase().includes(q) ||
        f.location?.path.toLowerCase().includes(q)
    );
  }, [resolved, searchFilter]);

  const filteredChanged = useMemo(() => {
    if (!searchFilter.trim()) return changed;
    const q = searchFilter.toLowerCase();
    return changed.filter(
      (c) =>
        c.finding.displayName.toLowerCase().includes(q) ||
        c.finding.family?.toLowerCase().includes(q) ||
        c.finding.location?.path.toLowerCase().includes(q)
    );
  }, [changed, searchFilter]);

  const isLoading = targetsLoading || driftLoading;

  if (isLoading && !drift) {
    return (
      <div className="space-y-6 font-mono animate-pulse" aria-label="Loading drift comparison">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4 min-h-[72px]">
          <div>
            <div className="h-3 w-48 bg-[var(--surface-raised)] rounded mb-2" />
            <div className="h-6 w-72 bg-[var(--surface-raised)] rounded" />
          </div>
          <div className="h-8 w-44 bg-[var(--surface-raised)] rounded" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 min-h-[110px]">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg h-[110px]"
            />
          ))}
        </div>
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 h-[350px]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Screen Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-widest text-[var(--crypto-pqc)] font-bold">
              Continuous Differential Monitor
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--crypto-pqc)]" />
              Snapshot Diff Active
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1">
            Cryptographic Drift Analysis
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Two-snapshot cryptographic diff identifying added, resolved, and changed risk postures.
          </p>
        </div>

        {/* Target & Snapshot Selector */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Target Select */}
          <div className="flex items-center gap-1.5">
            <label htmlFor="target-select" className="text-[var(--text-muted)] sr-only">
              Target
            </label>
            <select
              id="target-select"
              value={activeTargetId}
              onChange={(e) => setSelectedTargetId(e.target.value)}
              className="px-3 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs font-semibold"
            >
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.kind})
                </option>
              ))}
            </select>
          </div>

          {/* Snapshot Comparison Badge */}
          {drift && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-secondary)]">
              <Clock className="w-3 h-3 text-[var(--text-muted)]" />
              <span className="font-mono">{drift.fromSnapshotId}</span>
              <ArrowRight className="w-3 h-3 text-[var(--text-muted)]" />
              <span className="font-mono font-bold text-[var(--text-primary)]">
                {drift.toSnapshotId}
              </span>
            </div>
          )}
        </div>
      </header>

      {/* Drift Summary Bento Cards */}
      <section aria-label="Drift Summary Metrics" className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Added Findings */}
        <div
          onClick={() => setActiveTab('added')}
          className={`cursor-pointer bg-[var(--surface-card)] border p-4 rounded-lg flex flex-col justify-between transition-colors ${
            activeTab === 'added'
              ? 'border-[var(--crypto-shor-border)] bg-[var(--crypto-shor-bg)]'
              : 'border-[var(--border-subtle)] hover:border-[var(--crypto-shor-border)]'
          }`}
          role="button"
          tabIndex={0}
          aria-label="Filter added findings"
        >
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Added Assets</span>
            <PlusCircle className="w-4 h-4 text-[var(--crypto-shor)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-shor)]">
              +{summary.addedCount}
            </span>
            <span className="text-xs text-[var(--text-muted)]">new findings</span>
          </div>
          <div className="text-[10px] text-[var(--crypto-shor)]">
            <span>Introduced since last snapshot</span>
          </div>
        </div>

        {/* Resolved Findings */}
        <div
          onClick={() => setActiveTab('resolved')}
          className={`cursor-pointer bg-[var(--surface-card)] border p-4 rounded-lg flex flex-col justify-between transition-colors ${
            activeTab === 'resolved'
              ? 'border-[var(--crypto-pqc-border)] bg-[var(--crypto-pqc-bg)]'
              : 'border-[var(--border-subtle)] hover:border-[var(--crypto-pqc-border)]'
          }`}
          role="button"
          tabIndex={0}
          aria-label="Filter resolved findings"
        >
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Resolved Assets</span>
            <CheckCircle2 className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-pqc)]">
              -{summary.resolvedCount}
            </span>
            <span className="text-xs text-[var(--text-muted)]">remediated</span>
          </div>
          <div className="text-[10px] text-[var(--crypto-pqc)]">
            <span>Purged or migrated to PQC</span>
          </div>
        </div>

        {/* Changed Bands */}
        <div
          onClick={() => setActiveTab('changed')}
          className={`cursor-pointer bg-[var(--surface-card)] border p-4 rounded-lg flex flex-col justify-between transition-colors ${
            activeTab === 'changed'
              ? 'border-[var(--crypto-grover-border)] bg-[var(--crypto-grover-bg)]'
              : 'border-[var(--border-subtle)] hover:border-[var(--crypto-grover-border)]'
          }`}
          role="button"
          tabIndex={0}
          aria-label="Filter changed findings"
        >
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Changed Bands</span>
            <AlertCircle className="w-4 h-4 text-[var(--crypto-grover)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-grover)]">
              {summary.changedCount}
            </span>
            <span className="text-xs text-[var(--text-muted)]">posture shifts</span>
          </div>
          <div className="text-[10px] text-[var(--crypto-grover)]">
            <span>Risk severity re-evaluated</span>
          </div>
        </div>

        {/* Net Risk Delta */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--border-prominent)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Net Risk Delta</span>
            {summary.netRiskDelta <= 0 ? (
              <TrendingDown className="w-4 h-4 text-[var(--crypto-pqc)]" />
            ) : (
              <TrendingUp className="w-4 h-4 text-[var(--crypto-shor)]" />
            )}
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span
              className={`text-2xl sm:text-3xl font-bold ${
                summary.netRiskDelta <= 0
                  ? 'text-[var(--crypto-pqc)]'
                  : 'text-[var(--crypto-shor)]'
              }`}
            >
              {summary.netRiskDelta > 0
                ? `+${summary.netRiskDelta}`
                : summary.netRiskDelta}
            </span>
            <span className="text-xs text-[var(--text-muted)]">pts</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] flex items-center gap-1">
            {summary.netRiskDelta <= 0 ? (
              <span>Overall exposure reduced</span>
            ) : (
              <span>Overall exposure increased</span>
            )}
          </div>
        </div>
      </section>

      {/* Filter Tabs & Search Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 text-xs" role="tablist">
          {(
            [
              { id: 'all', label: 'All Drift', count: added.length + resolved.length + changed.length },
              { id: 'added', label: 'Added', count: added.length },
              { id: 'resolved', label: 'Resolved', count: resolved.length },
              { id: 'changed', label: 'Changed', count: changed.length },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)]'
              }`}
              role="tab"
              aria-selected={activeTab === tab.id}
            >
              <span>{tab.label}</span>
              <span className="text-[10px] opacity-80">({tab.count})</span>
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search drift findings..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs w-56 sm:w-64"
            aria-label="Search drift findings"
          />
        </div>
      </div>

      {/* Drift Content Sections */}
      <div className="space-y-6">
        {/* 1. Added Findings Section */}
        {(activeTab === 'all' || activeTab === 'added') && (
          <section
            aria-labelledby="added-findings-heading"
            className="bg-[var(--surface-card)] border border-[var(--crypto-shor-border)] rounded-lg overflow-hidden shadow-sm"
          >
            <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--crypto-shor-bg)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PlusCircle className="w-4 h-4 text-[var(--crypto-shor)]" />
                <h2 id="added-findings-heading" className="text-xs font-bold text-[var(--crypto-shor)] uppercase tracking-wider">
                  Newly Added Cryptographic Assets ({filteredAdded.length})
                </h2>
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">
                Click any row to open Finding Drawer
              </span>
            </div>

            {filteredAdded.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                No newly added findings detected.
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-subtle)]">
                {filteredAdded.map((f) => (
                  <div
                    key={f.id}
                    onClick={() => openDrawer(f)}
                    className="p-3.5 hover:bg-[var(--surface-raised)] transition-colors cursor-pointer flex items-center justify-between gap-4 group"
                    role="button"
                    tabIndex={0}
                    aria-label={`Inspect finding ${f.displayName}`}
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-[var(--text-primary)] group-hover:text-[var(--crypto-shor)] transition-colors">
                          {f.displayName}
                        </span>
                        {f.risk && <RiskBandBadge band={f.risk.band} score={f.risk.score} />}
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                          {f.family}
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] truncate max-w-xl font-mono">
                        {f.location?.path}:{f.location?.line}
                      </div>
                      {f.recommendation && (
                        <div className="text-[11px] text-[var(--text-secondary)] flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-[var(--crypto-pqc)] shrink-0" />
                          <span className="truncate">{f.recommendation.action}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[var(--text-muted)] group-hover:text-[var(--text-primary)] shrink-0">
                      <span className="text-xs hidden sm:inline">Inspect</span>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 2. Resolved Findings Section */}
        {(activeTab === 'all' || activeTab === 'resolved') && (
          <section
            aria-labelledby="resolved-findings-heading"
            className="bg-[var(--surface-card)] border border-[var(--crypto-pqc-border)] rounded-lg overflow-hidden shadow-sm"
          >
            <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--crypto-pqc-bg)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <h2 id="resolved-findings-heading" className="text-xs font-bold text-[var(--crypto-pqc)] uppercase tracking-wider">
                  Resolved / Remediated Assets ({filteredResolved.length})
                </h2>
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">
                Successfully excised or upgraded
              </span>
            </div>

            {filteredResolved.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                No resolved findings in this diff snapshot.
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-subtle)]">
                {filteredResolved.map((f) => (
                  <div
                    key={f.id}
                    className="p-3.5 flex items-center justify-between gap-4 text-xs"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs line-through text-[var(--text-muted)]">
                          {f.displayName}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)] font-semibold">
                          Remediated
                        </span>
                        <span className="text-[10px] text-[var(--text-secondary)]">
                          {f.family}
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] font-mono truncate">
                        {f.location?.path}:{f.location?.line}
                      </div>
                    </div>

                    <div className="text-[11px] text-[var(--crypto-pqc)] font-semibold shrink-0">
                      Zero Threat Active
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* 3. Changed Findings Section */}
        {(activeTab === 'all' || activeTab === 'changed') && (
          <section
            aria-labelledby="changed-findings-heading"
            className="bg-[var(--surface-card)] border border-[var(--crypto-grover-border)] rounded-lg overflow-hidden shadow-sm"
          >
            <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--crypto-grover-bg)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-[var(--crypto-grover)]" />
                <h2 id="changed-findings-heading" className="text-xs font-bold text-[var(--crypto-grover)] uppercase tracking-wider">
                  Changed Severity Postures ({filteredChanged.length})
                </h2>
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">
                Click any row to open Finding Drawer
              </span>
            </div>

            {filteredChanged.length === 0 ? (
              <div className="p-8 text-center text-xs text-[var(--text-muted)]">
                No changed posture findings detected.
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-subtle)]">
                {filteredChanged.map((c) => (
                  <div
                    key={c.finding.id}
                    onClick={() => openDrawer(c.finding)}
                    className="p-3.5 hover:bg-[var(--surface-raised)] transition-colors cursor-pointer flex items-center justify-between gap-4 group text-xs"
                    role="button"
                    tabIndex={0}
                    aria-label={`Inspect changed finding ${c.finding.displayName}`}
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-xs text-[var(--text-primary)] group-hover:text-[var(--crypto-grover)] transition-colors">
                          {c.finding.displayName}
                        </span>

                        {/* Band Transition Badge */}
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[10px]">
                          <span className="uppercase text-[var(--text-muted)]">{c.fromBand}</span>
                          <ArrowRight className="w-3 h-3 text-[var(--text-muted)]" />
                          <span className="uppercase font-bold text-[var(--crypto-grover)]">
                            {c.toBand}
                          </span>
                        </div>
                      </div>
                      <div className="text-[11px] text-[var(--text-muted)] font-mono truncate">
                        {c.finding.location?.path}:{c.finding.location?.line}
                      </div>
                      {c.finding.risk?.reason && (
                        <div className="text-[11px] text-[var(--text-secondary)] truncate">
                          Reason: {c.finding.risk.reason}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-[var(--text-muted)] group-hover:text-[var(--text-primary)] shrink-0">
                      <span className="text-xs hidden sm:inline">Inspect</span>
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}

export default function DriftPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 font-mono text-xs text-[var(--text-muted)] animate-pulse">
          LOADING DRIFT TELEMETRY...
        </div>
      }
    >
      <DriftContent />
    </Suspense>
  );
}
