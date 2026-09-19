'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '../lib/store';
import { triageFinding } from '../lib/api';
import { CryptoBadge } from './CryptoBadge';
import { RiskBandBadge } from './RiskBandBadge';
import { classifyAlgorithm, type Finding } from '../types/crypto';
import {
  X,
  Shield,
  Code2,
  FileCode,
  Layers,
  Calculator,
  ArrowRight,
  Cpu,
  CheckCircle2,
  Save,
  Clock,
  Sparkles,
  Check,
} from 'lucide-react';

export function FindingDrawer() {
  const { selectedFinding, isDrawerOpen, closeDrawer } = useAppStore();
  const [triageStatus, setTriageStatus] = useState<Finding['triage']['status'] | null>(null);
  const [triageNote, setTriageNote] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (!isDrawerOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDrawer();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDrawerOpen, closeDrawer]);

  if (!isDrawerOpen || !selectedFinding) return null;

  const finding = selectedFinding;
  const { risk, recommendation } = finding;
  const activeStatus = triageStatus || finding.triage.status;

  if (!risk || !recommendation) {
    // Nullable per contract (an unscored finding); this drawer is
    // risk/recommendation-focused, so show a minimal fallback rather than
    // fabricate numbers.
    return (
      <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true" aria-label="Cryptographic finding details drawer">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeDrawer} />
        <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
          <div className="w-screen max-w-md bg-[var(--surface-base)] border-l border-[var(--border-prominent)] shadow-2xl flex flex-col p-6 font-mono text-xs">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-[var(--text-primary)]">{finding.displayName}</h2>
              <button onClick={closeDrawer} aria-label="Close drawer" className="p-1.5 rounded hover:bg-[var(--surface-card-hover)]">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-[var(--text-muted)]">
              This finding has not been risk-scored yet (scan still in progress, or scoring failed for
              this asset). No risk waterfall or PQC recommendation is available.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const semanticClass = classifyAlgorithm(finding.family, finding.displayName, risk.classicallyBroken);

  const handleTriageSave = async () => {
    setIsSaving(true);
    try {
      await triageFinding(finding.id, {
        status: activeStatus,
        note: triageNote || finding.triage.note || undefined,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2000);
    } catch (e) {
      console.error('Triage error:', e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true" aria-label="Cryptographic finding details drawer">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={closeDrawer}
      />

      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-[var(--surface-base)] border-l border-[var(--border-prominent)] shadow-2xl flex flex-col">
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <CryptoBadge
                  semanticClass={semanticClass}
                  displayName={finding.displayName}
                  needsReview={risk.needsReview}
                />
                <RiskBandBadge band={risk.band} score={risk.score} />
              </div>
              <h2 className="text-lg font-mono font-bold text-[var(--text-primary)]">
                {finding.displayName} in {finding.location.path}
              </h2>
              <p className="text-xs font-mono text-[var(--text-muted)] mt-1">
                Finding ID: {finding.id} · Surface: {finding.surface} · Source: {finding.source}
              </p>
            </div>
            <button
              onClick={closeDrawer}
              className="p-1.5 rounded hover:bg-[var(--surface-card-hover)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Body */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 font-mono text-xs">
            {/* Threat Summary */}
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg space-y-2">
              <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-[var(--crypto-shor)]" />
                <span>Quantum & Classical Threat Assessment</span>
              </div>
              <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                {risk.reason}
              </p>
              {risk.hndl && (
                <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border border-[var(--crypto-shor-border)] text-[10px] font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />
                  <span>HARVEST NOW, DECRYPT LATER (HNDL) ACTIVE EXPOSURE</span>
                </div>
              )}
            </div>

            {/* V*F*U*E*K Mathematical Waterfall */}
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg space-y-3">
              <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Calculator className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                  <span>Risk Score Mathematical Waterfall</span>
                </span>
                <span className="text-[var(--text-primary)] font-bold text-sm num-tabular">
                  {risk.score.toFixed(1)} / 100
                </span>
              </div>
              <div className="grid grid-cols-5 gap-2 text-center py-2 border-y border-[var(--border-subtle)]">
                <div>
                  <div className="text-[10px] text-[var(--text-muted)]">V (Vuln)</div>
                  <div className="font-bold text-[var(--text-primary)] text-sm num-tabular">{risk.V}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[var(--text-muted)]">F (Func)</div>
                  <div className="font-bold text-[var(--text-primary)] text-sm num-tabular">{risk.F}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[var(--text-muted)]">U (Urgency)</div>
                  <div className="font-bold text-[var(--crypto-pqc)] text-sm num-tabular">{risk.U.toFixed(2)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[var(--text-muted)]">E (Exposure)</div>
                  <div className="font-bold text-[var(--text-primary)] text-sm num-tabular">{risk.E}</div>
                </div>
                <div>
                  <div className="text-[10px] text-[var(--text-muted)]">K (Crit)</div>
                  <div className="font-bold text-[var(--text-primary)] text-sm num-tabular">{risk.K}</div>
                </div>
              </div>
              <div className="text-[10px] text-[var(--text-secondary)] flex justify-between">
                <span>Formula: $100 \times V \times F \times U \times E \times K$</span>
                <span>Mosca Margin: $X({risk.X}y) + Y({risk.Y}y) - Z({risk.Z}y) = {risk.moscaMargin}y$</span>
              </div>
            </div>

            {/* Code / Hex Snippet with line & offset */}
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden">
              <div className="bg-[var(--surface-raised)] px-4 py-2 border-b border-[var(--border-subtle)] flex items-center justify-between">
                <span className="text-[11px] font-bold text-[var(--text-secondary)] flex items-center gap-1.5">
                  <Code2 className="w-3.5 h-3.5 text-[var(--crypto-safe-classical)]" />
                  <span>Evidence Snippet · Line {finding.location.line} {finding.location.offset !== undefined ? `· Byte Offset ${finding.location.offset}` : ''}</span>
                </span>
                <span className="text-[10px] text-[var(--text-muted)]">{finding.location.path}</span>
              </div>
              <div className="p-3 bg-black/40 overflow-x-auto text-[11px] font-mono-code text-[var(--text-primary)]">
                <code>{finding.snippet || `[0x${(finding.location.offset || 0).toString(16).padStart(8, '0')}]: ${finding.displayName} detected`}</code>
              </div>
            </div>

            {/* PQC Recommendation with Cost Deltas */}
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg space-y-3">
              <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                <span>NIST Post-Quantum Replacement Strategy</span>
              </div>
              <div className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
                <div className="text-xs font-semibold text-[var(--crypto-pqc)]">
                  Target: {recommendation.target}
                </div>
                <div className="text-[11px] text-[var(--text-secondary)] mt-1">
                  {recommendation.action}
                </div>
              </div>

              {/* Byte & Latency deltas */}
              <div className="grid grid-cols-3 gap-2 text-center text-[10px] pt-1">
                <div className="bg-[var(--surface-raised)] p-2 rounded border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-muted)]">Δ Public Key</div>
                  <div className="font-bold text-[var(--text-primary)] text-xs mt-0.5 num-tabular">
                    {recommendation.cost.pkBytesDelta > 0 ? `+${recommendation.cost.pkBytesDelta}` : recommendation.cost.pkBytesDelta} B
                  </div>
                </div>
                <div className="bg-[var(--surface-raised)] p-2 rounded border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-muted)]">Δ Wire / Ciphertext</div>
                  <div className="font-bold text-[var(--text-primary)] text-xs mt-0.5 num-tabular">
                    {recommendation.cost.wireBytesDelta > 0 ? `+${recommendation.cost.wireBytesDelta}` : recommendation.cost.wireBytesDelta} B
                  </div>
                </div>
                <div className="bg-[var(--surface-raised)] p-2 rounded border border-[var(--border-subtle)]">
                  <div className="text-[var(--text-muted)]">Δ Op Latency</div>
                  <div className="font-bold text-[var(--text-primary)] text-xs mt-0.5 num-tabular">
                    {recommendation.cost.opMsDelta > 0 ? `+${recommendation.cost.opMsDelta}` : recommendation.cost.opMsDelta} ms
                  </div>
                </div>
              </div>
            </div>

            {/* Analyst Triage Actions */}
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg space-y-3">
              <div className="text-[11px] font-bold text-[var(--text-muted)] uppercase">
                Analyst Triage & Operational Decision
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: 'open', label: 'Open Threat' },
                  { id: 'accepted-risk', label: 'Accepted Risk' },
                  { id: 'false-positive', label: 'False Positive' },
                  { id: 'fixed', label: 'Fixed / Mitigated' },
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setTriageStatus(item.id as Finding['triage']['status'])}
                    className={`py-1.5 px-2 rounded border text-center transition-all ${
                      activeStatus === item.id
                        ? 'bg-[var(--crypto-pqc-bg)] border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] font-bold'
                        : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-prominent)]'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-muted)] block mb-1">
                  Analyst Operational Justification / Note:
                </label>
                <textarea
                  rows={2}
                  value={triageNote || finding.triage.note || ''}
                  onChange={(e) => setTriageNote(e.target.value)}
                  placeholder="Record cryptographic justification, remediation ticket, or migration milestone..."
                  className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-1">
                <button
                  onClick={handleTriageSave}
                  disabled={isSaving}
                  className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity flex items-center gap-1.5"
                >
                  {savedSuccess ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      <span>TRIAGE SAVED</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-3.5 h-3.5" />
                      <span>{isSaving ? 'SAVING...' : 'COMMIT DECISION'}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
