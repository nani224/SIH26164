'use client';

import { useState, useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../../lib/store';
import { mockFindings } from '../../mocks/data';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { CbomExportButton } from '../../components/CbomExportButton';
import { classifyAlgorithm, type Finding, type RiskBand } from '../../types/crypto';
import {
  ListFilter,
  Search,
  SlidersHorizontal,
  Bookmark,
  ChevronDown,
  ArrowUpDown,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';

export default function InventoryPage() {
  const { activeScanId, openDrawer } = useAppStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBand, setSelectedBand] = useState<string>('all');
  const [selectedFamily, setSelectedFamily] = useState<string>('all');
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [activePreset, setActivePreset] = useState<'all' | 'hndl' | 'broken' | 'review'>('all');

  // Generate 1,000+ synthetic high-density items modeled accurately from mock findings for virtualization testing
  const allFindings = useMemo(() => {
    const list: Finding[] = [];
    for (let i = 0; i < 150; i++) {
      mockFindings.forEach((base, idx) => {
        list.push({
          ...base,
          id: `f-${i * 10 + idx + 1}`,
          location: {
            ...base.location,
            line: base.location.line + i * 14,
            path: i % 2 === 0 ? base.location.path : `pkg/module_${i}/${base.location.path}`,
          },
        });
      });
    }
    return list;
  }, []);

  // Filter logic
  const filtered = useMemo(() => {
    return allFindings.filter((f) => {
      if (activePreset === 'hndl' && !f.risk.hndl) return false;
      if (activePreset === 'broken' && !f.risk.classicallyBroken) return false;
      if (activePreset === 'review' && !f.risk.needsReview) return false;

      if (selectedBand !== 'all' && f.risk.band !== selectedBand) return false;
      if (selectedFamily !== 'all') {
        const cls = classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken);
        if (cls !== selectedFamily) return false;
      }
      if (onlyNeedsReview && !f.risk.needsReview) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          f.displayName.toLowerCase().includes(q) ||
          f.family.toLowerCase().includes(q) ||
          f.location.path.toLowerCase().includes(q) ||
          f.surface.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [allFindings, activePreset, selectedBand, selectedFamily, onlyNeedsReview, searchQuery]);

  // Virtualizer setup for 60 fps table scrolling
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 10,
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
            Virtualized 60 fps catalog. Algorithm parameters, attack surfaces, confidence thresholds, and Mosca risk metrics.
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

        {/* Band Filter */}
        <select
          value={selectedBand}
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

      {/* Virtualized Table Container */}
      <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden bg-[var(--surface-card)]">
        {/* Fixed Header */}
        <div className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] grid grid-cols-12 px-4 py-2.5 font-bold text-[11px] text-[var(--text-secondary)] select-none">
          <div className="col-span-3">ALGORITHM & FAMILY</div>
          <div className="col-span-4">LOCATION & SYMBOL</div>
          <div className="col-span-2">SURFACE</div>
          <div className="col-span-1 text-right">SCORE</div>
          <div className="col-span-2 text-right">RISK BAND</div>
        </div>

        {/* Virtualized Body */}
        <div
          ref={parentRef}
          className="h-[520px] overflow-y-auto divide-y divide-[var(--border-subtle)] select-none"
        >
          <div
            style={{
              height: `${rowVirtualizer.getTotalSize()}px`,
              width: '100%',
              position: 'relative',
            }}
          >
            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const item = filtered[virtualRow.index];
              const cls = classifyAlgorithm(item.family, item.displayName, item.risk.classicallyBroken);

              return (
                <div
                  key={item.id}
                  onClick={() => openDrawer(item)}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                  className="grid grid-cols-12 px-4 py-2.5 items-center hover:bg-[var(--surface-card-hover)] cursor-pointer transition-colors border-b border-[var(--border-subtle)]/50"
                >
                  {/* Algorithm & Family */}
                  <div className="col-span-3 flex items-center gap-2 truncate pr-2">
                    <CryptoBadge
                      semanticClass={cls}
                      displayName={item.displayName}
                      needsReview={item.risk.needsReview}
                      size="sm"
                    />
                  </div>

                  {/* Location & Symbol */}
                  <div className="col-span-4 truncate text-[var(--text-secondary)] pr-2">
                    <span className="text-[var(--text-primary)] font-semibold">{item.location.path}</span>
                    <span className="text-[var(--text-muted)] ml-1">:{item.location.line}</span>
                    {item.symbol && (
                      <span className="text-[10px] text-[var(--text-muted)] ml-2">({item.symbol})</span>
                    )}
                  </div>

                  {/* Surface */}
                  <div className="col-span-2 text-[var(--text-muted)] truncate">
                    {item.surface}
                  </div>

                  {/* Score */}
                  <div className="col-span-1 text-right num-tabular font-bold text-[var(--text-primary)]">
                    {item.risk.score.toFixed(1)}
                  </div>

                  {/* Risk Band */}
                  <div className="col-span-2 text-right">
                    <RiskBandBadge band={item.risk.band} score={item.risk.score} showScore={false} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
