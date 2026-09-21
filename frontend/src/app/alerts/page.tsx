'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchAlerts, acknowledgeAlert, fetchProbes, fetchTargets } from '../../lib/api';
import { UnauthorizedState } from '../../components/UnauthorizedState';
import { isUnauthorizedError } from '../../lib/auth';
import type { Alert, AlertType, ProbeResult, RiskBand } from '../../types/crypto';
import {
  Bell,
  Radio,
  AlertTriangle,
  CheckCircle2,
  Shield,
  Clock,
  ArrowRight,
  RotateCw,
  Search,
  Filter,
  Server,
  Lock,
  Unlock,
  Sparkles,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [filterType, setFilterType] = useState<string>('all');
  const [filterAck, setFilterAck] = useState<string>('unack');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTargetId, setSelectedTargetId] = useState<string>('all');
  const [ackingAlertId, setAckingAlertId] = useState<string | null>(null);

  // Queries
  const {
    data: alerts = [],
    isLoading: alertsLoading,
    error: alertsError,
    refetch: refetchAlerts,
  } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => fetchAlerts(),
    refetchInterval: 30000,
  });

  const {
    data: probes = [],
    isLoading: probesLoading,
    error: probesError,
    refetch: refetchProbes,
  } = useQuery({
    queryKey: ['probes'],
    queryFn: () => fetchProbes(),
    refetchInterval: 30000,
  });

  const { data: targets = [], error: targetsError } = useQuery({
    queryKey: ['targets'],
    queryFn: fetchTargets,
  });

  // Mutation for acknowledge
  const ackMutation = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id),
    onMutate: (id) => setAckingAlertId(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      setAckingAlertId(null);
    },
    onError: () => setAckingAlertId(null),
  });

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesType = filterType === 'all' || alert.type === filterType;
      const matchesAck =
        filterAck === 'all' ||
        (filterAck === 'unack' && !alert.acknowledged) ||
        (filterAck === 'ack' && alert.acknowledged);
      const matchesTarget =
        selectedTargetId === 'all' || alert.targetId === selectedTargetId;
      const matchesSearch =
        alert.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        alert.targetId.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesAck && matchesTarget && matchesSearch;
    });
  }, [alerts, filterType, filterAck, selectedTargetId, searchQuery]);

  // Derived counts
  const unackCount = useMemo(() => alerts.filter((a) => !a.acknowledged).length, [alerts]);
  const criticalAlertsCount = useMemo(
    () => alerts.filter((a) => a.severity === 'critical' && !a.acknowledged).length,
    [alerts]
  );
  const downgradeAlertsCount = useMemo(
    () => alerts.filter((a) => a.type === 'probe-downgrade' && !a.acknowledged).length,
    [alerts]
  );

  const formatRelativeTime = (isoString: string) => {
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const getSeverityBadgeClass = (severity: RiskBand) => {
    switch (severity) {
      case 'critical':
        return 'bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border-[var(--crypto-shor-border)]';
      case 'high':
        return 'bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border-[var(--crypto-grover-border)]';
      case 'medium':
        return 'bg-[var(--crypto-classical-bg)] text-[var(--crypto-classical)] border-[var(--crypto-classical-border)]';
      case 'low':
        return 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border-[var(--border-subtle)]';
    }
  };

  const getTypeBadgeClass = (type: AlertType) => {
    switch (type) {
      case 'probe-downgrade':
        return 'bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border-[var(--crypto-shor-border)]';
      case 'new-critical':
        return 'bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border-[var(--crypto-shor-border)]';
      case 'cert-expiring':
        return 'bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border-[var(--crypto-grover-border)]';
      case 'drift':
        return 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border-[var(--crypto-pqc-border)]';
      case 'residue-rise':
        return 'bg-[var(--coverage-residue-bg)] text-[var(--coverage-residue)] border-[var(--coverage-residue-border)]';
    }
  };

  const isLoading = alertsLoading || probesLoading;

  if (isUnauthorizedError(alertsError) || isUnauthorizedError(probesError) || isUnauthorizedError(targetsError)) {
    return (
      <UnauthorizedState
        onRetry={() => {
          refetchAlerts();
          refetchProbes();
        }}
        context="Cryptographic Alerts & Monitoring Console"
      />
    );
  }

  if (isLoading && alerts.length === 0) {
    return (
      <div className="space-y-6 font-mono animate-pulse" aria-label="Loading alerts and probes">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4 min-h-[72px]">
          <div>
            <div className="h-3 w-48 bg-[var(--surface-raised)] rounded mb-2" />
            <div className="h-6 w-72 bg-[var(--surface-raised)] rounded" />
          </div>
          <div className="h-8 w-32 bg-[var(--surface-raised)] rounded" />
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
              Real-Time Security Feed & Probes
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--crypto-pqc)]" />
              Active Probe Monitoring
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1">
            Security Alerts & Protocol Probes
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Active downgrade detection, expiring certificate alerts, drift signals, and TLS/SSH probe telemetry.
          </p>
        </div>

        <button
          onClick={() => {
            refetchAlerts();
            refetchProbes();
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] transition-colors"
          title="Refresh alerts telemetry"
          aria-label="Refresh telemetry"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </header>

      {/* Top Bento Grid Metrics */}
      <section aria-label="Alerts Summary Metrics" className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Active Unacknowledged Alerts */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--border-prominent)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Active Alerts</span>
            <Bell className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span
              className={`text-2xl sm:text-3xl font-bold ${
                unackCount > 0 ? 'text-[var(--crypto-grover)]' : 'text-[var(--text-primary)]'
              }`}
            >
              {unackCount}
            </span>
            <span className="text-xs text-[var(--text-muted)]">unacknowledged</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span>{alerts.length} total alerts logged</span>
          </div>
        </div>

        {/* Critical Severity Alerts */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-shor-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Critical Alerts</span>
            <AlertTriangle className="w-4 h-4 text-[var(--crypto-shor)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-shor)]">
              {criticalAlertsCount}
            </span>
          </div>
          <div className="text-[10px] text-[var(--crypto-shor)] font-semibold">
            <span>Requires immediate remediation</span>
          </div>
        </div>

        {/* Downgrade Probes Detected */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-shor-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Probe Downgrades</span>
            <Radio className="w-4 h-4 text-[var(--crypto-shor)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-shor)]">
              {downgradeAlertsCount}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span>Cipher suite negotiation regression</span>
          </div>
        </div>

        {/* Probed Endpoints */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-pqc-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Active Probes</span>
            <Server className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--crypto-pqc)]">
              {probes.length}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span>TLS and SSH active probes</span>
          </div>
        </div>
      </section>

      {/* Main Grid: Alerts Feed + Probe Surface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Alerts Feed */}
        <div className="lg:col-span-2 space-y-4">
          {/* Alerts Filter Toolbar */}
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              {/* Ack Status Filter */}
              <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-0.5 rounded border border-[var(--border-subtle)]">
                <button
                  onClick={() => setFilterAck('unack')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    filterAck === 'unack'
                      ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  Active ({unackCount})
                </button>
                <button
                  onClick={() => setFilterAck('ack')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    filterAck === 'ack'
                      ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  Acknowledged
                </button>
                <button
                  onClick={() => setFilterAck('all')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    filterAck === 'all'
                      ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                  }`}
                >
                  All
                </button>
              </div>

              {/* Type Filter */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="px-2.5 py-1 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-secondary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                aria-label="Filter by alert type"
              >
                <option value="all">All Alert Types</option>
                <option value="residue-rise">Residue Rise Alerts</option>
                <option value="probe-downgrade">Probe Downgrades</option>
                <option value="new-critical">New Critical Findings</option>
                <option value="cert-expiring">Expiring Certificates</option>
                <option value="drift">Estate Drift</option>
              </select>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Search alerts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)] text-xs w-44 sm:w-52"
                aria-label="Search alerts"
              />
            </div>
          </div>

          {/* Alert Feed List */}
          <section
            aria-label="Alert Feed List"
            className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden shadow-sm"
          >
            <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--surface-overlay)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <h2 className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider">
                  Security Alerts Feed ({filteredAlerts.length})
                </h2>
              </div>
            </div>

            {filteredAlerts.length === 0 ? (
              <div className="p-12 text-center text-xs text-[var(--text-muted)]">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-[var(--crypto-pqc)] opacity-80" />
                <p className="font-semibold text-[var(--text-secondary)]">Zero active alerts matched</p>
                <p className="mt-1">All monitored targets and probes are operating within policy thresholds.</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-subtle)]">
                {filteredAlerts.map((alert) => {
                  const isAcking = ackingAlertId === alert.id;
                  const target = targets.find((t) => t.id === alert.targetId);
                  return (
                    <div
                      key={alert.id}
                      className="p-4 hover:bg-[var(--surface-raised)] transition-colors flex flex-col sm:flex-row sm:items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1.5 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          {/* Severity Badge */}
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getSeverityBadgeClass(
                              alert.severity
                            )}`}
                          >
                            {alert.severity}
                          </span>

                          {/* Alert Type Badge */}
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${getTypeBadgeClass(
                              alert.type
                            )}`}
                          >
                            {alert.type.replace('-', ' ')}
                          </span>

                          {/* Timestamp */}
                          <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            <span>{formatRelativeTime(alert.createdAt)}</span>
                          </span>
                        </div>

                        {/* Alert Message */}
                        <p className="font-semibold text-[var(--text-primary)] text-xs sm:text-sm">
                          {alert.message}
                        </p>

                        {/* Target Info */}
                        <div className="flex items-center gap-2 text-[11px] text-[var(--text-secondary)]">
                          <span>Target:</span>
                          <Link
                            href={`/estate`}
                            className="text-[var(--crypto-classical)] hover:underline flex items-center gap-0.5 font-mono"
                          >
                            <span>{target?.name || alert.targetId}</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </Link>
                        </div>

                        {/* Residue Explorer Deep Link */}
                        {alert.type === 'residue-rise' && (
                          <div className="pt-1">
                            <Link
                              href={`/residue?targetId=${alert.targetId}`}
                              className="inline-flex items-center gap-1 text-[11px] text-[var(--coverage-residue)] font-bold hover:underline"
                            >
                              <span>Inspect Unexplained Residue Clusters</span>
                              <ArrowRight className="w-3 h-3" />
                            </Link>
                          </div>
                        )}
                      </div>

                      {/* Action Button */}
                      <div className="shrink-0 self-end sm:self-start">
                        {alert.acknowledged ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[10px] bg-[var(--surface-raised)] text-[var(--text-muted)] border border-[var(--border-subtle)] font-semibold">
                            <CheckCircle2 className="w-3 h-3 text-[var(--crypto-pqc)]" />
                            <span>Acknowledged</span>
                          </span>
                        ) : (
                          <button
                            onClick={() => ackMutation.mutate(alert.id)}
                            disabled={isAcking}
                            className="px-3 py-1.5 rounded text-xs font-semibold bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 transition-opacity shadow-sm disabled:opacity-50 inline-flex items-center gap-1.5"
                            aria-label={`Acknowledge alert ${alert.id}`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>{isAcking ? 'Acknowledging...' : 'Acknowledge'}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* Right 1 Col: Active Protocol Probes Surface */}
        <div className="space-y-4">
          <section
            aria-label="Active Protocol Probes Surface"
            className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden shadow-sm"
          >
            <div className="p-3.5 border-b border-[var(--border-subtle)] bg-[var(--surface-overlay)] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <h2 className="text-xs font-bold text-[var(--text-primary)] uppercase tracking-wider">
                  Active Protocol Probes
                </h2>
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">{probes.length} Live Endpoints</span>
            </div>

            <div className="p-4 space-y-5">
              {probes.map((probe) => {
                const isQuantumSafe = Boolean(probe.negotiated?.quantumSafe);
                return (
                  <div
                    key={probe.id}
                    className="p-3.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] space-y-3"
                  >
                    {/* Endpoint Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Server className="w-4 h-4 text-[var(--crypto-classical)]" />
                        <span className="font-bold text-xs text-[var(--text-primary)] font-mono">
                          {probe.host}:{probe.port}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[var(--crypto-classical-bg)] text-[var(--crypto-classical)] border border-[var(--crypto-classical-border)]">
                        {probe.protocol.toUpperCase()}
                      </span>
                    </div>

                    {/* Negotiated State Box */}
                    <div
                      className={`p-3 rounded border text-xs space-y-1.5 ${
                        isQuantumSafe
                          ? 'border-[var(--crypto-pqc-border)] bg-[var(--crypto-pqc-bg)]'
                          : 'border-[var(--crypto-shor-border)] bg-[var(--crypto-shor-bg)]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--text-muted)]">
                          Negotiated Cipher Suite
                        </span>
                        {/* NEGOTIATED Badge */}
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-bold tracking-wider uppercase border ${
                            isQuantumSafe
                              ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] border-[var(--crypto-pqc)]'
                              : 'bg-[var(--crypto-shor)] text-[var(--surface-base)] border-[var(--crypto-shor)]'
                          }`}
                        >
                          NEGOTIATED
                        </span>
                      </div>

                      <div className="font-mono text-xs font-bold text-[var(--text-primary)]">
                        {probe.negotiated?.cipher || probe.negotiated?.version || 'Unknown'}
                      </div>

                      {probe.negotiated?.keyExchange && (
                        <div className="text-[11px] text-[var(--text-secondary)] font-mono">
                          KEX: {probe.negotiated.keyExchange}
                        </div>
                      )}

                      <div className="pt-1 flex items-center justify-between text-[10px]">
                        <span className="text-[var(--text-muted)]">
                          Probed: {formatRelativeTime(probe.probedAt)}
                        </span>
                        <span
                          className={`font-bold ${
                            isQuantumSafe ? 'text-[var(--crypto-pqc)]' : 'text-[var(--crypto-shor)]'
                          }`}
                        >
                          {isQuantumSafe ? 'PQC SECURE' : 'SHOR-VULNERABLE'}
                        </span>
                      </div>
                    </div>

                    {/* Supported Suites List */}
                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-center justify-between text-[10px] text-[var(--text-muted)] uppercase tracking-wider">
                        <span>Advertised / Supported Suites</span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)] font-semibold">
                          SUPPORTED
                        </span>
                      </div>

                      <div className="space-y-1">
                        {probe.supported.map((sup, sIdx) => {
                          const isSupPqc = Boolean(sup.quantumSafe);
                          const name = sup.cipher || sup.kex || `Suite #${sIdx + 1}`;
                          return (
                            <div
                              key={sIdx}
                              className="px-2.5 py-1.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] flex items-center justify-between text-[11px] font-mono"
                            >
                              <span className="text-[var(--text-secondary)] truncate max-w-[200px]">
                                {name}
                              </span>
                              {isSupPqc ? (
                                <span className="text-[10px] text-[var(--crypto-pqc)] font-bold shrink-0">
                                  PQC
                                </span>
                              ) : (
                                <span className="text-[10px] text-[var(--text-muted)] shrink-0">
                                  Classical
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
