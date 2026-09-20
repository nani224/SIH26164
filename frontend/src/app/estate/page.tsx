'use client';

import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  fetchEstateSummary,
  fetchTargets,
  createTarget,
  patchTarget,
  deleteTarget,
  scanTargetNow,
  fetchPolicies,
} from '../../lib/api';
import type { Target, TargetKind, TargetCreate, TargetPatch, Policy } from '../../types/crypto';
import { AuditVerifySeal } from '../../components/AuditVerifySeal';
import {
  Shield,
  Layers,
  Activity,
  AlertTriangle,
  Radio,
  GitBranch,
  Folder,
  Server,
  Play,
  RotateCw,
  Plus,
  Search,
  Filter,
  Trash2,
  Edit2,
  ExternalLink,
  CheckCircle2,
  Clock,
  X,
  Sparkles,
  GitPullRequest,
  Terminal,
} from 'lucide-react';

export default function EstatePage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [kindFilter, setKindFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [editingTarget, setEditingTarget] = useState<Target | null>(null);
  const [deletingTarget, setDeletingTarget] = useState<Target | null>(null);
  const [scanningTargetId, setScanningTargetId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ text: string; scanId?: string } | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  // Form states for Create/Edit
  const [formData, setFormData] = useState<TargetCreate>({
    name: '',
    kind: 'repo',
    uri: '',
    policyId: 'policy-default-defense',
    schedule: '@daily',
    enabled: true,
  });

  // Queries with 30s auto-refresh for continuous telemetry
  const {
    data: estateSummary,
    isLoading: summaryLoading,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ['estateSummary'],
    queryFn: async () => {
      const data = await fetchEstateSummary();
      setLastRefreshedAt(new Date());
      return data;
    },
    refetchInterval: 30000,
  });

  const {
    data: targets = [],
    isLoading: targetsLoading,
    refetch: refetchTargets,
  } = useQuery({
    queryKey: ['targets'],
    queryFn: fetchTargets,
    refetchInterval: 30000,
  });

  const { data: policies = [] } = useQuery({
    queryKey: ['policies'],
    queryFn: fetchPolicies,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: createTarget,
    onSuccess: (newTarget) => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      setIsRegisterOpen(false);
      resetForm();
      setToastMessage({ text: `Target "${newTarget.name}" registered successfully.` });
    },
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: TargetPatch }) => patchTarget(id, patch),
    onSuccess: (updatedTarget) => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      setEditingTarget(null);
      resetForm();
      setToastMessage({ text: `Target "${updatedTarget.name}" updated successfully.` });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteTarget(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      setDeletingTarget(null);
      setToastMessage({ text: 'Target removed from estate monitoring.' });
    },
  });

  const scanNowMutation = useMutation({
    mutationFn: (id: string) => scanTargetNow(id),
    onMutate: (id) => {
      setScanningTargetId(id);
    },
    onSuccess: (scan, targetId) => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      setScanningTargetId(null);
      setToastMessage({
        text: `Active scan initiated (${scan.id}).`,
        scanId: scan.id,
      });
    },
    onError: () => {
      setScanningTargetId(null);
    },
  });

  // Auto-clear toast
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => setToastMessage(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  const resetForm = () => {
    setFormData({
      name: '',
      kind: 'repo',
      uri: '',
      policyId: policies[0]?.id || 'policy-default-defense',
      schedule: '@daily',
      enabled: true,
    });
  };

  const handleOpenEdit = (target: Target) => {
    setEditingTarget(target);
    setFormData({
      name: target.name,
      kind: target.kind,
      uri: target.uri,
      policyId: target.policyId,
      schedule: target.schedule,
      enabled: target.enabled,
    });
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.uri.trim()) return;
    createMutation.mutate(formData);
  };

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTarget) return;
    patchMutation.mutate({
      id: editingTarget.id,
      patch: {
        name: formData.name,
        policyId: formData.policyId,
        schedule: formData.schedule,
        enabled: formData.enabled,
      },
    });
  };

  // Filtered targets
  const filteredTargets = useMemo(() => {
    return targets.filter((target) => {
      const matchesSearch =
        target.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        target.uri.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesKind = kindFilter === 'all' || target.kind === kindFilter;
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'enabled' && target.enabled) ||
        (statusFilter === 'disabled' && !target.enabled);
      return matchesSearch && matchesKind && matchesStatus;
    });
  }, [targets, searchQuery, kindFilter, statusFilter]);

  // Helper for relative time
  const formatRelativeTime = (isoString?: string | null) => {
    if (!isoString) return 'Never';
    const now = new Date();
    const then = new Date(isoString);
    const diffSec = Math.floor((now.getTime() - then.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  };

  // Helper for Kind icon
  const getKindIcon = (kind: TargetKind) => {
    switch (kind) {
      case 'repo':
        return <GitBranch className="w-3.5 h-3.5" />;
      case 'path':
        return <Folder className="w-3.5 h-3.5" />;
      case 'endpoint':
        return <Radio className="w-3.5 h-3.5" />;
      default:
        return <Server className="w-3.5 h-3.5" />;
    }
  };

  const getKindColorClass = (kind: TargetKind) => {
    switch (kind) {
      case 'repo':
        return 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border-[var(--crypto-pqc-border)]';
      case 'path':
        return 'bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border-[var(--crypto-grover-border)]';
      case 'endpoint':
        return 'bg-[var(--crypto-classical-bg)] text-[var(--crypto-classical)] border-[var(--crypto-classical-border)]';
      default:
        return 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
    }
  };

  const isLoading = summaryLoading || targetsLoading;

  if (isLoading && targets.length === 0) {
    return (
      <div className="space-y-6 font-mono animate-pulse" aria-label="Loading estate console">
        {/* Header Skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4 min-h-[72px]">
          <div>
            <div className="h-3 w-48 bg-[var(--surface-raised)] rounded mb-2" />
            <div className="h-6 w-72 bg-[var(--surface-raised)] rounded" />
          </div>
          <div className="flex items-center gap-2">
            <div className="h-8 w-32 bg-[var(--surface-raised)] rounded" />
          </div>
        </div>

        {/* Bento Metrics Skeleton */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 min-h-[110px]">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg h-[110px] flex flex-col justify-between"
            >
              <div className="h-3 w-20 bg-[var(--surface-raised)] rounded" />
              <div className="h-8 w-16 bg-[var(--surface-raised)] rounded" />
              <div className="h-2 w-24 bg-[var(--surface-raised)] rounded" />
            </div>
          ))}
        </div>

        {/* Table Skeleton */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 min-h-[300px]">
          <div className="h-4 w-40 bg-[var(--surface-raised)] rounded mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-[var(--surface-raised)] rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Toast Notification */}
      {toastMessage && (
        <aside
          aria-label="Estate Notification"
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border border-[var(--crypto-pqc-border)] bg-[var(--surface-overlay)] text-[var(--text-primary)] shadow-lg backdrop-blur-md"
        >
          <CheckCircle2 className="w-5 h-5 text-[var(--crypto-pqc)] shrink-0" />
          <div className="text-xs">
            <p className="font-semibold">{toastMessage.text}</p>
            {toastMessage.scanId && (
              <Link
                href={`/overview?scanId=${toastMessage.scanId}`}
                className="underline text-[var(--crypto-pqc)] hover:text-opacity-80"
              >
                View Scan Results &rarr;
              </Link>
            )}
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="ml-2 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            aria-label="Close notification"
          >
            <X className="w-4 h-4" />
          </button>
        </aside>
      )}

      {/* Screen Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-widest text-[var(--crypto-pqc)] font-bold">
              Continuous Operation Monitor
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--crypto-pqc)] animate-pulse" />
              Live Telemetry (30s polling)
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1">
            Cryptographic Estate Console
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Continuous posture monitoring across repositories, binary paths, and TLS/SSH endpoints.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => {
              refetchSummary();
              refetchTargets();
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] transition-colors"
            title="Refresh estate telemetry"
            aria-label="Refresh telemetry"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => {
              resetForm();
              setIsRegisterOpen(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded text-xs font-semibold bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 transition-opacity shadow-sm"
            aria-label="Register Target"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Register Target</span>
          </button>
        </div>
      </header>

      {/* Top Bento Grid Metrics */}
      <section aria-label="Estate Health Metrics" className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Total Targets */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--border-prominent)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Total Targets</span>
            <Layers className="w-4 h-4 text-[var(--crypto-classical)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              {estateSummary?.totalTargets ?? targets.length}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] flex items-center gap-2">
            <span>{targets.filter((t) => t.enabled).length} Active</span>
            <span>&bull;</span>
            <span>{targets.filter((t) => !t.enabled).length} Paused</span>
          </div>
        </div>

        {/* Total Scans Completed */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--border-prominent)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Total Scans</span>
            <Activity className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              {estateSummary?.totalScans ?? 0}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Last sync: {lastRefreshedAt.toLocaleTimeString()}</span>
          </div>
        </div>

        {/* Critical Findings */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-shor-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Critical Findings</span>
            <AlertTriangle className="w-4 h-4 text-[var(--crypto-shor)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-shor)]">
              {estateSummary?.criticalFindings ?? 0}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] flex items-center justify-between">
            <span>{estateSummary?.totalFindings ?? 0} total findings</span>
            <Link
              href="/inventory?band=critical"
              className="text-[var(--crypto-shor)] hover:underline flex items-center gap-0.5"
            >
              Inspect &rarr;
            </Link>
          </div>
        </div>

        {/* PQC Readiness Score Gauge */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-pqc-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">PQC Readiness</span>
            <Sparkles className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-pqc)]">
              {estateSummary?.pqcReadinessScore ?? 0}%
            </span>
            <span className="text-[10px] text-[var(--text-muted)]">Target: 100%</span>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-[var(--surface-raised)] rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-[var(--crypto-pqc)] h-full transition-all duration-500 rounded-full"
              style={{ width: `${Math.min(estateSummary?.pqcReadinessScore ?? 0, 100)}%` }}
            />
          </div>
        </div>

        {/* Active Alerts */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-grover-border)] transition-colors col-span-2 lg:col-span-1">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Active Alerts</span>
            <Radio className="w-4 h-4 text-[var(--crypto-grover)]" />
          </div>
          <div className="my-2 flex items-center justify-between">
            <span
              className={`text-2xl sm:text-3xl font-bold ${
                (estateSummary?.activeAlerts ?? 0) > 0
                  ? 'text-[var(--crypto-grover)]'
                  : 'text-[var(--text-primary)]'
              }`}
            >
              {estateSummary?.activeAlerts ?? 0}
            </span>
            {(estateSummary?.activeAlerts ?? 0) > 0 && (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border border-[var(--crypto-grover-border)]">
                Unresolved
              </span>
            )}
          </div>
          <div className="text-[10px] flex items-center justify-between text-[var(--text-secondary)]">
            <span>Signals & downgrade probes</span>
            <Link href="/alerts" className="text-[var(--crypto-grover)] hover:underline">
              View Feed &rarr;
            </Link>
          </div>
        </div>
      </section>

      {/* Targets Management Section */}
      <section
        aria-labelledby="monitored-targets-heading"
        className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden shadow-sm"
      >
        {/* Table Filters & Toolbar */}
        <div className="p-4 border-b border-[var(--border-subtle)] flex flex-col md:flex-row md:items-center justify-between gap-3 bg-[var(--surface-overlay)]">
          <div className="flex items-center gap-2">
            <h2 id="monitored-targets-heading" className="text-sm font-bold text-[var(--text-primary)]">
              Monitored Cryptographic Targets
            </h2>
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
              {filteredTargets.length} / {targets.length}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Search targets or URIs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs w-48 sm:w-60"
                aria-label="Search targets"
              />
            </div>

            {/* Kind Filter */}
            <div className="flex items-center gap-1">
              <label htmlFor="kind-filter" className="text-[var(--text-muted)] sr-only">
                Filter by Kind
              </label>
              <select
                id="kind-filter"
                value={kindFilter}
                onChange={(e) => setKindFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs"
              >
                <option value="all">All Kinds</option>
                <option value="repo">Repo</option>
                <option value="path">Path</option>
                <option value="endpoint">Endpoint</option>
              </select>
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-1">
              <label htmlFor="status-filter" className="text-[var(--text-muted)] sr-only">
                Filter by Status
              </label>
              <select
                id="status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2.5 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs"
              >
                <option value="all">All Statuses</option>
                <option value="enabled">Active Only</option>
                <option value="disabled">Paused Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Target Table */}
        {filteredTargets.length === 0 ? (
          <div className="p-12 text-center text-[var(--text-muted)]">
            <Layers className="w-8 h-8 mx-auto mb-3 opacity-40 text-[var(--text-muted)]" />
            <p className="text-sm font-semibold text-[var(--text-secondary)]">No targets matched criteria</p>
            <p className="text-xs mt-1">Adjust your filters or register a new target to start continuous monitoring.</p>
            <button
              onClick={() => {
                resetForm();
                setIsRegisterOpen(true);
              }}
              className="mt-4 px-3 py-1.5 rounded text-xs font-semibold bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 inline-flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Register Target</span>
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse" role="table" aria-label="Cryptographic Targets">
              <thead>
                <tr className="border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)] uppercase text-[10px] tracking-wider">
                  <th scope="col" className="py-3 px-4 font-semibold">Target & URI</th>
                  <th scope="col" className="py-3 px-3 font-semibold">Kind</th>
                  <th scope="col" className="py-3 px-3 font-semibold">Policy</th>
                  <th scope="col" className="py-3 px-3 font-semibold">Schedule</th>
                  <th scope="col" className="py-3 px-3 font-semibold">Last Scan</th>
                  <th scope="col" className="py-3 px-3 font-semibold">Status</th>
                  <th scope="col" className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {filteredTargets.map((target) => {
                  const isScanningThis = scanningTargetId === target.id;
                  return (
                    <tr
                      key={target.id}
                      className="hover:bg-[var(--surface-raised)] transition-colors group"
                    >
                      {/* Target Name & URI */}
                      <td className="py-3 px-4">
                        <div className="flex items-start gap-2.5">
                          <div
                            className={`p-1.5 rounded border shrink-0 mt-0.5 ${getKindColorClass(
                              target.kind
                            )}`}
                          >
                            {getKindIcon(target.kind)}
                          </div>
                          <div className="min-w-0">
                            <div className="font-semibold text-[var(--text-primary)] truncate">
                              {target.name}
                            </div>
                            <div className="text-[11px] text-[var(--text-muted)] truncate max-w-xs sm:max-w-md font-mono">
                              {target.uri}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Kind Badge */}
                      <td className="py-3 px-3">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${getKindColorClass(
                            target.kind
                          )}`}
                        >
                          {target.kind.toUpperCase()}
                        </span>
                      </td>

                      {/* Policy */}
                      <td className="py-3 px-3 text-[var(--text-secondary)]">
                        <span className="font-mono text-[11px]">
                          {target.policyId.replace('policy-', '')}
                        </span>
                      </td>

                      {/* Schedule */}
                      <td className="py-3 px-3 text-[var(--text-secondary)]">
                        <span className="px-2 py-0.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[10px] font-mono">
                          {target.schedule}
                        </span>
                      </td>

                      {/* Last Scan */}
                      <td className="py-3 px-3 text-[var(--text-secondary)]">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-[var(--text-muted)]" />
                          <span>{formatRelativeTime(target.lastScanAt)}</span>
                        </div>
                        {target.lastScanId && (
                          <Link
                            href={`/overview?scanId=${target.lastScanId}`}
                            className="text-[10px] text-[var(--crypto-classical)] hover:underline flex items-center gap-0.5 mt-0.5"
                          >
                            <span>{target.lastScanId.substring(0, 11)}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-3">
                        {target.enabled ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--crypto-pqc)]" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] bg-[var(--surface-raised)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)]" />
                            Paused
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Scan Now */}
                          <button
                            onClick={() => scanNowMutation.mutate(target.id)}
                            disabled={isScanningThis}
                            className="p-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-base)] text-[var(--crypto-pqc)] hover:bg-[var(--crypto-pqc-bg)] hover:border-[var(--crypto-pqc-border)] transition-colors disabled:opacity-50"
                            title="Scan target immediately"
                            aria-label={`Scan target ${target.name}`}
                          >
                            <Play
                              className={`w-3.5 h-3.5 ${isScanningThis ? 'animate-spin' : ''}`}
                            />
                          </button>

                          {/* View Drift */}
                          <Link
                            href={`/drift?targetId=${target.id}`}
                            className="p-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-base)] text-[var(--crypto-classical)] hover:bg-[var(--crypto-classical-bg)] hover:border-[var(--crypto-classical-border)] transition-colors"
                            title="View drift comparison"
                            aria-label={`View drift for ${target.name}`}
                          >
                            <Activity className="w-3.5 h-3.5" />
                          </Link>

                          {/* Edit Target */}
                          <button
                            onClick={() => handleOpenEdit(target)}
                            className="p-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-base)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] transition-colors"
                            title="Edit target"
                            aria-label={`Edit target ${target.name}`}
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          {/* Delete Target */}
                          <button
                            onClick={() => setDeletingTarget(target)}
                            className="p-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-base)] text-[var(--crypto-shor)] hover:bg-[var(--crypto-shor-bg)] hover:border-[var(--crypto-shor-border)] transition-colors"
                            title="Delete target"
                            aria-label={`Delete target ${target.name}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* CI/CD Pipeline Surfaces & Continuous Inspection Gates */}
      <section aria-label="CI/CD Pipeline Integrations" className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
          <div>
            <div className="flex items-center gap-1.5 text-xs text-[var(--crypto-pqc)] font-bold mb-0.5">
              <GitPullRequest className="w-3.5 h-3.5" />
              <span>CI/CD PIPELINE SURFACES & AUTOMATION</span>
            </div>
            <h2 className="text-base font-bold text-[var(--text-primary)]">
              Continuous Cryptographic Gates & PR Inspection
            </h2>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Automated precision gate enforcement for pull requests and CI pipelines.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold">
              PRECISION GATE ACTIVE
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* GitHub Actions Card */}
          <div className="p-4 rounded-lg bg-[var(--surface-base)] border border-[var(--border-subtle)] space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <GitBranch className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <span className="font-bold text-sm text-[var(--text-primary)]">GitHub Actions</span>
              </div>
              <span
                className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold"
                title="Status: Action ready; webhook daemon runner under continuous development"
              >
                REUSABLE WORKFLOW
              </span>
            </div>

            <p className="text-[11px] text-[var(--text-muted)]">
              Reusable action <code className="text-[var(--text-primary)]">.github/workflows/ecdat-scan-reusable.yml</code> executes deterministic scans on PR events and fails PR checks on CRITICAL findings.
            </p>

            <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] font-mono text-[10px] text-[var(--text-secondary)] space-y-1">
              <div>uses: nani224/SIH26164/.github/actions/ecdat-scan@main</div>
              <div className="text-[var(--text-muted)]">with: fail_on: critical | upload_cbom: true</div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-[var(--text-secondary)] pt-1">
              <span className="text-[var(--band-medium)] font-bold">
                [Roadmap: GitHub Actions / GitLab CI runner pending]
              </span>
              <span className="text-[var(--crypto-pqc)] font-semibold">Exit Code 1 on Critical</span>
            </div>
          </div>

          {/* GitLab CI Card */}
          <div className="p-4 rounded-lg bg-[var(--surface-base)] border border-[var(--border-subtle)] space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-[var(--crypto-classical)]" />
                <span className="font-bold text-sm text-[var(--text-primary)]">GitLab CI Runner</span>
              </div>
              <span
                className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--crypto-classical-bg)] border border-[var(--crypto-classical-border)] text-[var(--crypto-classical)] font-bold"
                title="Status: Air-gapped container runner pending continuous daemon hook"
              >
                CONTAINERIZED
              </span>
            </div>

            <p className="text-[11px] text-[var(--text-muted)]">
              Air-gapped container runner executing offline binary and repository analysis within isolated sovereign enclave environments.
            </p>

            <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] font-mono text-[10px] text-[var(--text-secondary)] space-y-1">
              <div>image: ghcr.io/nani224/ecdat-scanner:latest</div>
              <div className="text-[var(--text-muted)]">script: - ecdat scan --offline --format sarif,cbom</div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-[var(--text-secondary)] pt-1">
              <span className="text-[var(--band-medium)] font-bold">
                [Roadmap: GitHub Actions / GitLab CI runner pending]
              </span>
              <span className="text-[var(--crypto-classical)] font-semibold">Air-gapped Sovereign</span>
            </div>
          </div>
        </div>
      </section>

      {/* Cryptographic Audit Log Hash-Chain Integrity Seal */}
      <section aria-label="Cryptographic Audit Integrity" className="mt-2">
        <AuditVerifySeal variant="card" />
      </section>

      {/* Register Target Modal */}
      {isRegisterOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="register-target-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg bg-[var(--surface-card)] border border-[var(--border-prominent)] rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-4 border-b border-[var(--border-subtle)] bg-[var(--surface-overlay)]">
              <div className="flex items-center gap-2">
                <Plus className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <h2 id="register-target-title" className="text-sm font-bold text-[var(--text-primary)]">
                  Register Cryptographic Target
                </h2>
              </div>
              <button
                onClick={() => setIsRegisterOpen(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-4 space-y-4 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Target Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Core Payment Gateway"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                    Kind *
                  </label>
                  <select
                    value={formData.kind}
                    onChange={(e) => setFormData({ ...formData, kind: e.target.value as TargetKind })}
                    className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                  >
                    <option value="repo">Repository (Git)</option>
                    <option value="path">Filesystem / Binary Path</option>
                    <option value="endpoint">Live TLS / SSH Endpoint</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                    Schedule *
                  </label>
                  <select
                    value={formData.schedule}
                    onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                    className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                  >
                    <option value="@hourly">Hourly (@hourly)</option>
                    <option value="@daily">Daily (@daily)</option>
                    <option value="0 */6 * * *">Every 6 hours</option>
                    <option value="@weekly">Weekly (@weekly)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Target URI / Path / Host *
                </label>
                <input
                  type="text"
                  required
                  placeholder={
                    formData.kind === 'repo'
                      ? 'https://github.com/org/repo.git'
                      : formData.kind === 'path'
                      ? '/opt/production/bin/app'
                      : 'api.payments.internal:443'
                  }
                  value={formData.uri}
                  onChange={(e) => setFormData({ ...formData, uri: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] font-mono"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Cryptographic Policy
                </label>
                <select
                  value={formData.policyId}
                  onChange={(e) => setFormData({ ...formData, policyId: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                >
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.id})
                    </option>
                  ))}
                  {policies.length === 0 && (
                    <option value="policy-default-defense">Default Defense Policy</option>
                  )}
                </select>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="target-enabled-cb"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  className="rounded border-[var(--border-subtle)] text-[var(--crypto-pqc)] focus:ring-0"
                />
                <label htmlFor="target-enabled-cb" className="text-[var(--text-primary)] select-none">
                  Enable continuous monitoring immediately
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-subtle)]">
                <button
                  type="button"
                  onClick={() => setIsRegisterOpen(false)}
                  className="px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-1.5 rounded font-semibold bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Registering...' : 'Register Target'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Target Modal */}
      {editingTarget && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-target-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        >
          <div className="w-full max-w-lg bg-[var(--surface-card)] border border-[var(--border-prominent)] rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between p-4 border-b border-[var(--border-subtle)] bg-[var(--surface-overlay)]">
              <div className="flex items-center gap-2">
                <Edit2 className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <h2 id="edit-target-title" className="text-sm font-bold text-[var(--text-primary)]">
                  Edit Target: {editingTarget.name}
                </h2>
              </div>
              <button
                onClick={() => setEditingTarget(null)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                aria-label="Close modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="p-4 space-y-4 text-xs">
              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Target Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                />
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Schedule
                </label>
                <select
                  value={formData.schedule}
                  onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                >
                  <option value="@hourly">Hourly (@hourly)</option>
                  <option value="@daily">Daily (@daily)</option>
                  <option value="0 */6 * * *">Every 6 hours</option>
                  <option value="@weekly">Weekly (@weekly)</option>
                </select>
              </div>

              <div>
                <label className="block text-[var(--text-secondary)] font-semibold mb-1">
                  Cryptographic Policy
                </label>
                <select
                  value={formData.policyId}
                  onChange={(e) => setFormData({ ...formData, policyId: e.target.value })}
                  className="w-full px-3 py-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                >
                  {policies.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="edit-target-enabled-cb"
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  className="rounded border-[var(--border-subtle)] text-[var(--crypto-pqc)] focus:ring-0"
                />
                <label htmlFor="edit-target-enabled-cb" className="text-[var(--text-primary)] select-none">
                  Target is enabled for continuous scanning
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-subtle)]">
                <button
                  type="button"
                  onClick={() => setEditingTarget(null)}
                  className="px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={patchMutation.isPending}
                  className="px-4 py-1.5 rounded font-semibold bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 disabled:opacity-50"
                >
                  {patchMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingTarget && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-target-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
        >
          <div className="w-full max-w-md bg-[var(--surface-card)] border border-[var(--crypto-shor-border)] rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="p-4 border-b border-[var(--border-subtle)] flex items-center gap-2 text-[var(--crypto-shor)]">
              <Trash2 className="w-5 h-5" />
              <h2 id="delete-target-title" className="text-sm font-bold">
                Delete Target
              </h2>
            </div>
            <div className="p-4 space-y-2 text-xs text-[var(--text-secondary)]">
              <p>
                Are you sure you want to remove <strong className="text-[var(--text-primary)]">{deletingTarget.name}</strong> from continuous monitoring?
              </p>
              <p className="text-[11px] text-[var(--text-muted)]">
                Historical scan logs and CBOM snapshots will be preserved, but automated periodic scans will cease immediately.
              </p>
            </div>
            <div className="p-4 border-t border-[var(--border-subtle)] flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeletingTarget(null)}
                className="px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deletingTarget.id)}
                className="px-4 py-1.5 rounded font-semibold bg-[var(--crypto-shor)] text-white hover:opacity-90 disabled:opacity-50 text-xs"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
