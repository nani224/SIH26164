'use client';

import { useState, useMemo, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../../lib/store';
import { fetchScanFindings } from '../../lib/api';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { CbomExportButton } from '../../components/CbomExportButton';
import { classifyAlgorithm } from '../../types/crypto';
import {
  ListFilter,
  Search,
  Bookmark,
  ExternalLink,
  ShieldAlert,
  RefreshCw,
  Cpu,
  Cloud,
  HelpCircle,
} from 'lucide-react';

export default function InventoryPage() {
  const { activeScanId, openDrawer } = useAppStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBand, setSelectedBand] = useState<string>('all');
  const [selectedFamily, setSelectedFamily] = useState<string>('all');
  const [selectedSurface, setSelectedSurface] = useState<string>('all');
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [activePreset, setActivePreset] = useState<'all' | 'hndl' | 'broken' | 'review' | 'proposed'>('all');

  const {
    data: findingsData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['findings', activeScanId, selectedBand, selectedFamily, selectedSurface, searchQuery, onlyNeedsReview],
    queryFn: () =>
      fetchScanFindings(activeScanId, {
        band: selectedBand,
        family: selectedFamily,
        surface: selectedSurface,
        q: searchQuery,
        needsReview: onlyNeedsReview,
      }),
  });

  // Findings straight from the API -- no synthetic duplication. This used
  // to fabricate up to 120 fake copies of every real finding (fake ids,
  // fake paths) whenever a real scan had fewer than 50 results, "to prove
  // virtualization works" -- but that meant every real scan under 50
  // findings showed fabricated rows mixed into real data, and a search
  // match on the one real row got buried among 119 fakes. Virtualizer
  // capability belongs in a dedicated perf test with synthetic data (see
  // MoscaMatrix's dense-dataset test), not baked into the page that also
  // renders real backend results.
  const virtualRows = useMemo(() => findingsData?.items ?? [], [findingsData]);

  // Preset and facet filter logic
  const filtered = useMemo(() => {
    return virtualRows.filter((f) => {
      if (activePreset === 'hndl' && !f.risk?.hndl) return false;
      if (activePreset === 'broken' && !f.risk?.classicallyBroken) return false;
      if (activePreset === 'review' && !f.risk?.needsReview) return false;
      if (activePreset === 'proposed' && !f.displayName.includes('[Proposed]')) return false;
      if (selectedSurface !== 'all' && f.surface !== selectedSurface) return false;
      if (selectedBand !== 'all' && f.risk?.band !== selectedBand) return false;
      if (selectedFamily !== 'all') {
        const fam = classifyAlgorithm(f.family, f.displayName, f.risk?.classicallyBroken);
        if (fam !== selectedFamily) return false;
      }
      if (onlyNeedsReview && !f.risk?.needsReview) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matches =
          f.displayName.toLowerCase().includes(q) ||
          (f.family ?? '').toLowerCase().includes(q) ||
          f.location.path.toLowerCase().includes(q) ||
          (f.symbol && f.symbol.toLowerCase().includes(q));
        if (!matches) return false;
      }
      return true;
    });
  }, [virtualRows, activePreset, selectedSurface, selectedBand, selectedFamily, onlyNeedsReview, searchQuery]);

  // Virtualizer setup for 60 fps table scrolling
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 12,
  });

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <ListFilter className="w-3.5 h-3.5" />
            <span>SCREEN 4 · HIGH-DENSITY CRYPTOGRAPHIC INVENTORY</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Discovered Cryptographic Assets ({filtered.length.toLocaleString()} items)
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Virtualized 60 fps catalog. Live API queries via TanStack Query. Hardware and Cloud KMS appear with [Proposed] tag.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CbomExportButton scanId={activeScanId} />
        </div>
      </div>

      {/* Preset Filter Views */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
          <Bookmark className="w-3 h-3 text-[var(--crypto-pqc)]" />
          <span>Saved Views:</span>
        </span>
        {[
          { id: 'all', label: 'All Discovered Assets' },
          { id: 'hndl', label: 'HNDL Threat Exposure' },
          { id: 'broken', label: 'Classically Broken Audit' },
          { id: 'review', label: 'Low Confidence (Review Req.)' },
          { id: 'proposed', label: 'Hardware & Cloud [Proposed]' },
        ].map((p) => (
          <button
            key={p.id}
            onClick={() => setActivePreset(p.id as any)}
            className={`px-2.5 py-1 rounded text-[11px] border transition-colors ${
              activePreset === p.id
                ? 'bg-[var(--crypto-pqc-bg)] border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold'
                : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-prominent)]'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Faceted Filter Toolbar */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg flex flex-wrap items-center gap-3">
        {/* Search bar */}
        <div className="flex items-center bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 flex-1 min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-[var(--crypto-pqc)] mr-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search algorithm, curve, file path, symbol... (Hotkey: /)"
            className="w-full bg-transparent text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none text-xs"
          />
        </div>

        {/* Surface Filter */}
        <select
          value={selectedSurface}
          aria-label="Filter by attack surface"
          onChange={(e) => setSelectedSurface(e.target.value)}
          className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
        >
          <option value="all">All Attack Surfaces</option>
          <option value="source-ast">Source AST</option>
          <option value="binary-embedded">Binary Embedded</option>
          <option value="network-protocol">Network Protocol</option>
          <option value="hardware-module">Hardware Module [Proposed]</option>
          <option value="cloud-service">Cloud Service [Proposed]</option>
        </select>

        {/* Band Filter */}
        <select
          value={selectedBand}
          aria-label="Filter by risk band"
          onChange={(e) => setSelectedBand(e.target.value)}
          className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
        >
          <option value="all">All Risk Bands</option>
          <option value="critical">Critical (≥ 60)</option>
          <option value="high">High (35–59)</option>
          <option value="medium">Medium (15–34)</option>
          <option value="low">Low (&lt; 15)</option>
        </select>

        {/* Semantic Family Filter */}
        <select
          value={selectedFamily}
          aria-label="Filter by semantic family"
          onChange={(e) => setSelectedFamily(e.target.value)}
          className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
        >
          <option value="all">All Semantic Families</option>
          <option value="shor">Shor-vulnerable</option>
          <option value="classically-broken">Classically broken</option>
          <option value="grover">Grover-weakened</option>
          <option value="quantum-safe-classical">Classical Safe</option>
          <option value="pqc">Post-Quantum</option>
        </select>

        {/* Needs Review Toggle */}
        <label className="inline-flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)] cursor-pointer select-none">
          <input
            type="checkbox"
            checked={onlyNeedsReview}
            onChange={(e) => setOnlyNeedsReview(e.target.checked)}
            className="accent-[var(--crypto-pqc)] rounded"
          />
          <span>Confidence &lt; 0.75 only</span>
        </label>
      </div>

      {isLoading ? (
        <div className="p-12 text-center border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-card)] animate-pulse">
          <RefreshCw className="w-5 h-5 animate-spin text-[var(--crypto-pqc)] mx-auto mb-2" />
          <span className="text-xs text-[var(--text-muted)]">LOADING DISCOVERED ASSET INVENTORY...</span>
        </div>
      ) : error ? (
        <div className="p-8 text-center border border-[var(--band-critical)] rounded-lg bg-[var(--surface-card)]">
          <p className="text-xs text-[var(--band-critical)] mb-2">Failed to query asset inventory from API endpoint.</p>
          <button onClick={() => refetch()} className="px-3 py-1 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] text-xs font-bold">
            Retry Query
          </button>
        </div>
      ) : (
        /* Virtualized Table Container */
        <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden bg-[var(--surface-card)]">
          {/* Fixed Header */}
          <div className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] grid grid-cols-12 px-4 py-2.5 font-bold text-[11px] text-[var(--text-secondary)] select-none">
            <div className="col-span-3">ALGORITHM & FAMILY</div>
            <div className="col-span-4">LOCATION & SYMBOL</div>
            <div className="col-span-2">SURFACE & TYPE</div>
            <div className="col-span-1 text-right">SCORE</div>
            <div className="col-span-2 text-right">RISK BAND</div>
          </div>

          {/* Virtualized Body */}
          <div
            ref={parentRef}
            tabIndex={0}
            role="region"
            aria-label="Cryptographic inventory assets table"
            className="h-[520px] overflow-y-auto divide-y divide-[var(--border-subtle)] select-none focus:outline-none focus:ring-1 focus:ring-[var(--crypto-pqc)]"
          >
            {filtered.length === 0 ? (
              <div className="p-12 text-center text-[var(--text-muted)]">
                No cryptographic findings match the selected filter criteria.
              </div>
            ) : (
              <div
                style={{
                  height: `${rowVirtualizer.getTotalSize() || filtered.length * 48}px`,
                  width: '100%',
                  position: 'relative',
                }}
              >
                {(rowVirtualizer.getVirtualItems().length > 0
                  ? rowVirtualizer.getVirtualItems()
                  : filtered.slice(0, 20).map((_, index) => ({ index, start: index * 48, size: 48, key: index }))
                ).map((virtualRow) => {
                  const f = filtered[virtualRow.index];
                  if (!f) return null;
                  const isProposed = f.displayName.includes('[Proposed]');

                  return (
                    <div
                      key={f.id}
                      onClick={() => openDrawer(f)}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualRow.size}px`,
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                      className="grid grid-cols-12 px-4 items-center hover:bg-[var(--surface-raised)] cursor-pointer transition-colors"
                    >
                      {/* Algorithm & Family */}
                      <div className="col-span-3 flex items-center gap-2 min-w-0 pr-2">
                        <span className="font-bold text-[var(--text-primary)] truncate">
                          {f.displayName}
                        </span>
                        <CryptoBadge
                          cryptoClass={classifyAlgorithm(f.family, f.displayName, f.risk?.classicallyBroken)}
                          label={f.family ?? undefined}
                          size="sm"
                        />
                        {f.negotiated !== undefined && f.negotiated !== null && (
                          <span
                            className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase tracking-wider border ${
                              f.negotiated
                                ? 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border-[var(--crypto-pqc-border)]'
                                : 'bg-[var(--surface-raised)] text-[var(--text-secondary)] border-[var(--border-subtle)]'
                            }`}
                          >
                            {f.negotiated ? 'NEGOTIATED' : 'SUPPORTED'}
                          </span>
                        )}
                        {isProposed && (
                          <span
                            title="[Proposed: Hardware security module & cloud discovery pending backend implementation]"
                            className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold flex items-center gap-0.5 flex-shrink-0"
                          >
                            <Cpu className="w-2.5 h-2.5" />
                            <span>PROPOSED</span>
                          </span>
                        )}
                      </div>

                      {/* Location & Symbol */}
                      <div className="col-span-4 truncate text-[var(--text-muted)] pr-2">
                        <span className="text-[var(--text-secondary)]">{f.location.path}</span>
                        {f.location.line && <span>:{f.location.line}</span>}
                        {f.symbol && <span className="text-[var(--text-muted)] ml-1.5">({f.symbol})</span>}
                      </div>

                      {/* Surface & Kind */}
                      <div className="col-span-2 text-[var(--text-secondary)] truncate">
                        <span className="px-1.5 py-0.5 rounded bg-[var(--surface-raised)] text-[10px] border border-[var(--border-subtle)]">
                          {f.surface}
                        </span>
                      </div>

                      {/* Score */}
                      <div className="col-span-1 text-right font-bold num-tabular text-[var(--text-primary)]">
                        {f.risk ? f.risk.score.toFixed(1) : '—'}
                      </div>

                      {/* Risk Band */}
                      <div className="col-span-2 flex items-center justify-end gap-1.5">
                        {f.risk && <RiskBandBadge band={f.risk.band} score={f.risk.score} size="sm" />}
                        {f.risk?.needsReview && (
                          <span
                            title="Confidence < 0.75: Needs human review"
                            className="text-[9px] px-1 py-0.2 rounded border border-dashed border-[var(--band-medium)] text-[var(--band-medium)] font-bold"
                          >
                            REVIEW
                          </span>
                        )}
                        <ExternalLink className="w-3.5 h-3.5 text-[var(--text-muted)] ml-1" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
