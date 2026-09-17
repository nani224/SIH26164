'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../lib/store';
import {
  Upload,
  FileArchive,
  Cpu,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Play,
  Terminal,
  Clock,
  Sparkles,
  ArrowRight,
  Shield,
  FileCheck,
} from 'lucide-react';

export default function ScanLauncherPage() {
  const router = useRouter();
  const { crqcZ, setCrqcZ, setActiveScanId } = useAppStore();

  const [selectedFile, setSelectedFile] = useState<{ name: string; size: number; hash: string } | null>({
    name: 'ntro-core-infrastructure-snapshot.tar.gz',
    size: 28450190,
    hash: '8f92a31d4e7b6c501192e4ab912cd3ef681b4029415c48b78990e1f721ab3091',
  });
  const [targetPath, setTargetPath] = useState('/opt/ntro/deployments/core-mesh');
  const [selectedPolicy, setSelectedPolicy] = useState('policy-default-defense');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStage, setScanStage] = useState<'idle' | 'ingesting' | 'scanning' | 'scoring' | 'done'>('idle');
  const [counters, setCounters] = useState({ files: 0, bytes: 0, findings: 0 });

  const startScan = () => {
    setIsScanning(true);
    setScanStage('ingesting');
    setCounters({ files: 0, bytes: 0, findings: 0 });

    // Stage 1: Ingesting
    setTimeout(() => {
      setCounters({ files: 450, bytes: 9200000, findings: 2 });
      setScanStage('scanning');

      // Stage 2: Scanning (AST + Binary)
      setTimeout(() => {
        setCounters({ files: 1420, bytes: 28450190, findings: 8 });
        setScanStage('scoring');

        // Stage 3: Scoring (Mosca Quantum Framework)
        setTimeout(() => {
          setScanStage('done');
          setIsScanning(false);
          setActiveScanId('scan-7f8e1a');
        }, 1200);
      }, 1500);
    }, 1200);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-4 font-mono">
      {/* Header */}
      <div className="border-b border-[var(--border-subtle)] pb-4">
        <div className="flex items-center gap-2 text-[var(--crypto-pqc)] text-xs mb-1">
          <Terminal className="w-3.5 h-3.5" />
          <span>SCREEN 1 · CRYPTOGRAPHIC SCAN LAUNCHER</span>
        </div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          Target Ingestion & Assessment Setup
        </h1>
        <p className="text-xs text-[var(--text-secondary)] mt-1">
          Scan source repositories, compiled ELF/PE binaries, libraries, and container images.
          Deterministic offline discovery outputs CycloneDX 1.6 CBOM and Mosca quantum risk models.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Ingestion Dropzone & Parameters */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dropzone */}
          <div className="bg-[var(--surface-card)] border border-[var(--border-prominent)] rounded-xl p-6 text-center relative hover:border-[var(--border-focus)] transition-colors">
            <input
              type="file"
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  setSelectedFile({
                    name: file.name,
                    size: file.size,
                    hash: '9f81a7b3c2e5d4a106e23b18cd76a543210efab7612c890123456789abcdef01',
                  });
                }
              }}
            />
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] flex items-center justify-center text-[var(--crypto-pqc)]">
                <Upload className="w-6 h-6" />
              </div>
              <div>
                <div className="text-sm font-bold text-[var(--text-primary)]">
                  Drag and drop bundle archive or binary target
                </div>
                <div className="text-xs text-[var(--text-muted)] mt-1">
                  Supports .zip, .tar, .tar.gz, ELF, PE, Mach-O, container image tarballs
                </div>
              </div>
            </div>
          </div>

          {/* Selected File / Local Path preview */}
          {selectedFile && (
            <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[var(--text-primary)] font-semibold">
                  <FileArchive className="w-4 h-4 text-[var(--crypto-pqc)]" />
                  <span>{selectedFile.name}</span>
                </div>
                <span className="text-[var(--text-muted)] num-tabular">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </span>
              </div>
              <div className="text-[11px] text-[var(--text-muted)] break-all">
                SHA-256 Bundle Hash:{' '}
                <span className="text-[var(--text-secondary)] font-mono">{selectedFile.hash}</span>
              </div>
            </div>
          )}

          {/* Policy & Mosca Scenario Configuration */}
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-5 rounded-lg space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-2">
              <Sliders className="w-4 h-4 text-[var(--crypto-grover)]" />
              <span>Assessment Parameters</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="text-[var(--text-muted)] block mb-1">
                  Evaluation Policy:
                </label>
                <select
                  value={selectedPolicy}
                  onChange={(e) => setSelectedPolicy(e.target.value)}
                  className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
                >
                  <option value="policy-default-defense">National Defense Core (Default CNSA 2.0)</option>
                  <option value="policy-telecom-critical">Telecom Mission Critical (5G / Core Gateway)</option>
                  <option value="policy-internal-test">Internal R&D Testbed (Relaxed)</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-[var(--text-muted)]">CRQC Horizon (Z):</label>
                  <span className="font-bold text-[var(--crypto-grover)] num-tabular">
                    {crqcZ} YEARS
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="15"
                  step="1"
                  value={crqcZ}
                  onChange={(e) => setCrqcZ(Number(e.target.value))}
                  className="w-full accent-[var(--crypto-pqc)] cursor-pointer mt-1"
                />
                <div className="flex justify-between text-[9px] text-[var(--text-muted)]">
                  <span>5y (Hostile)</span>
                  <span>10y (Standard)</span>
                  <span>15y (Long-term)</span>
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={startScan}
                disabled={isScanning}
                className="w-full py-2.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold text-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                {isScanning ? (
                  <>
                    <span className="w-4 h-4 border-2 border-[var(--surface-base)] border-t-transparent rounded-full animate-spin" />
                    <span>EXECUTING DISCOVERY PIPELINE...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>START ENTERPRISE SCAN</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Col: Real-time Live Event Timeline */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
            <span className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[var(--crypto-pqc)]" />
              <span>Live Stage Timeline</span>
            </span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-muted)]">
              WS /events
            </span>
          </div>

          <div className="space-y-4 text-xs">
            {/* Stage 1: Ingestion */}
            <div className="flex items-start gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] mt-0.5 ${
                scanStage === 'ingesting'
                  ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] animate-pulse'
                  : scanStage === 'scanning' || scanStage === 'scoring' || scanStage === 'done'
                  ? 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]'
                  : 'bg-[var(--surface-raised)] text-[var(--text-muted)]'
              }`}>
                {scanStage === 'scanning' || scanStage === 'scoring' || scanStage === 'done' ? '✓' : '1'}
              </div>
              <div>
                <div className="font-semibold text-[var(--text-primary)]">Target Ingestion</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  Prefilter ELF, PE, certificates & unpack archive
                </div>
              </div>
            </div>

            {/* Stage 2: Scanning */}
            <div className="flex items-start gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] mt-0.5 ${
                scanStage === 'scanning'
                  ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] animate-pulse'
                  : scanStage === 'scoring' || scanStage === 'done'
                  ? 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]'
                  : 'bg-[var(--surface-raised)] text-[var(--text-muted)]'
              }`}>
                {scanStage === 'scoring' || scanStage === 'done' ? '✓' : '2'}
              </div>
              <div>
                <div className="font-semibold text-[var(--text-primary)]">Deep AST & Binary Scan</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  Tree-sitter AST queries, pyelftools symbol disasm
                </div>
              </div>
            </div>

            {/* Stage 3: Scoring */}
            <div className="flex items-start gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] mt-0.5 ${
                scanStage === 'scoring'
                  ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] animate-pulse'
                  : scanStage === 'done'
                  ? 'bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]'
                  : 'bg-[var(--surface-raised)] text-[var(--text-muted)]'
              }`}>
                {scanStage === 'done' ? '✓' : '3'}
              </div>
              <div>
                <div className="font-semibold text-[var(--text-primary)]">Mosca Quantum Scoring</div>
                <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  Compute M = X + Y - Z and map PQC recommendations
                </div>
              </div>
            </div>
          </div>

          {/* Real Counter Display */}
          <div className="bg-[var(--surface-base)] border border-[var(--border-subtle)] p-3 rounded space-y-1.5 text-[11px] pt-3">
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Analyzed Files:</span>
              <span className="text-[var(--text-primary)] font-bold num-tabular">{counters.files}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Data Ingested:</span>
              <span className="text-[var(--text-primary)] font-bold num-tabular">
                {(counters.bytes / 1024 / 1024).toFixed(1)} MB
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Discovered Findings:</span>
              <span className="text-[var(--crypto-shor)] font-bold num-tabular">{counters.findings}</span>
            </div>
          </div>

          {/* Scan Completion Action */}
          {scanStage === 'done' && (
            <div className="pt-2">
              <button
                onClick={() => router.push('/overview')}
                className="w-full py-2 rounded bg-[var(--crypto-safe-classical)] text-white font-bold text-xs flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
              >
                <span>OPEN SCAN OVERVIEW CONSOLE</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
