'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchCloudKeys } from '../lib/api';
import type { CloudKeysResponse, CloudKeyRecord } from '../types/crypto';
import {
  X,
  Cloud,
  Key,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';

interface CloudKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CloudKeysModal({ isOpen, onClose }: CloudKeysModalProps) {
  const { data: cloudData, isLoading } = useQuery<CloudKeysResponse>({
    queryKey: ['cloudKeys'],
    queryFn: () => fetchCloudKeys(),
    enabled: isOpen,
  });

  if (!isOpen) return null;

  const keys = cloudData?.keys ?? [];
  const roadmapText =
    cloudData?.roadmap ??
    '[Roadmap] AWS KMS via LocalStack is actively supported in v1.0. Azure Key Vault and GCP Cloud HSM are scheduled for v1.1.';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cloud KMS Cryptographic Keys"
      className="fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-12 flex items-center justify-center font-mono text-xs"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal Container */}
      <div className="relative w-full max-w-3xl bg-[var(--surface-base)] border border-[var(--border-prominent)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]">
              <Cloud className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-[var(--text-primary)]">
                Cloud KMS Cryptographic Keys (AWS KMS)
              </h2>
              <p className="text-[11px] text-[var(--text-muted)]">
                Cryptographic material discovered from cloud key management services (NTRO SIH26164)
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

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {/* Honest Roadmap Transparency Notice */}
          <div className="p-3.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px] space-y-1">
            <div className="font-bold text-[var(--crypto-pqc)] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" />
              <span>Multi-Cloud Integration Transparency</span>
            </div>
            <p className="text-[var(--text-secondary)] leading-relaxed">{roadmapText}</p>
          </div>

          {/* Keys Table */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[var(--text-primary)] uppercase text-[10px]">
                Discovered KMS Keys ({keys.length})
              </span>
              <span className="text-[10px] text-[var(--text-muted)]">
                Audit Standard: NIST SP 800-57 (Max 365 Days)
              </span>
            </div>

            {isLoading ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="h-16 rounded bg-[var(--surface-card)] animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden">
                <table className="w-full text-left">
                  <thead className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] uppercase">
                    <tr>
                      <th className="p-3">Key ID / ARN</th>
                      <th className="p-3">Algorithm</th>
                      <th className="p-3">Rotation Age</th>
                      <th className="p-3">Compliance</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)]">
                    {keys.map((k) => {
                      const isOverdue = k.rotationAgeDays > 365 || !k.policyCompliant;
                      return (
                        <tr key={k.keyId} className="hover:bg-[var(--surface-raised)] transition-colors">
                          <td className="p-3">
                            <div className="font-bold text-[var(--text-primary)] font-mono text-[11px] truncate max-w-xs">
                              {k.keyId}
                            </div>
                            <div className="text-[10px] text-[var(--text-muted)] uppercase mt-0.5">
                              Provider: {k.provider}
                            </div>
                          </td>
                          <td className="p-3">
                            <span className="font-bold text-[var(--text-secondary)]">
                              {k.algorithm} ({k.keySize}-bit)
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1.5">
                              <Clock className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                              <span className="font-bold num-tabular text-[var(--text-primary)]">
                                {k.rotationAgeDays} days
                              </span>
                            </div>
                          </td>
                          <td className="p-3">
                            {isOverdue ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border border-[var(--crypto-shor-border)]">
                                <AlertTriangle className="w-3 h-3" />
                                <span>Rotation Overdue</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[var(--coverage-attributed-bg)] text-[var(--coverage-attributed)] border border-[var(--coverage-attributed-border)]">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>Compliant</span>
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
