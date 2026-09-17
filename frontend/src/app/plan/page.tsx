'use client';

import { useState } from 'react';
import { useAppStore } from '../../lib/store';
import { mockFindings } from '../../mocks/data';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { classifyAlgorithm, type Finding } from '../../types/crypto';
import {
  FileText,
  Download,
  FileCode,
  ArrowRight,
  Shield,
  Clock,
  Layers,
  Check,
  AlertCircle,
} from 'lucide-react';

export default function MigrationPlanPage() {
  const { openDrawer } = useAppStore();
  const [downloaded, setDownloaded] = useState(false);

  // Group findings by system component
  const systems = [
    {
      name: 'Core Network Gateway & SSH Bastion',
      exposure: 'External (Perimeter)',
      criticality: 'Mission-Critical',
      items: mockFindings.filter(
        (f) => f.location.path.includes('sshd') || f.location.path.includes('gateway')
      ),
    },
    {
      name: 'Legacy Authentication & Microservices',
      exposure: 'Internal (Mesh)',
      criticality: 'High',
      items: mockFindings.filter(
        (f) => f.location.path.includes('legacy') || f.location.path.includes('firmware')
      ),
    },
    {
      name: 'Data Storage & Vault',
      exposure: 'Isolated (Enclave)',
      criticality: 'High',
      items: mockFindings.filter(
        (f) => f.location.path.includes('storage') || f.location.path.includes('vault')
      ),
    },
  ];

  const handleDownloadPlanJson = () => {
    const planJson = mockFindings.map((f) => ({
      location: f.location.path,
      line: f.location.line,
      asset: f.displayName,
      score: f.risk.score,
      band: f.risk.band,
      reason: f.risk.reason,
      mosca_margin: f.risk.moscaMargin,
      confidence: f.confidence,
      action: f.recommendation.action,
      target: f.recommendation.target,
      cost_deltas: f.recommendation.cost,
    }));

    const blob = new Blob([JSON.stringify(planJson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ecdat-remediation-plan.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2000);
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <FileText className="w-3.5 h-3.5" />
            <span>SCREEN 9 · REMEDIATION MIGRATION PLAN</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Prioritized Post-Quantum Remediation Plan
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Grouped by system exposure, ordered by threat score. Target algorithms with byte/ms cost delta trade-offs.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Executive PDF button disabled with [Proposed] tooltip */}
          <button
            disabled
            className="px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-muted)] cursor-not-allowed opacity-60 flex items-center gap-1.5"
            title="[Proposed: Executive PDF generation logged in contracts/PROPOSALS.md pending backend implementation]"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>EXECUTIVE PDF [PROPOSED]</span>
          </button>

          {/* JSON Export button */}
          <button
            onClick={handleDownloadPlanJson}
            className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity flex items-center gap-1.5"
          >
            {downloaded ? (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>EXPORTED</span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>EXPORT PLAN JSON</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Systems Groups */}
      <div className="space-y-6">
        {systems.map((sys, idx) => (
          <div
            key={idx}
            className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-4 shadow-lg"
          >
            {/* System Group Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
              <div>
                <span className="text-sm font-bold text-[var(--text-primary)]">{sys.name}</span>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  Exposure: {sys.exposure} · Criticality: {sys.criticality}
                </div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--crypto-pqc)] font-bold">
                {sys.items.length} Actionable Item{sys.items.length > 1 ? 's' : ''}
              </span>
            </div>

            {/* Findings under this system */}
            <div className="space-y-3">
              {sys.items.map((item) => {
                const cls = classifyAlgorithm(item.family, item.displayName, item.risk.classicallyBroken);

                return (
                  <div
                    key={item.id}
                    onClick={() => openDrawer(item)}
                    className="p-3.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--border-focus)] transition-all cursor-pointer space-y-2.5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <CryptoBadge semanticClass={cls} displayName={item.displayName} size="sm" />
                        <span className="text-[var(--text-primary)] font-semibold">{item.location.path}:{item.location.line}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <RiskBandBadge band={item.risk.band} score={item.risk.score} />
                      </div>
                    </div>

                    {/* Action & Target */}
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 bg-[var(--surface-base)] p-2.5 rounded border border-[var(--border-subtle)]">
                      <div className="space-y-0.5">
                        <div className="text-[10px] text-[var(--text-muted)] uppercase">Recommended Migration</div>
                        <div className="text-xs text-[var(--text-primary)]">
                          <strong className="text-[var(--crypto-pqc)]">{item.recommendation.target}</strong>: {item.recommendation.action}
                        </div>
                      </div>

                      {/* Cost Delta Bars */}
                      <div className="flex items-center gap-3 text-right font-mono text-[10px] pt-1 md:pt-0">
                        <div>
                          <span className="text-[var(--text-muted)] block">Δ Wire</span>
                          <span className="font-bold text-[var(--text-primary)] num-tabular">
                            {item.recommendation.cost.wireBytesDelta > 0 ? `+${item.recommendation.cost.wireBytesDelta}` : item.recommendation.cost.wireBytesDelta} B
                          </span>
                        </div>
                        <div>
                          <span className="text-[var(--text-muted)] block">Δ Latency</span>
                          <span className="font-bold text-[var(--text-primary)] num-tabular">
                            {item.recommendation.cost.opMsDelta > 0 ? `+${item.recommendation.cost.opMsDelta}` : item.recommendation.cost.opMsDelta} ms
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
