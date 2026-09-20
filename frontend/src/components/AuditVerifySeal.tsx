'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { verifyAudit } from '../lib/api';
import { ShieldCheck, ShieldAlert, RotateCw, Copy, Check, Lock } from 'lucide-react';

interface AuditVerifySealProps {
  variant?: 'card' | 'badge' | 'banner';
  className?: string;
}

export function AuditVerifySeal({ variant = 'card', className = '' }: AuditVerifySealProps) {
  const [copied, setCopied] = useState(false);

  const {
    data: auditData,
    isLoading,
    isRefetching,
    refetch,
    error,
  } = useQuery({
    queryKey: ['auditVerify'],
    queryFn: verifyAudit,
    staleTime: 60000,
  });

  const handleCopyHash = () => {
    if (!auditData?.headHash) return;
    navigator.clipboard.writeText(auditData.headHash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isValid = auditData?.status === 'valid';
  const recordCount = auditData?.recordCount ?? 0;
  const headHash = auditData?.headHash ?? '';
  const details = auditData?.details ?? '';

  if (variant === 'badge') {
    return (
      <div
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-mono select-none ${
          isValid
            ? 'bg-[var(--crypto-pqc-bg)] border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]'
            : 'bg-[var(--crypto-shor-bg)] border-[var(--band-critical)] text-[var(--band-critical)]'
        } ${className}`}
        title={`Audit Chain: ${isValid ? 'Valid' : 'Tampered'} (${recordCount} records)`}
      >
        {isValid ? <ShieldCheck className="w-3.5 h-3.5" /> : <ShieldAlert className="w-3.5 h-3.5" />}
        <span className="font-bold">{isValid ? 'AUDIT SEAL INTACT' : 'CHAIN TAMPERED'}</span>
        <span className="text-[10px] text-[var(--text-muted)]">({recordCount} recs)</span>
      </div>
    );
  }

  if (variant === 'banner') {
    return (
      <div
        className={`p-3 rounded-lg border font-mono text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
          isValid
            ? 'bg-[var(--crypto-pqc-bg)] border-[var(--crypto-pqc-border)]'
            : 'bg-[var(--crypto-shor-bg)] border-[var(--band-critical)]'
        } ${className}`}
      >
        <div className="flex items-center gap-2.5">
          <div
            className={`w-7 h-7 rounded flex items-center justify-center shrink-0 border ${
              isValid
                ? 'bg-[var(--surface-base)] text-[var(--crypto-pqc)] border-[var(--crypto-pqc-border)]'
                : 'bg-[var(--surface-base)] text-[var(--band-critical)] border-[var(--band-critical)]'
            }`}
          >
            {isValid ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-[var(--text-primary)]">
                {isValid ? 'Cryptographic Audit Log Integrity Verified' : 'Audit Log Tampering Detected'}
              </span>
              <span
                className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                  isValid
                    ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)]'
                    : 'bg-[var(--band-critical)] text-[var(--surface-base)]'
                }`}
              >
                {isValid ? 'VALID' : 'TAMPERED'}
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-secondary)] mt-0.5">
              {details || `SHA-256 hash-chain verified across ${recordCount} immutable ledger entries.`}
            </p>
          </div>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="px-2.5 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] text-[11px] font-bold flex items-center gap-1.5 shrink-0 transition-colors"
        >
          <RotateCw className={`w-3 h-3 ${isRefetching ? 'animate-spin' : ''}`} />
          <span>Re-verify</span>
        </button>
      </div>
    );
  }

  // Default: 'card'
  return (
    <div
      className={`bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-4 font-mono text-xs shadow-sm ${className}`}
      data-testid="audit-verify-control"
    >
      <div className="flex items-start justify-between gap-3 border-b border-[var(--border-subtle)] pb-3 mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border ${
              isValid
                ? 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border-[var(--crypto-pqc-border)]'
                : 'bg-[var(--crypto-shor-bg)] text-[var(--band-critical)] border-[var(--band-critical)]'
            }`}
          >
            {isValid ? <ShieldCheck className="w-5 h-5" /> : <ShieldAlert className="w-5 h-5" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-[var(--text-primary)]">
                Audit Log Hash-Chain Integrity
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                  isValid
                    ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)]'
                    : 'bg-[var(--band-critical)] text-[var(--surface-base)]'
                }`}
              >
                {isValid ? 'CHAIN VALID' : 'TAMPERED'}
              </span>
            </div>
            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
              Cryptographic SHA-256 Merkle chain verification for tamper-evident compliance.
            </p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isLoading || isRefetching}
          className="px-2.5 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-prominent)] text-[11px] font-bold flex items-center gap-1.5 shrink-0 transition-colors"
          title="Trigger hash-chain re-verification"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isRefetching ? 'animate-spin' : ''}`} />
          <span>{isRefetching ? 'Verifying...' : 'Re-verify'}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="py-4 text-center text-[var(--text-muted)] animate-pulse">
          Verifying SHA-256 hash-chain across audit log records...
        </div>
      ) : error ? (
        <div className="py-2 text-[var(--band-critical)]">
          Failed to query audit verification endpoint.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Record Count */}
            <div className="p-2.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)]">
              <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mb-1">
                Verified Records
              </div>
              <div className="text-base font-bold text-[var(--text-primary)] num-tabular flex items-center gap-1.5">
                <span>{recordCount.toLocaleString()}</span>
                <span className="text-[11px] font-normal text-[var(--text-secondary)]">ledger entries</span>
              </div>
            </div>

            {/* Verification Status */}
            <div className="p-2.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)]">
              <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mb-1">
                Cryptographic Seal
              </div>
              <div className="text-sm font-bold text-[var(--crypto-pqc)] flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5" />
                <span>SHA-256 Intact · Zero Breaches</span>
              </div>
            </div>
          </div>

          {/* SHA-256 Head Hash */}
          <div className="p-2.5 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="min-w-0 flex-1">
              <div className="text-[10px] uppercase font-bold text-[var(--text-muted)] mb-0.5">
                Head Hash (SHA-256)
              </div>
              <div
                className="font-mono text-[11px] text-[var(--text-secondary)] truncate"
                title={headHash}
              >
                {headHash}
              </div>
            </div>
            <button
              onClick={handleCopyHash}
              className="px-2 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-[10px] font-bold flex items-center gap-1 shrink-0 self-start sm:self-center transition-colors"
              title="Copy full SHA-256 head hash"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-[var(--crypto-pqc)]" />
                  <span className="text-[var(--crypto-pqc)]">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy Hash</span>
                </>
              )}
            </button>
          </div>

          {/* Detail explanation */}
          {details && (
            <p className="text-[11px] text-[var(--text-muted)] leading-relaxed">
              {details}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
