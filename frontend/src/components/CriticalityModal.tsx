'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchAssetCriticalities,
  setAssetCriticality,
  importCriticalityCsv,
  fetchTargets,
} from '../lib/api';
import type {
  AssetCriticality,
  Criticality,
  AssetFacing,
  Finding,
  Target,
} from '../types/crypto';
import {
  X,
  Shield,
  Upload,
  AlertTriangle,
  CheckCircle2,
  ArrowUpDown,
  FileText,
  Plus,
  Trash2,
  Sparkles,
} from 'lucide-react';

interface CriticalityModalProps {
  isOpen: boolean;
  onClose: () => void;
  findings?: Finding[];
  onApplyCriticality?: () => void;
}

export function CriticalityModal({
  isOpen,
  onClose,
  findings = [],
  onApplyCriticality,
}: CriticalityModalProps) {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'editor' | 'import'>('editor');

  // Form states for manual entry
  const [newTargetId, setNewTargetId] = useState('target-001');
  const [newPattern, setNewPattern] = useState('');
  const [newCriticality, setNewCriticality] = useState<Criticality>('mission-critical');
  const [newOwner, setNewOwner] = useState('');
  const [newClassification, setNewClassification] = useState('RESTRICTED');
  const [newFacing, setNewFacing] = useState<AssetFacing>('internal');

  // CSV Import states
  const [csvText, setCsvText] = useState('');
  const [csvError, setCsvError] = useState<string | null>(null);

  // Queries
  const { data: targets = [] } = useQuery<Target[]>({
    queryKey: ['targets'],
    queryFn: fetchTargets,
    enabled: isOpen,
  });

  const { data: criticalities = [] } = useQuery<AssetCriticality[]>({
    queryKey: ['assetCriticalities'],
    queryFn: () => fetchAssetCriticalities(),
    enabled: isOpen,
  });

  // Mutations
  const setMutation = useMutation({
    mutationFn: setAssetCriticality,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assetCriticalities'] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      onApplyCriticality?.();
      setNewPattern('');
      setNewOwner('');
    },
  });

  const importMutation = useMutation({
    mutationFn: importCriticalityCsv,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assetCriticalities'] });
      queryClient.invalidateQueries({ queryKey: ['findings'] });
      queryClient.invalidateQueries({ queryKey: ['estateSummary'] });
      onApplyCriticality?.();
      setCsvText('');
      setCsvError(null);
      setActiveTab('editor');
    },
  });

  // CSV Parsing and Validation
  const parsedCsv = useMemo(() => {
    if (!csvText.trim()) return { records: [], errors: [] };
    const lines = csvText.trim().split('\n');
    const records: AssetCriticality[] = [];
    const errors: string[] = [];

    lines.forEach((line, idx) => {
      const parts = line.split(',').map((p) => p.trim());
      if (idx === 0 && parts[0].toLowerCase() === 'targetid') {
        // Skip header row
        return;
      }
      if (parts.length < 6) {
        errors.push(`Row ${idx + 1}: Expected 6 columns, got ${parts.length}`);
        return;
      }
      const [targetId, pathPattern, crit, businessOwner, dataClassification, facing] = parts;

      if (!['mission-critical', 'high', 'medium', 'low'].includes(crit)) {
        errors.push(`Row ${idx + 1}: Invalid criticality "${crit}". Must be mission-critical, high, medium, or low.`);
        return;
      }

      if (!['internal', 'external'].includes(facing)) {
        errors.push(`Row ${idx + 1}: Invalid facing "${facing}". Must be internal or external.`);
        return;
      }

      records.push({
        targetId,
        pathPattern,
        criticality: crit as Criticality,
        businessOwner,
        dataClassification,
        facing: facing as AssetFacing,
        source: 'import',
      });
    });

    return { records, errors };
  }, [csvText]);

  // Projected Re-ranking Preview
  const projectedRankings = useMemo(() => {
    const combinedCriticalities = [...criticalities, ...parsedCsv.records];
    if (combinedCriticalities.length === 0) return [];

    // Simulate ranking: score boosted if path matches a mission-critical or high asset
    return findings
      .map((f) => {
        let critWeight = 1.0;
        const matchingRule = combinedCriticalities.find((c) => {
          const regex = new RegExp(c.pathPattern.replace(/\*\*/g, '.*'));
          return regex.test(f.location.path);
        });

        if (matchingRule) {
          if (matchingRule.criticality === 'mission-critical') critWeight = 1.8;
          else if (matchingRule.criticality === 'high') critWeight = 1.4;
          else if (matchingRule.criticality === 'medium') critWeight = 1.1;
        }

        const baseScore = f.risk?.score ?? 50;
        const projectedScore = Math.min(100, baseScore * critWeight);
        return {
          id: f.id,
          name: f.displayName,
          path: f.location.path,
          baseScore,
          projectedScore,
          matchingRule,
        };
      })
      .sort((a, b) => b.projectedScore - a.projectedScore);
  }, [findings, criticalities, parsedCsv.records]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Business Criticality & Asset Re-ranking"
      className="fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-12 flex items-center justify-center font-mono text-xs"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal Container */}
      <div className="relative w-full max-w-4xl bg-[var(--surface-base)] border border-[var(--border-prominent)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-[var(--text-primary)]">
                Business Criticality & Finding Re-ranking
              </h2>
              <p className="text-[11px] text-[var(--text-muted)]">
                Define asset criticality, data classification, and internal/external exposure to re-rank findings (NTRO SIH26164)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1.5 rounded hover:bg-[var(--surface-card-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-[var(--border-subtle)] bg-[var(--surface-overlay)] px-4 pt-2">
          <button
            onClick={() => setActiveTab('editor')}
            className={`px-3 py-2 font-bold border-b-2 transition-all ${
              activeTab === 'editor'
                ? 'border-[var(--crypto-pqc)] text-[var(--crypto-pqc)]'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            Criticality Rule Editor ({criticalities.length})
          </button>
          <button
            onClick={() => setActiveTab('import')}
            className={`px-3 py-2 font-bold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === 'import'
                ? 'border-[var(--crypto-pqc)] text-[var(--crypto-pqc)]'
                : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>CSV Import & Re-ranking Preview</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {activeTab === 'editor' && (
            <div className="space-y-6">
              {/* Add New Criticality Rule Form */}
              <div className="p-4 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] space-y-3">
                <div className="font-bold text-[var(--text-primary)] text-xs flex items-center gap-1.5">
                  <Plus className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                  <span>Add Path Criticality Assignment</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label htmlFor="crit-target-select" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Target</label>
                    <select
                      id="crit-target-select"
                      aria-label="Target selection"
                      value={newTargetId}
                      onChange={(e) => setNewTargetId(e.target.value)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-[var(--text-primary)]"
                    >
                      {targets.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label htmlFor="crit-pattern-input" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Path Pattern</label>
                    <input
                      id="crit-pattern-input"
                      type="text"
                      placeholder="e.g. src/crypto/**"
                      value={newPattern}
                      onChange={(e) => setNewPattern(e.target.value)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)]"
                    />
                  </div>

                  <div>
                    <label htmlFor="crit-level-select" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Criticality</label>
                    <select
                      id="crit-level-select"
                      aria-label="Criticality level"
                      value={newCriticality}
                      onChange={(e) => setNewCriticality(e.target.value as Criticality)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-[var(--text-primary)]"
                    >
                      <option value="mission-critical">Mission Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>

                  <div>
                    <label htmlFor="crit-owner-input" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Business Owner</label>
                    <input
                      id="crit-owner-input"
                      type="text"
                      placeholder="e.g. Cryptography Core Team"
                      value={newOwner}
                      onChange={(e) => setNewOwner(e.target.value)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)]"
                    />
                  </div>

                  <div>
                    <label htmlFor="crit-class-input" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Classification</label>
                    <input
                      id="crit-class-input"
                      type="text"
                      placeholder="e.g. RESTRICTED-DEFENSE"
                      value={newClassification}
                      onChange={(e) => setNewClassification(e.target.value)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-[var(--text-primary)]"
                    />
                  </div>

                  <div>
                    <label htmlFor="crit-facing-select" className="block text-[10px] text-[var(--text-muted)] uppercase mb-1">Facing Exposure</label>
                    <select
                      id="crit-facing-select"
                      aria-label="Facing exposure"
                      value={newFacing}
                      onChange={(e) => setNewFacing(e.target.value as AssetFacing)}
                      className="w-full bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded px-2 py-1.5 text-[var(--text-primary)]"
                    >
                      <option value="internal">Internal Facing</option>
                      <option value="external">External Facing</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={() => {
                    if (!newPattern.trim() || !newOwner.trim()) return;
                    setMutation.mutate({
                      targetId: newTargetId,
                      pathPattern: newPattern.trim(),
                      criticality: newCriticality,
                      businessOwner: newOwner.trim(),
                      dataClassification: newClassification.trim(),
                      facing: newFacing,
                      source: 'manual',
                    });
                  }}
                  disabled={!newPattern.trim() || !newOwner.trim() || setMutation.isPending}
                  className="px-4 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 disabled:opacity-40"
                >
                  {setMutation.isPending ? 'Saving...' : 'Save Criticality Assignment'}
                </button>
              </div>

              {/* Active Rules Table */}
              <div className="space-y-2">
                <span className="font-bold text-[var(--text-secondary)] uppercase text-[10px]">
                  Active Criticality Rules
                </span>
                <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden">
                  <table className="w-full text-left">
                    <thead className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] uppercase">
                      <tr>
                        <th className="p-2.5">Pattern</th>
                        <th className="p-2.5">Criticality</th>
                        <th className="p-2.5">Owner</th>
                        <th className="p-2.5">Classification</th>
                        <th className="p-2.5">Facing</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {criticalities.map((c, i) => (
                        <tr key={i} className="hover:bg-[var(--surface-raised)]">
                          <td className="p-2.5 font-bold text-[var(--text-primary)]">{c.pathPattern}</td>
                          <td className="p-2.5">
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border border-[var(--crypto-shor-border)]">
                              {c.criticality}
                            </span>
                          </td>
                          <td className="p-2.5 text-[var(--text-secondary)]">{c.businessOwner}</td>
                          <td className="p-2.5 text-[var(--text-muted)]">{c.dataClassification}</td>
                          <td className="p-2.5 uppercase font-bold text-[10px]">{c.facing}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'import' && (
            <div className="space-y-5">
              {/* CSV Input */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="csv-textarea" className="font-bold text-[var(--text-primary)]">
                    Paste CSV Records (targetId, pathPattern, criticality, businessOwner, dataClassification, facing)
                  </label>
                  <button
                    onClick={() =>
                      setCsvText(
                        `targetId,pathPattern,criticality,businessOwner,dataClassification,facing\n` +
                        `target-001,src/crypto/**,mission-critical,Cryptographic Architecture Group,RESTRICTED-DEFENSE,internal\n` +
                        `target-001,src/gateway/**,high,External Boundary Operations,CONFIDENTIAL,external\n` +
                        `target-002,firmware/**,mission-critical,Firmware Platform Sec,RESTRICTED-DEFENSE,internal`
                      )
                    }
                    className="text-[10px] text-[var(--crypto-pqc)] hover:underline"
                  >
                    Load Sample CSV
                  </button>
                </div>

                <textarea
                  id="csv-textarea"
                  rows={4}
                  value={csvText}
                  onChange={(e) => setCsvText(e.target.value)}
                  placeholder="target-001,src/crypto/**,mission-critical,Cryptographic Core,RESTRICTED,internal"
                  className="w-full bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded p-2.5 font-mono text-[11px] text-[var(--text-primary)] focus:outline-none focus:border-[var(--crypto-pqc)]"
                />

                {parsedCsv.errors.length > 0 && (
                  <div className="p-3 rounded bg-red-950/40 border border-red-500/50 text-red-300 text-[11px] space-y-1">
                    <div className="font-bold flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>CSV Validation Errors ({parsedCsv.errors.length}):</span>
                    </div>
                    {parsedCsv.errors.map((err, i) => (
                      <div key={i}>• {err}</div>
                    ))}
                  </div>
                )}
              </div>

              {/* Projected Re-ranking Impact Table */}
              {projectedRankings.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                      <ArrowUpDown className="w-3.5 h-3.5 text-[var(--crypto-shor)]" />
                      <span>Projected Finding Re-ranking Impact Preview</span>
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)]">
                      Elevates findings in mission-critical & high paths
                    </span>
                  </div>

                  <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden max-h-56 overflow-y-auto">
                    <table className="w-full text-left">
                      <thead className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] uppercase sticky top-0">
                        <tr>
                          <th className="p-2">Rank</th>
                          <th className="p-2">Finding</th>
                          <th className="p-2">Path</th>
                          <th className="p-2">Base Score</th>
                          <th className="p-2">Re-ranked Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-subtle)]">
                        {projectedRankings.slice(0, 5).map((item, idx) => (
                          <tr key={item.id} className="hover:bg-[var(--surface-raised)]">
                            <td className="p-2 font-bold text-[var(--crypto-shor)]">#{idx + 1}</td>
                            <td className="p-2 font-semibold text-[var(--text-primary)]">{item.name}</td>
                            <td className="p-2 text-[var(--text-muted)]">{item.path}</td>
                            <td className="p-2 num-tabular text-[var(--text-secondary)]">{item.baseScore.toFixed(1)}</td>
                            <td className="p-2 num-tabular font-bold text-[var(--crypto-shor)]">
                              {item.projectedScore.toFixed(1)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <button
                id="confirm-csv-import-btn"
                onClick={() => importMutation.mutate(csvText)}
                disabled={parsedCsv.records.length === 0 || parsedCsv.errors.length > 0 || importMutation.isPending}
                className="w-full py-2.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold disabled:opacity-40 hover:opacity-90 transition-opacity"
              >
                {importMutation.isPending ? 'Applying CSV & Re-ranking...' : `Apply CSV (${parsedCsv.records.length} records) & Re-rank Inventory`}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
