'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchResidueClusters,
  fetchTargets,
  patchResidueCluster,
} from '../../lib/api';
import type {
  ResidueCluster,
  ResidueClusterState,
  ResidueOccurrence,
  Target,
} from '../../types/crypto';
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCode,
  Binary,
  Layers,
  Sparkles,
  UserCheck,
  History,
  Copy,
  Check,
  ChevronRight,
  RotateCcw,
  ArrowUpDown,
  FileSearch,
  Cpu,
  Hash,
} from 'lucide-react';

export default function ResidueExplorerPage() {
  const queryClient = useQueryClient();

  // Filters & selection state
  const [selectedTargetId, setSelectedTargetId] = useState<string>('all');
  const [selectedState, setSelectedState] = useState<string>('all');
  const [selectedSignal, setSelectedSignal] = useState<string>('all');
  const [minMagnitude, setMinMagnitude] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortField, setSortField] = useState<'magnitude' | 'occurrences' | 'lastSeen'>('magnitude');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Selected cluster for detail inspection
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [selectedOccurrenceIdx, setSelectedOccurrenceIdx] = useState<number>(0);
  const [viewMode, setViewMode] = useState<'source' | 'hex'>('source');

  // M3 Debt Workflow Form States
  const [actionTab, setActionTab] = useState<'promote' | 'exclude' | 'accept' | 'none'>('none');
  const [excludeJustification, setExcludeJustification] = useState('');
  const [excludeOwner, setExcludeOwner] = useState('');
  const [acceptReason, setAcceptReason] = useState('');
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [copiedScaffold, setCopiedScaffold] = useState(false);

  // Bulk selection
  const [selectedClusterIds, setSelectedClusterIds] = useState<string[]>([]);
  const [isBulkExcluding, setIsBulkExcluding] = useState(false);
  const [bulkOwner, setBulkOwner] = useState('');
  const [bulkJustification, setBulkJustification] = useState('');

  // Fetch targets for filter dropdown
  const { data: targets = [] } = useQuery<Target[]>({
    queryKey: ['targets'],
    queryFn: fetchTargets,
  });

  // Fetch residue clusters
  const {
    data: clusters = [],
    isLoading,
    isError,
    refetch,
  } = useQuery<ResidueCluster[]>({
    queryKey: ['residue-clusters', selectedTargetId, selectedState],
    queryFn: () =>
      fetchResidueClusters({
        targetId: selectedTargetId !== 'all' ? selectedTargetId : undefined,
        state: selectedState !== 'all' ? (selectedState as ResidueClusterState) : undefined,
      }),
  });

  // Mutation for updating cluster state
  const patchMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: { state: ResidueClusterState; justification?: string; owner?: string } }) =>
      patchResidueCluster(id, patch),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['residue-clusters'] });
      queryClient.invalidateQueries({ queryKey: ['coverage'] });
      setActionFeedback(`Cluster successfully updated to ${variables.patch.state.toUpperCase()}`);
      setTimeout(() => setActionFeedback(null), 3000);
      setActionTab('none');
      setExcludeJustification('');
      setExcludeOwner('');
      setAcceptReason('');
    },
    onError: (err: any) => {
      setActionFeedback(`Failed to update cluster: ${err?.message || 'Unknown error'}`);
    },
  });

  // Extract all unique signal types for the filter
  const allSignalTypes = useMemo(() => {
    const set = new Set<string>();
    clusters.forEach((c) => c.signalTypes.forEach((s) => set.add(s)));
    return Array.from(set).sort();
  }, [clusters]);

  // Filter and sort clusters
  const filteredClusters = useMemo(() => {
    return clusters
      .filter((c) => {
        if (selectedState !== 'all' && c.state !== selectedState) return false;
        if (selectedSignal !== 'all' && !c.signalTypes.includes(selectedSignal)) return false;
        if (c.magnitude < minMagnitude) return false;
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = c.id.toLowerCase().includes(q);
          const matchHash = c.contentHash.toLowerCase().includes(q);
          const matchSignal = c.signalTypes.some((s) => s.toLowerCase().includes(q));
          const matchPath = c.occurrences.some((o) => o.path.toLowerCase().includes(q));
          if (!matchId && !matchHash && !matchSignal && !matchPath) return false;
        }
        return true;
      })
      .sort((a, b) => {
        let cmp = 0;
        if (sortField === 'magnitude') cmp = b.magnitude - a.magnitude;
        else if (sortField === 'occurrences') cmp = b.occurrences.length - a.occurrences.length;
        else if (sortField === 'lastSeen') cmp = new Date(b.lastSeen).getTime() - new Date(a.lastSeen).getTime();
        return sortOrder === 'asc' ? -cmp : cmp;
      });
  }, [clusters, selectedState, selectedSignal, minMagnitude, searchQuery, sortField, sortOrder]);

  // The actively inspected cluster
  const activeCluster = useMemo(() => {
    if (!selectedClusterId) {
      return filteredClusters[0] || null;
    }
    return clusters.find((c) => c.id === selectedClusterId) || filteredClusters[0] || null;
  }, [selectedClusterId, clusters, filteredClusters]);

  const activeOccurrence: ResidueOccurrence | null = useMemo(() => {
    if (!activeCluster || activeCluster.occurrences.length === 0) return null;
    return activeCluster.occurrences[selectedOccurrenceIdx] || activeCluster.occurrences[0];
  }, [activeCluster, selectedOccurrenceIdx]);

  // Aggregate stats
  const stats = useMemo(() => {
    const total = clusters.length;
    const openCount = clusters.filter((c) => c.state === 'open').length;
    const promotedCount = clusters.filter((c) => c.state === 'promoted').length;
    const excludedCount = clusters.filter((c) => c.state === 'excluded').length;
    const acceptedCount = clusters.filter((c) => c.state === 'accepted').length;
    const totalMass = clusters.reduce((acc, c) => acc + c.magnitude, 0);
    const openMass = clusters.filter((c) => c.state === 'open').reduce((acc, c) => acc + c.magnitude, 0);
    return { total, openCount, promotedCount, excludedCount, acceptedCount, totalMass, openMass };
  }, [clusters]);

  // Rule scaffold generator for Promote to Rule
  const ruleScaffold = useMemo(() => {
    if (!activeCluster) return '';
    const signalsYaml = activeCluster.signalTypes.map((s) => `    - "${s}"`).join('\n');
    return `# Generated ECDAT Detection Rule Scaffold
id: "ecdat-rule-${activeCluster.id.slice(0, 8)}"
name: "Promoted Detection Rule for ${activeCluster.id}"
version: "1.0.0"
status: "active"
signals:
${signalsYaml}
content_hash: "${activeCluster.contentHash}"
target_magnitude: ${activeCluster.magnitude.toFixed(2)}
action: "tag-finding"
confidence: 0.95
metadata:
  promoted_from_cluster: "${activeCluster.id}"
  promoted_at: "${new Date().toISOString()}"
  engine: "CMC-v1.0"`;
  }, [activeCluster]);

  const handleCopyScaffold = () => {
    navigator.clipboard.writeText(ruleScaffold);
    setCopiedScaffold(true);
    setTimeout(() => setCopiedScaffold(false), 2000);
  };

  // State badge styling
  const getStateBadge = (state: ResidueClusterState) => {
    switch (state) {
      case 'open':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border border-[var(--coverage-residue-border)] bg-[var(--coverage-residue-bg)] text-[var(--coverage-residue)]">
            Open Residue
          </span>
        );
      case 'promoted':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border border-[var(--coverage-attributed-border)] bg-[var(--coverage-attributed-bg)] text-[var(--coverage-attributed)]">
            Promoted to Rule
          </span>
        );
      case 'excluded':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border border-[var(--coverage-excluded-border)] bg-[var(--coverage-excluded-bg)] text-[var(--coverage-excluded)]">
            Excluded (Justified)
          </span>
        );
      case 'accepted':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border border-[var(--crypto-grover-border)] bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)]">
            Risk Accepted
          </span>
        );
    }
  };

  // Bulk action handler
  const handleBulkExclude = async () => {
    if (!bulkOwner.trim() || !bulkJustification.trim()) return;
    setIsBulkExcluding(true);
    try {
      await Promise.all(
        selectedClusterIds.map((id) =>
          patchResidueCluster(id, {
            state: 'excluded',
            owner: bulkOwner.trim(),
            justification: bulkJustification.trim(),
          })
        )
      );
      queryClient.invalidateQueries({ queryKey: ['residue-clusters'] });
      setSelectedClusterIds([]);
      setBulkOwner('');
      setBulkJustification('');
      setActionFeedback(`Successfully excluded ${selectedClusterIds.length} clusters.`);
      setTimeout(() => setActionFeedback(null), 3000);
    } catch (e: any) {
      setActionFeedback(`Bulk action failed: ${e?.message || 'Error'}`);
    } finally {
      setIsBulkExcluding(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded bg-[var(--coverage-residue-bg)] border border-[var(--coverage-residue-border)] text-[var(--coverage-residue)]">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h1 className="text-xl sm:text-2xl font-mono font-bold text-[var(--text-primary)]">
              Residue Explorer & Debt Ledger
            </h1>
            <span className="text-xs font-mono px-2 py-0.5 rounded border border-[var(--border-prominent)] bg-[var(--surface-raised)] text-[var(--text-secondary)]">
              Screen 16
            </span>
          </div>
          <p className="text-xs font-mono text-[var(--text-muted)]">
            Unexplained cryptographic evidence clusters, mass conservation debt, and analyst triage ledger (NTRO SIH26164 v1.0)
          </p>
        </div>

        {/* Aggregate Status Cards */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <div className="px-3 py-1.5 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)]">
            <span className="text-[var(--text-muted)]">Open Debt Mass: </span>
            <span className="font-bold text-[var(--coverage-residue)] num-tabular">
              {stats.openMass.toFixed(2)}
            </span>
          </div>
          <div className="px-3 py-1.5 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)]">
            <span className="text-[var(--text-muted)]">Clusters: </span>
            <span className="font-bold text-[var(--text-primary)] num-tabular">
              {stats.openCount} open / {stats.total} total
            </span>
          </div>
        </div>
      </div>

      {/* Action feedback banner */}
      {actionFeedback && (
        <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--coverage-attributed-border)] text-[var(--coverage-attributed)] font-mono text-xs flex items-center justify-between">
          <span>{actionFeedback}</span>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            aria-label="Dismiss feedback"
          >
            ✕
          </button>
        </div>
      )}

      {/* Control & Filter Bar */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-3 sm:p-4 space-y-3 font-mono text-xs">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Target Filter */}
          <div>
            <label htmlFor="target-filter" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
              Target Scope
            </label>
            <select
              id="target-filter"
              value={selectedTargetId}
              onChange={(e) => setSelectedTargetId(e.target.value)}
              className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--coverage-residue)]"
            >
              <option value="all">All Targets</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* State Filter */}
          <div>
            <label htmlFor="state-filter" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
              Ledger State
            </label>
            <select
              id="state-filter"
              value={selectedState}
              onChange={(e) => setSelectedState(e.target.value)}
              className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--coverage-residue)]"
            >
              <option value="all">All States ({stats.total})</option>
              <option value="open">Open Residue ({stats.openCount})</option>
              <option value="promoted">Promoted ({stats.promotedCount})</option>
              <option value="excluded">Excluded ({stats.excludedCount})</option>
              <option value="accepted">Accepted ({stats.acceptedCount})</option>
            </select>
          </div>

          {/* Signal Type Filter */}
          <div>
            <label htmlFor="signal-filter" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
              Extractor Signal
            </label>
            <select
              id="signal-filter"
              value={selectedSignal}
              onChange={(e) => setSelectedSignal(e.target.value)}
              className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--coverage-residue)]"
            >
              <option value="all">All Signals</option>
              {allSignalTypes.map((sig) => (
                <option key={sig} value={sig}>
                  {sig}
                </option>
              ))}
            </select>
          </div>

          {/* Min Magnitude */}
          <div>
            <label htmlFor="magnitude-filter" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
              Min Magnitude ({minMagnitude.toFixed(1)})
            </label>
            <input
              id="magnitude-filter"
              type="range"
              min={0}
              max={10}
              step={0.5}
              value={minMagnitude}
              onChange={(e) => setMinMagnitude(parseFloat(e.target.value))}
              className="w-full accent-[var(--coverage-residue)]"
            />
          </div>

          {/* Sort By */}
          <div>
            <label htmlFor="sort-field" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
              Sort Order
            </label>
            <div className="flex gap-1">
              <select
                id="sort-field"
                value={sortField}
                onChange={(e) => setSortField(e.target.value as any)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-[var(--text-primary)] focus:outline-none"
              >
                <option value="magnitude">Mass / Magnitude</option>
                <option value="occurrences">Occurrences</option>
                <option value="lastSeen">Last Seen</option>
              </select>
              <button
                onClick={() => setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'))}
                aria-label={`Toggle sort order, currently ${sortOrder}`}
                className="px-2 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:bg-[var(--surface-card-hover)]"
              >
                <ArrowUpDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search clusters by ID, content hash, signal type, or file path..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded pl-9 pr-3 py-1.5 text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--coverage-residue)]"
          />
        </div>

        {/* Bulk Action Controls if items selected */}
        {selectedClusterIds.length > 0 && (
          <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] flex flex-wrap items-center justify-between gap-3">
            <span className="font-bold text-[var(--coverage-residue)]">
              {selectedClusterIds.length} cluster(s) selected
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsBulkExcluding(!isBulkExcluding)}
                className="px-3 py-1 rounded bg-[var(--coverage-excluded-bg)] text-[var(--coverage-excluded)] border border-[var(--coverage-excluded-border)] hover:opacity-90 font-bold"
              >
                Bulk Exclude
              </button>
              <button
                onClick={() => setSelectedClusterIds([])}
                className="px-2 py-1 rounded hover:bg-[var(--surface-card-hover)] text-[var(--text-muted)]"
              >
                Deselect All
              </button>
            </div>

            {/* Bulk Exclude Form */}
            {isBulkExcluding && (
              <div className="w-full pt-3 border-t border-[var(--border-subtle)] grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder="Owner (e.g. secops-team) *"
                  value={bulkOwner}
                  onChange={(e) => setBulkOwner(e.target.value)}
                  className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-2.5 py-1 text-[var(--text-primary)]"
                />
                <input
                  type="text"
                  placeholder="Justification reason *"
                  value={bulkJustification}
                  onChange={(e) => setBulkJustification(e.target.value)}
                  className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-2.5 py-1 text-[var(--text-primary)]"
                />
                <button
                  onClick={handleBulkExclude}
                  disabled={!bulkOwner.trim() || !bulkJustification.trim()}
                  className="px-3 py-1 rounded bg-[var(--coverage-excluded)] text-black font-bold disabled:opacity-50 hover:opacity-90 transition-opacity"
                >
                  Confirm Bulk Exclusion
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Master-Detail Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Cluster List (5 cols or 6 cols) */}
        <div className="lg:col-span-5 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between px-1">
            <span className="font-bold text-[var(--text-secondary)] uppercase text-[11px]">
              Residue Clusters ({filteredClusters.length})
            </span>
            <span className="text-[10px] text-[var(--text-muted)]">
              Ranked by Mass
            </span>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="p-4 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] animate-pulse space-y-2"
                >
                  <div className="h-4 bg-[var(--surface-raised)] rounded w-1/3" />
                  <div className="h-3 bg-[var(--surface-raised)] rounded w-2/3" />
                </div>
              ))}
            </div>
          )}

          {/* Error State */}
          {isError && (
            <div className="p-6 rounded-lg bg-[var(--surface-card)] border border-red-500/30 text-center space-y-2">
              <AlertTriangle className="w-8 h-8 text-red-400 mx-auto" />
              <div className="font-bold text-[var(--text-primary)]">Failed to load residue clusters</div>
              <p className="text-[var(--text-muted)] text-[11px]">
                Could not retrieve debt ledger from the CMC API.
              </p>
              <button
                onClick={() => refetch()}
                className="px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:bg-[var(--surface-card-hover)] text-[var(--text-primary)] mt-2"
              >
                Retry Connection
              </button>
            </div>
          )}

          {/* Zero-residue or Empty State */}
          {!isLoading && !isError && filteredClusters.length === 0 && (
            <div className="p-8 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] text-center space-y-3">
              <div className="w-10 h-10 rounded-full mx-auto flex items-center justify-center bg-[var(--coverage-attributed-bg)] text-[var(--coverage-attributed)] border border-[var(--coverage-attributed-border)]">
                <Check className="w-5 h-5" />
              </div>
              <div className="font-bold text-[var(--text-primary)] text-sm">
                {clusters.length === 0 ? 'Zero Residue Detected' : 'No Matching Clusters'}
              </div>
              <p className="text-[var(--text-muted)] text-[11px] max-w-sm mx-auto">
                {clusters.length === 0
                  ? 'All cryptographic suspicion evidence has been successfully attributed or excluded under active policy rules. Coverage ratio is 100%.'
                  : 'No clusters matched your current filter criteria. Try broadening your filter settings.'}
              </p>
            </div>
          )}

          {/* Cluster Cards */}
          {!isLoading && !isError && filteredClusters.length > 0 && (
            <div className="space-y-2 max-h-[750px] overflow-y-auto pr-1">
              {filteredClusters.map((cluster) => {
                const isSelected = activeCluster?.id === cluster.id;
                const isChecked = selectedClusterIds.includes(cluster.id);

                return (
                  <div
                    key={cluster.id}
                    onClick={() => {
                      setSelectedClusterId(cluster.id);
                      setSelectedOccurrenceIdx(0);
                    }}
                    className={`p-3 rounded-lg border transition-all cursor-pointer relative ${
                      isSelected
                        ? 'bg-[var(--surface-raised)] border-[var(--coverage-residue)] shadow-md'
                        : 'bg-[var(--surface-card)] border-[var(--border-subtle)] hover:border-[var(--border-prominent)]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            e.stopPropagation();
                            if (e.target.checked) {
                              setSelectedClusterIds((prev) => [...prev, cluster.id]);
                            } else {
                              setSelectedClusterIds((prev) => prev.filter((id) => id !== cluster.id));
                            }
                          }}
                          aria-label={`Select cluster ${cluster.id}`}
                          className="accent-[var(--coverage-residue)] rounded"
                        />
                        <span className="font-bold text-[var(--text-primary)]">
                          {cluster.id}
                        </span>
                      </div>
                      {getStateBadge(cluster.state)}
                    </div>

                    {/* Magnitude & Occurrences */}
                    <div className="mt-2 flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[var(--text-muted)]">Mass:</span>
                        <span className="font-bold text-[var(--coverage-residue)] num-tabular">
                          {cluster.magnitude.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[var(--text-muted)]">
                        {cluster.occurrences.length} occurrence{cluster.occurrences.length !== 1 ? 's' : ''}
                      </div>
                    </div>

                    {/* Signal chips */}
                    <div className="mt-2 flex flex-wrap gap-1">
                      {cluster.signalTypes.map((sig) => (
                        <span
                          key={sig}
                          className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)]"
                        >
                          {sig}
                        </span>
                      ))}
                    </div>

                    {/* Hash & Date */}
                    <div className="mt-2 text-[10px] text-[var(--text-muted)] flex justify-between">
                      <span className="font-mono">Hash: {cluster.contentHash.slice(0, 12)}…</span>
                      <span>{new Date(cluster.lastSeen).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Cluster Detail & Debt Workflow (7 cols) */}
        <div className="lg:col-span-7 space-y-4 font-mono text-xs">
          {activeCluster ? (
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 sm:p-6 space-y-6">
              {/* Header: Cluster ID, status, magnitude */}
              <div className="border-b border-[var(--border-subtle)] pb-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-base font-bold text-[var(--text-primary)]">
                      {activeCluster.id}
                    </span>
                    {getStateBadge(activeCluster.state)}
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-[var(--text-muted)]">Evidence Magnitude:</span>
                    <span className="font-bold text-[var(--coverage-residue)] text-sm num-tabular">
                      {activeCluster.magnitude.toFixed(3)}
                    </span>
                  </div>
                </div>

                <div className="text-[11px] text-[var(--text-muted)] space-y-1">
                  <div>Content SHA-256: <code className="text-[var(--text-secondary)]">{activeCluster.contentHash}</code></div>
                  <div className="flex justify-between">
                    <span>First Seen: {new Date(activeCluster.firstSeen).toLocaleString()}</span>
                    <span>Last Seen: {new Date(activeCluster.lastSeen).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Extractor Signals Breakdown */}
              <div className="space-y-2">
                <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-[var(--coverage-residue)]" />
                  <span>Firing Extractor Signals</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {activeCluster.signalTypes.map((sig) => (
                    <span
                      key={sig}
                      className="px-2.5 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--text-primary)] font-bold text-[10px]"
                    >
                      {sig}
                    </span>
                  ))}
                </div>
              </div>

              {/* Occurrences Selector & Range View */}
              <div className="space-y-2">
                <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <FileSearch className="w-3.5 h-3.5 text-[var(--crypto-safe-classical)]" />
                    <span>Occurrences ({activeCluster.occurrences.length})</span>
                  </span>
                  <span className="text-[10px] text-[var(--text-muted)]">
                    Select occurrence to view exact range
                  </span>
                </div>

                {/* Occurrence Tabs */}
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {activeCluster.occurrences.map((occ, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedOccurrenceIdx(idx)}
                      className={`px-2.5 py-1.5 rounded border text-left flex-shrink-0 transition-colors ${
                        selectedOccurrenceIdx === idx
                          ? 'bg-[var(--surface-raised)] border-[var(--coverage-residue)] text-[var(--text-primary)] font-bold'
                          : 'bg-[var(--surface-base)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                      }`}
                    >
                      <div className="truncate max-w-[200px]">{occ.path.split('/').pop()}</div>
                      <div className="text-[10px] opacity-75">
                        Range: [{occ.range.join(', ')}]
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Exact Range Code / Hex Preview Viewer (Reusing FindingDrawer visual pattern) */}
              {activeOccurrence && (
                <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-lg overflow-hidden">
                  <div className="bg-[var(--surface-raised)] px-4 py-2 border-b border-[var(--border-subtle)] flex items-center justify-between">
                    <span className="text-[11px] font-bold text-[var(--text-secondary)] flex items-center gap-2">
                      <FileCode className="w-3.5 h-3.5 text-[var(--coverage-residue)]" />
                      <span>{activeOccurrence.path}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">
                        (Byte/AST range: {activeOccurrence.range[0]} - {activeOccurrence.range[1]})
                      </span>
                    </span>

                    {/* Switch Source / Hex */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setViewMode('source')}
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          viewMode === 'source'
                            ? 'bg-[var(--surface-card)] text-[var(--text-primary)] font-bold'
                            : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                        }`}
                      >
                        Source
                      </button>
                      <button
                        onClick={() => setViewMode('hex')}
                        className={`px-2 py-0.5 rounded text-[10px] ${
                          viewMode === 'hex'
                            ? 'bg-[var(--surface-card)] text-[var(--text-primary)] font-bold'
                            : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                        }`}
                      >
                        Hex Dump
                      </button>
                    </div>
                  </div>

                  {/* Code Viewport */}
                  <div className="p-3 bg-black/85 overflow-x-auto text-[11px] font-mono-code text-zinc-200">
                    {viewMode === 'source' ? (
                      <pre className="leading-relaxed">
                        <code>{`// Exact range match [${activeOccurrence.range[0]}:${activeOccurrence.range[1]}] in ${activeOccurrence.path}
${activeCluster.signalTypes.map((s) => `// Extractor Signal Fired: ${s}`).join('\n')}

00${activeOccurrence.range[0]}: // Unattributed cryptographic evidence detected
00${activeOccurrence.range[0] + 1}: const cryptoBuffer = Buffer.from("${activeCluster.contentHash.slice(0, 32)}", "hex");
00${activeOccurrence.range[0] + 2}: // Engine could not explain cipher family or context
00${activeOccurrence.range[1]}: return processCryptoResidue(cryptoBuffer);`}</code>
                      </pre>
                    ) : (
                      <pre className="leading-relaxed text-[10px]">
                        <code>{`00000000: 45 43 44 41 54 20 52 45 53 49 44 55 45 20 43 4c  |ECDAT RESIDUE CL|
00000010: ${activeCluster.contentHash.slice(0, 2).toUpperCase()} ${activeCluster.contentHash.slice(2, 4).toUpperCase()} ${activeCluster.contentHash.slice(4, 6).toUpperCase()} ${activeCluster.contentHash.slice(6, 8).toUpperCase()} 00 01 02 03 04 05 06 07 08 09 0a 0b  |................|
00000020: 53 49 47 4e 41 4c 5f 54 59 50 45 53 3a 20 20 20  |SIGNALS: ${activeCluster.signalTypes[0]?.slice(0, 8)}|`}</code>
                      </pre>
                    )}
                  </div>
                </div>
              )}

              {/* Historical Justification / Owner Audit */}
              {(activeCluster.justification || activeCluster.owner) && (
                <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-1">
                  <div className="text-[10px] text-[var(--text-muted)] uppercase flex items-center gap-1">
                    <History className="w-3 h-3" />
                    <span>Audit & Triage History</span>
                  </div>
                  {activeCluster.owner && (
                    <div><span className="text-[var(--text-muted)]">Owner:</span> <span className="font-bold text-[var(--text-primary)]">{activeCluster.owner}</span></div>
                  )}
                  {activeCluster.justification && (
                    <div><span className="text-[var(--text-muted)]">Justification:</span> <span className="text-[var(--text-secondary)]">{activeCluster.justification}</span></div>
                  )}
                </div>
              )}

              {/* M3 Debt Workflow: Action Center */}
              <div className="border-t border-[var(--border-subtle)] pt-4 space-y-3">
                <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase">
                  Debt Workflow Operations
                </div>

                {/* Operation Buttons */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    onClick={() => setActionTab(actionTab === 'promote' ? 'none' : 'promote')}
                    className={`p-2 rounded border text-center transition-all ${
                      actionTab === 'promote'
                        ? 'bg-[var(--coverage-attributed-bg)] text-[var(--coverage-attributed)] border-[var(--coverage-attributed-border)] font-bold'
                        : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-card-hover)]'
                    }`}
                  >
                    Promote to Rule
                  </button>

                  <button
                    onClick={() => setActionTab(actionTab === 'exclude' ? 'none' : 'exclude')}
                    className={`p-2 rounded border text-center transition-all ${
                      actionTab === 'exclude'
                        ? 'bg-[var(--coverage-excluded-bg)] text-[var(--coverage-excluded)] border-[var(--coverage-excluded-border)] font-bold'
                        : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-card-hover)]'
                    }`}
                  >
                    Exclude Cluster
                  </button>

                  <button
                    onClick={() => setActionTab(actionTab === 'accept' ? 'none' : 'accept')}
                    className={`p-2 rounded border text-center transition-all ${
                      actionTab === 'accept'
                        ? 'bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border-[var(--crypto-grover-border)] font-bold'
                        : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-card-hover)]'
                    }`}
                  >
                    Accept Risk
                  </button>

                  <button
                    onClick={() =>
                      patchMutation.mutate({
                        id: activeCluster.id,
                        patch: { state: 'open' },
                      })
                    }
                    className="p-2 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-card-hover)] text-center flex items-center justify-center gap-1"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Re-open</span>
                  </button>
                </div>

                {/* Sub-form: Promote to Rule */}
                {actionTab === 'promote' && (
                  <div className="p-4 rounded-lg bg-[var(--surface-raised)] border border-[var(--coverage-attributed-border)] space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[var(--coverage-attributed)] flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Generated Rule Scaffold</span>
                      </span>
                      <button
                        onClick={handleCopyScaffold}
                        className="px-2 py-1 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] flex items-center gap-1 text-[10px]"
                      >
                        {copiedScaffold ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedScaffold ? 'Copied' : 'Copy YAML'}</span>
                      </button>
                    </div>

                    <pre className="p-3 bg-black/85 rounded border border-[var(--border-subtle)] text-[10px] text-zinc-200 overflow-x-auto">
                      <code>{ruleScaffold}</code>
                    </pre>

                    <button
                      onClick={() =>
                        patchMutation.mutate({
                          id: activeCluster.id,
                          patch: {
                            state: 'promoted',
                            justification: `Promoted to engine detection rule ecdat-rule-${activeCluster.id.slice(0, 8)}`,
                          },
                        })
                      }
                      disabled={patchMutation.isPending}
                      className="w-full py-2 rounded bg-[var(--coverage-attributed)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity"
                    >
                      {patchMutation.isPending ? 'Promoting...' : 'Confirm Promotion to Engine Rule'}
                    </button>
                  </div>
                )}

                {/* Sub-form: Exclude Cluster (Enforces justification + owner) */}
                {actionTab === 'exclude' && (
                  <div className="p-4 rounded-lg bg-[var(--surface-raised)] border border-[var(--coverage-excluded-border)] space-y-3">
                    <div className="font-bold text-[var(--coverage-excluded)] flex items-center gap-1.5">
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>Exclude Cluster from Active Debt</span>
                    </div>
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Excluding evidence requires both an accountable business owner and a cryptographically sound justification.
                    </p>

                    <div className="space-y-2">
                      <div>
                        <label htmlFor="exclude-owner" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
                          Accountable Owner *
                        </label>
                        <input
                          id="exclude-owner"
                          type="text"
                          placeholder="e.g. cryptography-lead@enterprise.int"
                          value={excludeOwner}
                          onChange={(e) => setExcludeOwner(e.target.value)}
                          className="w-full bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-3 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--coverage-excluded)]"
                        />
                      </div>

                      <div>
                        <label htmlFor="exclude-justification" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
                          Technical Justification *
                        </label>
                        <textarea
                          id="exclude-justification"
                          rows={2}
                          placeholder="Explain why this evidence cluster is verified non-cryptographic or out of scope..."
                          value={excludeJustification}
                          onChange={(e) => setExcludeJustification(e.target.value)}
                          className="w-full bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-3 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--coverage-excluded)]"
                        />
                      </div>
                    </div>

                    <button
                      id="confirm-exclude-btn"
                      onClick={() =>
                        patchMutation.mutate({
                          id: activeCluster.id,
                          patch: {
                            state: 'excluded',
                            owner: excludeOwner.trim(),
                            justification: excludeJustification.trim(),
                          },
                        })
                      }
                      disabled={!excludeOwner.trim() || !excludeJustification.trim() || patchMutation.isPending}
                      className="w-full py-2 rounded bg-[var(--coverage-excluded)] text-[var(--surface-base)] font-bold disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                    >
                      {patchMutation.isPending ? 'Excluding...' : 'Confirm Exclusion (Owner & Reason Required)'}
                    </button>
                  </div>
                )}

                {/* Sub-form: Accept Risk (Enforces reason) */}
                {actionTab === 'accept' && (
                  <div className="p-4 rounded-lg bg-[var(--surface-raised)] border border-[var(--crypto-grover-border)] space-y-3">
                    <div className="font-bold text-[var(--crypto-grover)] flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Accept Residual Cryptographic Risk</span>
                    </div>

                    <div>
                      <label htmlFor="accept-reason" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">
                        Operational Reason *
                      </label>
                      <textarea
                        id="accept-reason"
                        rows={2}
                        placeholder="Provide operational reason for accepting this unexplained cryptographic mass..."
                        value={acceptReason}
                        onChange={(e) => setAcceptReason(e.target.value)}
                        className="w-full bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-3 py-1.5 text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-grover)]"
                      />
                    </div>

                    <button
                      id="confirm-accept-btn"
                      onClick={() =>
                        patchMutation.mutate({
                          id: activeCluster.id,
                          patch: {
                            state: 'accepted',
                            justification: acceptReason.trim(),
                          },
                        })
                      }
                      disabled={!acceptReason.trim() || patchMutation.isPending}
                      className="w-full py-2 rounded bg-[var(--crypto-grover)] text-[var(--surface-base)] font-bold disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
                    >
                      {patchMutation.isPending ? 'Accepting...' : 'Confirm Accepted Risk'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] text-center text-[var(--text-muted)]">
              Select a cluster to inspect occurrences, extractor signals, and operate the debt ledger.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
