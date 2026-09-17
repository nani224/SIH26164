'use client';

import { useMemo } from 'react';
import { useAppStore } from '../../lib/store';
import { FileCheck, ShieldAlert, AlertTriangle, Clock, Calendar, CheckCircle2, Shield } from 'lucide-react';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';

interface CertItem {
  id: string;
  cn: string;
  issuer: string;
  keyAlg: string;
  keySize: number;
  sigAlg: string;
  issued: string;
  expires: string;
  expiryYear: number;
  isExpired: boolean;
  sha1Signature: boolean;
}

export default function CertificatesPage() {
  const { crqcZ } = useAppStore();
  const currentYear = 2026;
  const crqcYear = currentYear + crqcZ;

  const certificates: CertItem[] = [
    {
      id: 'cert-01',
      cn: 'gateway.core.ntro.internal',
      issuer: 'NTRO Root CA 2018',
      keyAlg: 'RSA',
      keySize: 2048,
      sigAlg: 'sha256WithRSAEncryption',
      issued: '2023-01-15',
      expires: '2028-01-15',
      expiryYear: 2028,
      isExpired: false,
      sha1Signature: false,
    },
    {
      id: 'cert-02',
      cn: 'legacy-vpn.telecom.gov.in',
      issuer: 'NIC Sub-CA',
      keyAlg: 'RSA',
      keySize: 1024,
      sigAlg: 'sha1WithRSAEncryption',
      issued: '2019-04-10',
      expires: '2024-04-10',
      expiryYear: 2024,
      isExpired: true,
      sha1Signature: true,
    },
    {
      id: 'cert-03',
      cn: 'mesh-broker.internal',
      issuer: 'Defense Internal Subordinate CA',
      keyAlg: 'ECDSA',
      keySize: 256,
      sigAlg: 'ecdsa-with-SHA384',
      issued: '2024-08-01',
      expires: '2034-08-01',
      expiryYear: 2034,
      isExpired: false,
      sha1Signature: false,
    },
    {
      id: 'cert-04',
      cn: 'storage-vault.secure.internal',
      issuer: 'NTRO Master CA G2',
      keyAlg: 'RSA',
      keySize: 4096,
      sigAlg: 'sha384WithRSAEncryption',
      issued: '2022-11-20',
      expires: '2038-11-20',
      expiryYear: 2038,
      isExpired: false,
      sha1Signature: false,
    },
    {
      id: 'cert-05',
      cn: 'pqc-pilot-gateway.ntro.gov.in',
      issuer: 'PQC Testbed CA (FIPS 204)',
      keyAlg: 'ML-DSA',
      keySize: 65,
      sigAlg: 'id-ml-dsa-65',
      issued: '2026-02-01',
      expires: '2036-02-01',
      expiryYear: 2036,
      isExpired: false,
      sha1Signature: false,
    },
  ];

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <FileCheck className="w-3.5 h-3.5" />
            <span>SCREEN 8 · X.509 CERTIFICATE EXPIRY & QUANTUM HORIZON</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Certificate Lifetime Timeline vs CRQC Horizon
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Evaluates public key validity outlasting CRQC Horizon ($Z = {crqcZ}$ yrs → Year {crqcYear}). Expired certificates and SHA-1 signatures flagged.
          </p>
        </div>
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] px-3 py-2 rounded text-right">
          <div className="text-[10px] text-[var(--text-muted)]">CRQC Quantum Deadline</div>
          <div className="text-base font-bold text-[var(--crypto-pqc)] num-tabular">Year {crqcYear}</div>
        </div>
      </div>

      {/* Timeline Visual Cards */}
      <div className="space-y-4">
        {certificates.map((cert) => {
          const outlastsQuantum = cert.expiryYear >= crqcYear && cert.keyAlg !== 'ML-DSA';

          return (
            <div
              key={cert.id}
              className={`p-4 rounded-xl border transition-all bg-[var(--surface-card)] ${
                cert.isExpired
                  ? 'border-[var(--crypto-broken-border)] bg-[var(--crypto-broken-bg)]'
                  : outlastsQuantum
                  ? 'border-[var(--crypto-shor-border)] bg-[var(--crypto-shor-bg)]/20'
                  : 'border-[var(--border-subtle)]'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                {/* Cert Details */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-[var(--text-primary)]">{cert.cn}</span>
                    {cert.isExpired && (
                      <span className="px-1.5 py-0.2 rounded bg-[var(--crypto-broken)] text-[var(--surface-base)] text-[9px] font-bold">
                        EXPIRED
                      </span>
                    )}
                    {cert.sha1Signature && (
                      <span className="px-1.5 py-0.2 rounded bg-[var(--crypto-broken)] text-[var(--surface-base)] text-[9px] font-bold hatch-broken">
                        SHA-1 SIGNATURE
                      </span>
                    )}
                    {outlastsQuantum && (
                      <span className="px-1.5 py-0.2 rounded bg-[var(--band-critical)] text-[var(--surface-base)] text-[9px] font-bold animate-pulse">
                        VALID PAST CRQC HORIZON ({crqcYear})
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    Issuer: {cert.issuer} · Signature: {cert.sigAlg}
                  </div>
                </div>

                {/* Key Specification */}
                <div className="flex items-center gap-3 text-right">
                  <div>
                    <div className="text-[10px] text-[var(--text-muted)] uppercase">Key Specification</div>
                    <div className="font-bold text-xs text-[var(--text-primary)]">
                      {cert.keyAlg}-{cert.keySize}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[var(--text-muted)] uppercase">Expiry Date</div>
                    <div className="font-bold text-xs num-tabular text-[var(--text-primary)]">
                      {cert.expires} ({cert.expiryYear})
                    </div>
                  </div>
                </div>
              </div>

              {/* Graphical Timeline Bar */}
              <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex items-center gap-3">
                <span className="text-[10px] text-[var(--text-muted)] w-12">2026</span>
                <div className="flex-1 bg-[var(--surface-raised)] h-2 rounded-full relative overflow-hidden">
                  {/* Validity span */}
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(10, ((cert.expiryYear - 2026) / 16) * 100))}%`,
                    }}
                    className={`h-full rounded-full ${
                      cert.isExpired
                        ? 'bg-[var(--crypto-broken)]'
                        : outlastsQuantum
                        ? 'bg-[var(--crypto-shor)]'
                        : 'bg-[var(--crypto-pqc)]'
                    }`}
                  />
                  {/* CRQC line marker */}
                  <div
                    style={{
                      left: `${((crqcYear - 2026) / 16) * 100}%`,
                    }}
                    className="absolute top-0 bottom-0 w-0.5 bg-[var(--crypto-grover)] z-10"
                    title={`CRQC Horizon (${crqcYear})`}
                  />
                </div>
                <span className="text-[10px] text-[var(--crypto-grover)] font-bold w-20 text-right">
                  Z: {crqcYear}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
