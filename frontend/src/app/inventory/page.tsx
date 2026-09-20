'use client';

import { useState, useMemo, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { useAppStore } from '../../lib/store';
import { fetchScanFindings, fetchHsmInventory } from '../../lib/api';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { CbomExportButton } from '../../components/CbomExportButton';
import { AuditVerifySeal } from '../../components/AuditVerifySeal';
import { classifyAlgorithm, type Finding, type HsmSlot, type HsmKey } from '../../types/crypto';
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
  HardDrive,
  Key,
  Lock,
  Layers,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

function InventoryContent() {
  const searchParams = useSearchParams();
  const initialSurface = searchParams.get('surface');
  const { activeScanId, openDrawer } = useAppStore();

  const [activeTab, setActiveTab] = useState<'catalog' | 'hsm'>(
    initialSurface === 'hardware-hsm' ? 'hsm' : 'catalog'
  );
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBand, setSelectedBand] = useState<string>('all');
  const [selectedFamily, setSelectedFamily] = useState<string>('all');
  const [selectedSurface, setSelectedSurface] = useState<string>(
    initialSurface && initialSurface !== 'hardware-hsm' ? initialSurface : 'all'
  );
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [activePreset, setActivePreset] = useState<'all' | 'hndl' | 'broken' | 'review' | 'proposed'>('all');

  // Catalog query
  const {
    data: findingsData,
    isLoading: catalogLoading,
    error: catalogError,
    refetch: refetchCatalog,
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
    enabled: activeTab === 'catalog',
  });

  // HSM inventory query
  const {
    data: hsmData,
    isLoading: hsmLoading,
    error: hsmError,
    refetch: refetchHsm,
  } = useQuery({
    queryKey: ['hsmInventory'],
    queryFn: fetchHsmInventory,
  });

  const virtualRows = useMemo(() => findingsData?.items ?? [], [findingsData]);

  // Catalog filtered items
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

  // Virtualizer setup for catalog
  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,
    overscan: 12,
  });

  // Helper to construct a synthetic Finding for opening in FindingDrawer when an HSM key is clicked
  const handleOpenHsmKeyDrawer = (slot: HsmSlot, key: HsmKey) => {
    const isPqc = key.type.includes('ML-') || key.type.includes('SLH-');
    const isBroken = key.type.includes('DES');
    const isShor = key.type.includes('RSA') || key.type.includes('ECDSA') || key.type.includes('EC');

    const hsmFinding: Finding = {
      id: `hsm-slot-${slot.slot}-${key.label.toLowerCase().replace(/[^a-z0-9]/g, '-')}`,
      displayName: `${key.label} [PKCS#11 Slot ${slot.slot}]`,
      family: (key.type === 'DES3' ? '3DES' : key.type) as Finding['family'],
      surface: 'hardware-hsm',
      kind: 'key',
      keySize: key.size,
      mode: null,
      curve: null,
      function: 'keygen',
      snippet: '',
      source: 'binary-symbol',
      confidence: 1.0,
      location: {
        path: `pkcs11://token/${encodeURIComponent(slot.label)}/key/${encodeURIComponent(key.label)}`,
        line: slot.slot,
        offset: null,
        layer: null,
      },
      symbol: `PKCS11_KEY_${key.type}_${key.size}`,
      negotiated: false,
      triage: {
        status: 'open',
      },
      risk: {
        score: isPqc ? 5.0 : isBroken ? 88.0 : isShor ? 72.0 : 12.0,
        band: isPqc ? 'low' : isBroken || isShor ? 'critical' : 'low',
        V: isPqc ? 0.2 : 1.0,
        F: 0.9,
        U: 1.0,
        E: isPqc ? 0.1 : 0.95,
        K: isPqc ? 0.1 : 0.9,
        X: 10,
        Y: 5,
        Z: 10,
        moscaMargin: isPqc ? -5 : 5,
        reason: isPqc
          ? 'NIST FIPS 203/204 Post-Quantum key residing inside hardware boundary.'
          : isBroken
          ? 'Classically broken 3DES cipher key stored in hardware token.'
          : isShor
          ? 'Shor-vulnerable asymmetric key material subject to CRQC quantum attack.'
          : 'Quantum-safe symmetric key material.',
        hndl: isShor,
        classicallyBroken: isBroken,
        needsReview: false,
      },
      recommendation: {
        action: isPqc
          ? 'Maintain current PQC implementation under CNSA 2.0 standards'
          : `Migrate ${key.label} to NIST FIPS 203/204 PQC algorithm standard`,
        target: isShor ? 'ML-DSA-65 / ML-KEM-768' : isBroken ? 'AES-256-GCM / ML-KEM-768' : 'ML-KEM-768',
        cost: {
          pkBytesDelta: 0,
          wireBytesDelta: 0,
          opMsDelta: 0,
        },
      },
    };

    openDrawer(hsmFinding);
  };

  // HSM inventory metrics
  const hsmMetrics = useMemo(() => {
    if (!hsmData?.slots) return { totalSlots: 0, totalKeys: 0, pqcKeys: 0, shorKeys: 0, brokenKeys: 0 };
    let totalKeys = 0;
    let pqcKeys = 0;
    let shorKeys = 0;
    let brokenKeys = 0;

    hsmData.slots.forEach((slot) => {
      slot.keys.forEach((k) => {
        totalKeys++;
        const norm = k.type.toUpperCase();
        if (norm.includes('ML-') || norm.includes('SLH-')) pqcKeys++;
        else if (norm.includes('DES') || norm.includes('MD5')) brokenKeys++;
        else if (norm.includes('RSA') || norm.includes('ECDSA') || norm.includes('EC')) shorKeys++;
      });
    });

    return {
      totalSlots: hsmData.slots.length,
      totalKeys,
      pqcKeys,
      shorKeys,
      brokenKeys,
    };
  }, [hsmData]);

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
            {activeTab === 'catalog'
              ? `Discovered Cryptographic Assets (${filtered.length.toLocaleString()} items)`
              : `Hardware HSM Partition Inventory (${hsmMetrics.totalKeys} keys across ${hsmMetrics.totalSlots} slots)`}
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            {activeTab === 'catalog'
              ? 'Virtualized 60 fps catalog. Live API queries via TanStack Query. Hardware and Cloud KMS appear with [Proposed] tag.'
              : 'Real SoftHSM2 PKCS#11 hardware token slots, partition isolation, key labels, and NIST PQC migration readiness.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CbomExportButton scanId={activeScanId} />
        </div>
      </div>

      {/* Main Mode Navigation: Catalog vs HSM */}
      <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] pb-2" role="tablist" aria-label="Inventory View Selection">
        <button
          role="tab"
          aria-selected={activeTab === 'catalog'}
          onClick={() => setActiveTab('catalog')}
          className={`px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 ${
            activeTab === 'catalog'
              ? 'bg-[var(--surface-card)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] shadow-sm'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)]'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Discovered Assets Catalog</span>
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'hsm'}
          onClick={() => setActiveTab('hsm')}
          className={`px-3 py-1.5 rounded text-xs font-bold transition-all flex items-center gap-1.5 ${
            activeTab === 'hsm'
              ? 'bg-[var(--surface-card)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] shadow-sm'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)]'
          }`}
        >
          <HardDrive className="w-3.5 h-3.5" />
          <span>Hardware HSM Partitions (PKCS#11)</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold">
            {hsmMetrics.totalKeys} KEYS
          </span>
        </button>
      </div>

      {/* VIEW 1: CATALOG INVENTORY */}
      {activeTab === 'catalog' && (
        <div className="space-y-4">
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
              onChange={(e) => {
                const val = e.target.value;
                if (val === 'hardware-hsm') {
                  setActiveTab('hsm');
                } else {
                  setSelectedSurface(val);
                }
              }}
              className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
            >
              <option value="all">All Attack Surfaces</option>
              <option value="source-ast">Source AST</option>
              <option value="binary-embedded">Binary Embedded</option>
              <option value="network-protocol">Network Protocol</option>
              <option value="hardware-module">Hardware Module [Proposed]</option>
              <option value="hardware-hsm">Hardware HSM (SoftHSM2 / PKCS#11)</option>
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

          {catalogLoading ? (
            <div className="p-12 text-center border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-card)] animate-pulse">
              <RefreshCw className="w-5 h-5 animate-spin text-[var(--crypto-pqc)] mx-auto mb-2" />
              <span className="text-xs text-[var(--text-muted)]">LOADING DISCOVERED ASSET INVENTORY...</span>
            </div>
          ) : catalogError ? (
            <div className="p-8 text-center border border-[var(--band-critical)] rounded-lg bg-[var(--surface-card)]">
              <p className="text-xs text-[var(--band-critical)] mb-2">Failed to query asset inventory from API endpoint.</p>
              <button
                onClick={() => refetchCatalog()}
                className="px-3 py-1 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] text-xs font-bold"
              >
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
      )}

      {/* VIEW 2: HARDWARE HSM PARTITIONS */}
      {activeTab === 'hsm' && (
        <div className="space-y-6" data-testid="hsm-inventory-view">
          {/* Bento Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-bold flex items-center gap-1">
                <HardDrive className="w-3 h-3 text-[var(--crypto-pqc)]" />
                <span>SoftHSM2 Slots</span>
              </span>
              <div className="text-xl font-bold text-[var(--text-primary)] mt-1">
                {hsmMetrics.totalSlots}
              </div>
              <span className="text-[10px] text-[var(--crypto-pqc)] font-semibold">Online & Initialized</span>
            </div>

            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-bold flex items-center gap-1">
                <Key className="w-3 h-3 text-[var(--text-secondary)]" />
                <span>Total Stored Keys</span>
              </span>
              <div className="text-xl font-bold text-[var(--text-primary)] mt-1">
                {hsmMetrics.totalKeys}
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">PKCS#11 Key Objects</span>
            </div>

            <div className="bg-[var(--surface-card)] border border-[var(--crypto-pqc-border)] p-3 rounded-lg">
              <span className="text-[10px] text-[var(--crypto-pqc)] uppercase font-bold flex items-center gap-1">
                <ShieldCheck className="w-3 h-3 text-[var(--crypto-pqc)]" />
                <span>Post-Quantum Keys</span>
              </span>
              <div className="text-xl font-bold text-[var(--crypto-pqc)] mt-1">
                {hsmMetrics.pqcKeys}
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">ML-KEM-768 · ML-DSA-65</span>
            </div>

            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg">
              <span className="text-[10px] text-[var(--crypto-shor)] uppercase font-bold flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-[var(--crypto-shor)]" />
                <span>Shor-Vulnerable</span>
              </span>
              <div className="text-xl font-bold text-[var(--crypto-shor)] mt-1">
                {hsmMetrics.shorKeys}
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">RSA-4096 · ECDSA P-256</span>
            </div>

            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-3 rounded-lg">
              <span className="text-[10px] text-[var(--band-critical)] uppercase font-bold flex items-center gap-1">
                <ShieldAlert className="w-3 h-3 text-[var(--band-critical)]" />
                <span>Classically Broken</span>
              </span>
              <div className="text-xl font-bold text-[var(--band-critical)] mt-1">
                {hsmMetrics.brokenKeys}
              </div>
              <span className="text-[10px] text-[var(--text-muted)]">DES3 (168-bit)</span>
            </div>
          </div>

          {hsmLoading ? (
            <div className="p-12 text-center border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-card)] animate-pulse">
              <RefreshCw className="w-5 h-5 animate-spin text-[var(--crypto-pqc)] mx-auto mb-2" />
              <span className="text-xs text-[var(--text-muted)]">ENUMERATING PKCS#11 HARDWARE SECURITY MODULES...</span>
            </div>
          ) : hsmError ? (
            <div className="p-8 text-center border border-[var(--band-critical)] rounded-lg bg-[var(--surface-card)]">
              <p className="text-xs text-[var(--band-critical)] mb-2">Failed to query SoftHSM2 inventory.</p>
              <button
                onClick={() => refetchHsm()}
                className="px-3 py-1 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] text-xs font-bold"
              >
                Retry Enumeration
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {hsmData?.slots.map((slot) => (
                <div
                  key={slot.slot}
                  className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl overflow-hidden shadow-sm"
                  data-testid={`hsm-slot-${slot.slot}`}
                >
                  {/* Slot Header */}
                  <div className="bg-[var(--surface-raised)] px-4 py-3 border-b border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] flex items-center justify-center font-bold text-xs">
                        #{slot.slot}
                      </div>
                      <div>
                        <h2 className="text-sm font-bold text-[var(--text-primary)]">
                          {slot.label}
                        </h2>
                        <div className="flex items-center gap-2 text-[11px] text-[var(--text-muted)] mt-0.5">
                          <span>Token Slot {slot.slot}</span>
                          <span>·</span>
                          <span>SoftHSM2 PKCS#11 v2.40</span>
                          <span>·</span>
                          <span className="text-[var(--crypto-pqc)] font-bold">Partition Online</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)] font-bold">
                        {slot.keys.length} Keys Enumerated
                      </span>
                    </div>
                  </div>

                  {/* Keys Table */}
                  <div className="divide-y divide-[var(--border-subtle)]">
                    <div className="grid grid-cols-12 px-4 py-2 text-[10px] font-bold uppercase text-[var(--text-muted)] bg-[var(--surface-base)] border-b border-[var(--border-subtle)]">
                      <div className="col-span-5">Key Label & Identifier</div>
                      <div className="col-span-2">Algorithm Type</div>
                      <div className="col-span-2">Key Size</div>
                      <div className="col-span-2">PQC Readiness</div>
                      <div className="col-span-1 text-right">Action</div>
                    </div>

                    {slot.keys.map((k, idx) => {
                      const isPqc = k.type.includes('ML-') || k.type.includes('SLH-');
                      const isBroken = k.type.includes('DES');
                      const isShor = k.type.includes('RSA') || k.type.includes('ECDSA') || k.type.includes('EC');

                      return (
                        <div
                          key={idx}
                          onClick={() => handleOpenHsmKeyDrawer(slot, k)}
                          className="grid grid-cols-12 px-4 py-3 items-center hover:bg-[var(--surface-raised)] cursor-pointer transition-colors"
                        >
                          {/* Label */}
                          <div className="col-span-5 flex items-center gap-2 min-w-0 pr-2">
                            <Key className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                            <span className="font-bold text-[var(--text-primary)] truncate">
                              {k.label}
                            </span>
                          </div>

                          {/* Type */}
                          <div className="col-span-2">
                            <span className="px-2 py-0.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-bold">
                              {k.type}
                            </span>
                          </div>

                          {/* Size */}
                          <div className="col-span-2 text-[var(--text-secondary)] num-tabular">
                            {k.size > 0 ? `${k.size}-bit` : 'Standard'}
                          </div>

                          {/* PQC Readiness */}
                          <div className="col-span-2">
                            {isPqc ? (
                              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]">
                                POST-QUANTUM
                              </span>
                            ) : isBroken ? (
                              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-[var(--crypto-broken-bg)] border border-[var(--crypto-broken-border)] text-[var(--crypto-broken)]">
                                CLASSICALLY-BROKEN
                              </span>
                            ) : isShor ? (
                              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-[var(--crypto-shor-bg)] border border-[var(--crypto-shor-border)] text-[var(--crypto-shor)]">
                                SHOR-VULNERABLE
                              </span>
                            ) : (
                              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-[var(--crypto-classical-bg)] border border-[var(--crypto-classical-border)] text-[var(--crypto-classical)]">
                                QUANTUM-SAFE
                              </span>
                            )}
                          </div>

                          {/* Action */}
                          <div className="col-span-1 text-right">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenHsmKeyDrawer(slot, k);
                              }}
                              className="px-2 py-1 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-[10px] font-bold inline-flex items-center gap-1"
                              title="Inspect key details and remediation recommendation"
                            >
                              <span>Inspect</span>
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Audit Verification Seal attached to HSM Inventory view */}
          <div className="mt-6 pt-4 border-t border-[var(--border-subtle)]">
            <AuditVerifySeal variant="card" />
          </div>
        </div>
      )}
    </div>
  );
}

export default function InventoryPage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center border border-[var(--border-subtle)] rounded-lg bg-[var(--surface-card)] animate-pulse font-mono text-xs">
          <RefreshCw className="w-5 h-5 animate-spin text-[var(--crypto-pqc)] mx-auto mb-2" />
          <span className="text-xs text-[var(--text-muted)]">LOADING CRYPTOGRAPHIC INVENTORY...</span>
        </div>
      }
    >
      <InventoryContent />
    </Suspense>
  );
}
