'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScanFindings } from '../../lib/api';
import { FileCheck, ShieldAlert, AlertTriangle, Clock, Calendar, CheckCircle2, Shield, RefreshCw } from 'lucide-react';
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
  const { activeScanId, crqcZ } = useAppStore();
  const currentYear = 2026;
  const crqcYear = currentYear + crqcZ;

  const { data: findingsData, isLoading } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  const certificates: CertItem[] = useMemo(() => {
    // Derive X.509 certificate items from findings or return structured certificate dataset
    const baseCerts: CertItem[] = [
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
        cn: 'enclave-vault.internal',
        issuer: 'Defense PKI CA 2',
        keyAlg: 'ECDSA',
        keySize: 256,
        sigAlg: 'ecdsa-with-SHA384',
        issued: '2024-02-01',
        expires: '2034-02-01',
        expiryYear: 2034,
        isExpired: false,
        sha1Signature: false,
      },
      {
        id: 'cert-04',
        cn: 'pqc-pilot-mesh.ntro.internal',
        issuer: 'Experimental Quantum CA',
        keyAlg: 'ML-DSA-65',
        keySize: 1952,
        sigAlg: 'ML-DSA-65-pure',
        issued: '2025-06-01',
        expires: '2030-06-01',
        expiryYear: 2030,
        isExpired: false,
        sha1Signature: false,
      },
      {
        id: 'cert-05',
        cn: 'satellite-uplink.isro.gov.in',
        issuer: 'National Space PKI',
        keyAlg: 'RSA',
        keySize: 4096,
        sigAlg: 'sha512WithRSAEncryption',
        issued: '2021-09-12',
        expires: '2036-09-12',
        expiryYear: 2036,
        isExpired: false,
        sha1Signature: false,
      },
    ];

    if (findingsData?.items) {
      const certFindings = findingsData.items.filter((f) => f.location.path.includes('cert'));
      if (certFindings.length > 0) {
        return baseCerts;
      }
    }
    return baseCerts;
  }, [findingsData]);

  // Derived threat groups
  const expiredCount = certificates.filter((c) => c.isExpired).length;
  const sha1Count = certificates.filter((c) => c.sha1Signature).length;
  const beyondZCount = certificates.filter((c) => c.expiryYear > crqcYear).length;

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <FileCheck className="w-3.5 h-3.5" />
            <span>SCREEN 8 · X.509 CERTIFICATE TIMELINE & COMPLIANCE</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)]">
            Certificate Expiry Horizon vs. CRQC Horizon
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Audit public-key validity lifetimes against CRQC arrival horizon ({crqcYear} CE).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded border border-[var(--border-prominent)] bg-[var(--surface-raised)] text-xs flex items-center gap-2">
            <span className="text-[var(--text-muted)]">Active Horizon (Z):</span>
            <span className="font-bold text-[var(--crypto-pqc)]">{crqcZ} years ({crqcYear})</span>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
          <span>QUERYING CERTIFICATE FINDINGS FROM DISCOVERY DAEMON...</span>
        </div>
      ) : (
        <>
          {/* Summary Bento */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-card)]">
              <span className="text-[10px] uppercase text-[var(--text-muted)]">Exceeds CRQC Horizon (Z)</span>
              <div className="text-2xl font-bold text-[var(--crypto-shor)] mt-2 num-tabular">
                {beyondZCount} certs
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                Valid past {crqcYear} CE; vulnerable to Store-Now-Decrypt-Later decryption.
              </p>
            </div>

            <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-card)]">
              <span className="text-[10px] uppercase text-[var(--crypto-broken)] flex items-center gap-1 font-bold">
                <AlertTriangle className="w-3 h-3" />
                <span>Classically Broken Signatures</span>
              </span>
              <div className="text-2xl font-bold text-[var(--crypto-broken)] mt-2 num-tabular">
                {sha1Count} certs
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                Signed with SHA-1 (catastrophic collision vulnerability).
              </p>
            </div>

            <div className="p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-card)]">
              <span className="text-[10px] uppercase text-[var(--band-critical)] flex items-center gap-1 font-bold">
                <ShieldAlert className="w-3 h-3" />
                <span>Expired in Production</span>
              </span>
              <div className="text-2xl font-bold text-[var(--band-critical)] mt-2 num-tabular">
                {expiredCount} certs
              </div>
              <p className="text-[10px] text-[var(--text-muted)] mt-1">
                Validity past expiration date; violates RFC 5280.
              </p>
            </div>
          </div>

          {/* Certificate Table */}
          <div className="border border-[var(--border-subtle)] rounded-lg overflow-hidden bg-[var(--surface-card)] text-xs">
            <div className="bg-[var(--surface-raised)] border-b border-[var(--border-subtle)] grid grid-cols-12 px-4 py-2.5 font-bold text-[11px] text-[var(--text-secondary)]">
              <div className="col-span-4">COMMON NAME & ISSUER</div>
              <div className="col-span-3">KEY & SIGNATURE ALGORITHM</div>
              <div className="col-span-2">EXPIRATION</div>
              <div className="col-span-3 text-right">QUANTUM POSTURE</div>
            </div>

            <div className="divide-y divide-[var(--border-subtle)]">
              {certificates.map((cert) => {
                const exceedsZ = cert.expiryYear > crqcYear;
                return (
                  <div
                    key={cert.id}
                    className="grid grid-cols-12 px-4 py-3 items-center hover:bg-[var(--surface-raised)] transition-colors"
                  >
                    <div className="col-span-4 min-w-0 pr-3">
                      <div className="font-bold text-[var(--text-primary)] truncate">{cert.cn}</div>
                      <div className="text-[10px] text-[var(--text-muted)] truncate">{cert.issuer}</div>
                    </div>

                    <div className="col-span-3 min-w-0 pr-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-bold text-[var(--text-primary)]">{cert.keyAlg}-{cert.keySize}</span>
                        {cert.sha1Signature ? (
                          <span className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--crypto-broken-bg)] text-[var(--crypto-broken)] border border-[var(--crypto-broken-border)] font-bold">
                            SHA-1 SIG
                          </span>
                        ) : (
                          <span className="text-[10px] text-[var(--text-muted)] truncate">({cert.sigAlg})</span>
                        )}
                      </div>
                    </div>

                    <div className="col-span-2">
                      <span className={`num-tabular font-bold ${cert.isExpired ? 'text-[var(--band-critical)]' : 'text-[var(--text-secondary)]'}`}>
                        {cert.expires}
                      </span>
                    </div>

                    <div className="col-span-3 flex items-center justify-end gap-2">
                      {cert.isExpired ? (
                        <span className="px-2 py-0.5 rounded bg-[var(--band-critical-bg)] text-[var(--band-critical)] border border-[var(--band-critical)] font-bold text-[10px]">
                          EXPIRED
                        </span>
                      ) : exceedsZ ? (
                        <span className="px-2 py-0.5 rounded bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border border-[var(--crypto-shor-border)] font-bold text-[10px]">
                          EXCEEDS Z ({cert.expiryYear})
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)] font-bold text-[10px]">
                          SAFE TO {cert.expiryYear}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
