'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScanPlan } from '../../lib/api';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { classifyAlgorithm, type RemediationPlanItem } from '../../types/crypto';
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
  RefreshCw,
} from 'lucide-react';

export default function MigrationPlanPage() {
  const { activeScanId } = useAppStore();
  const [downloaded, setDownloaded] = useState(false);

  const { data: planItems, isLoading, error } = useQuery({
    queryKey: ['plan', activeScanId],
    queryFn: () => fetchScanPlan(activeScanId),
  });

  const handleDownloadPlanJson = () => {
    if (!planItems) return;
    const blob = new Blob([JSON.stringify(planItems, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ecdat-migration-plan-${activeScanId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 3000);
  };

  // Group plan items by top-level path / module
  const groupedPlan = useMemo(() => {
    if (!planItems) return [];
    const groups = new Map<string, RemediationPlanItem[]>();
    planItems.forEach((item) => {
      const topDir = item.location.split('/')[0] || 'root';
      const current = groups.get(topDir) || [];
      current.push(item);
      groups.set(topDir, current);
    });
    return Array.from(groups.entries()).map(([module, items], idx) => ({
      priority: idx + 1,
      module,
      items,
    }));
  }, [planItems]);

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <FileCode className="w-3.5 h-3.5" />
            <span>SCREEN 9 · POST-QUANTUM MIGRATION ROADMAP</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)]">
            Prioritized Cryptographic Remediation Sequence
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Grouped by subsystem module and risk severity. Live API query via TanStack Query.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* JSON Export Button */}
          <button
            onClick={handleDownloadPlanJson}
            className="px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--border-prominent)] text-[var(--text-primary)] font-bold text-xs flex items-center gap-1.5 transition-colors"
          >
            {downloaded ? <Check className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" /> : <Download className="w-3.5 h-3.5" />}
            <span>{downloaded ? 'PLAN EXPORTED' : 'EXPORT PLAN (JSON)'}</span>
          </button>

          {/* Executive PDF button disabled with [Proposed] tooltip */}
          <button
            disabled
            title="[Proposed: Executive PDF generation logged in contracts/PROPOSALS.md pending backend implementation]"
            className="px-3 py-1.5 rounded bg-[var(--surface-card)] border border-[var(--border-subtle)] text-[var(--text-muted)] opacity-50 cursor-not-allowed font-bold text-xs flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>EXECUTIVE PDF [PROPOSED]</span>
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
          <span>QUERYING REMEDIATION PLAN FROM API...</span>
        </div>
      ) : error ? (
        <div className="p-8 text-center text-xs border border-[var(--band-critical)] rounded-lg bg-[var(--surface-card)]">
          <p className="text-[var(--band-critical)]">Failed to load migration plan from API.</p>
        </div>
      ) : (
        /* Subsystem Remediation Sections */
        <div className="space-y-6">
          {groupedPlan.map((group) => (
            <div
              key={group.module}
              className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden"
            >
              {/* System Header */}
              <div className="p-4 bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--crypto-pqc)]">
                      STAGE {group.priority}
                    </span>
                    <h2 className="text-sm font-bold text-[var(--text-primary)]">
                      Module: {group.module}/
                    </h2>
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    {group.items.length} actionable cryptographic migration item(s) detected.
                  </div>
                </div>
              </div>

              {/* Finding Items Table */}
              <div className="divide-y divide-[var(--border-subtle)]">
                {group.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 flex items-center justify-between gap-4 hover:bg-[var(--surface-raised)] transition-colors"
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="pt-0.5">
                        <RiskBandBadge band={item.band} score={item.score} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-xs text-[var(--text-primary)]">
                            {item.asset}
                          </span>
                          <CryptoBadge
                            semanticClass={classifyAlgorithm(item.asset, item.asset)}
                            displayName={item.asset}
                            size="sm"
                          />
                        </div>
                        <p className="text-[11px] text-[var(--text-muted)] truncate mt-0.5">
                          {item.location}:{item.line}
                        </p>
                        <p className="text-[10px] text-[var(--crypto-pqc)] mt-1">
                          ↳ Target: <strong>{item.target}</strong> ({item.action})
                        </p>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <div className="text-xs font-bold text-[var(--text-primary)] num-tabular">
                        Score {item.score.toFixed(1)}
                      </div>
                      <div className="text-[10px] text-[var(--text-muted)]">
                        Mosca Margin: {item.mosca_margin > 0 ? `+${item.mosca_margin}y` : `${item.mosca_margin}y`}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
