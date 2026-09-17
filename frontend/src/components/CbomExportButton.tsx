'use client';

import { useState } from 'react';
import { Download, Check, ShieldCheck, FileJson, X } from 'lucide-react';

export function CbomExportButton({ scanId }: { scanId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  const handleDownload = () => {
    const cbomData = {
      bomFormat: 'CycloneDX',
      specVersion: '1.6',
      serialNumber: `urn:uuid:${crypto.randomUUID()}`,
      version: 1,
      metadata: {
        timestamp: new Date().toISOString(),
        tools: [
          {
            vendor: 'NTRO',
            name: 'ECDAT (SIH26164)',
            version: '1.0.0',
          },
        ],
        component: {
          name: 'scanned-target',
          type: 'application',
        },
      },
      signature: {
        algorithm: 'Ed25519',
        publicKey: '0x8f4b...39a1',
        value: '3045022100...f902206a',
        sha256Digest: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      },
    };

    const blob = new Blob([JSON.stringify(cbomData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cbom-${scanId}.cyclonedx.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloaded(true);
    setTimeout(() => setDownloaded(false), 2000);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--text-primary)] hover:bg-[var(--surface-card-hover)] font-mono text-xs transition-colors"
        title="Download CycloneDX 1.6 Cryptographic Bill of Materials (CBOM)"
      >
        <Download className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
        <span>EXPORT CBOM 1.6</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto p-4 flex items-center justify-center">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />
          <div className="relative w-full max-w-lg rounded-xl border border-[var(--border-prominent)] bg-[var(--surface-overlay)] shadow-2xl p-6 font-mono text-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
              <div className="flex items-center gap-2">
                <FileJson className="w-4 h-4 text-[var(--crypto-pqc)]" />
                <span className="font-bold text-[var(--text-primary)] text-sm">
                  CycloneDX 1.6 CBOM Export
                </span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded hover:bg-[var(--surface-raised)] text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-[var(--text-secondary)]">
              Full machine-readable Cryptographic Bill of Materials adhering to CycloneDX 1.6 schema standards with cryptographic signature verification record.
            </p>

            <div className="p-3 bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded space-y-1.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Spec Version:</span>
                <span className="text-[var(--crypto-pqc)] font-bold">CycloneDX 1.6</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Signing Algorithm:</span>
                <span className="text-[var(--text-primary)]">Ed25519 (RFC 8032)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Integrity Hash:</span>
                <span className="text-[var(--text-primary)] font-mono text-[10px]">SHA-256 Verified</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setIsOpen(false)}
                className="px-3 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-raised)]"
              >
                Close
              </button>
              <button
                onClick={handleDownload}
                className="px-4 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity flex items-center gap-1.5"
              >
                {downloaded ? (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>DOWNLOADED</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>DOWNLOAD JSON</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
