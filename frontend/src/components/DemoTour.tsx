'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAppStore } from '../lib/store';
import {
  Play,
  Pause,
  ChevronLeft,
  ChevronRight,
  X,
  Sparkles,
  Compass,
  Layers,
  Clock,
  ExternalLink,
  Shield,
  Volume2,
} from 'lucide-react';

interface TourStep {
  id: number;
  screenNumber: number;
  name: string;
  route: string;
  title: string;
  script: string;
  highlights: string[];
  action?: () => void;
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: 1,
    screenNumber: 11,
    name: 'Continuous Estate Console',
    route: '/estate',
    title: 'Autonomous Telemetry & Cryptographic Estate',
    script:
      'ECDAT monitors real-time cryptographic posture across all enterprise targets with a 30s telemetry loop, SoftHSM2 slot partitions, CI/CD precision gates, and SHA-256 audit hash-chain integrity verification.',
    highlights: [
      'Live 30-second telemetry polling across all repo, binary, and endpoint targets',
      'CI/CD precision gates blocking PR merges on critical Shor-vulnerable findings',
      'Tamper-evident SHA-256 Merkle audit log verification seal',
    ],
  },
  {
    id: 2,
    screenNumber: 12,
    name: 'Estate Cryptographic Trend',
    route: '/trend',
    title: 'Dual-Axis Historical Risk & Critical Findings',
    script:
      'Historical trajectory tracking over 7D/30D/90D ranges. Observe how critical Shor-vulnerable findings drop while average risk scores steadily decline as PQC migration takes effect.',
    highlights: [
      'Dual-axis time series with SVG/D3 path generation and interactive tooltips',
      'Synchronized 7D / 30D / 90D telemetry range windows',
      'Comprehensive audit telemetry event log table with deep-links',
    ],
  },
  {
    id: 3,
    screenNumber: 13,
    name: 'Cryptographic Drift Analysis',
    route: '/drift',
    title: 'Two-Snapshot Differential Analysis',
    script:
      'Pinpoint exact cryptographic regressions between scan snapshots. Newly introduced Shor-vulnerable keys are flagged in Ember Red, resolved remediations in Lattice Teal, and configuration alterations in Amber.',
    highlights: [
      'Two-snapshot diff identifying Added, Resolved, and Modified algorithms',
      'Deep-linked drawer inspection for newly introduced threat assets',
      'Automatic regression alerts preventing unapproved legacy cipher regressions',
    ],
  },
  {
    id: 4,
    screenNumber: 14,
    name: 'Security Alerts & Protocol Probes',
    route: '/alerts',
    title: 'Active Downgrade Probes & Live Telemetry',
    script:
      'Signals-intelligence alerts feed detecting cipher suite downgrade regressions in production TLS/SSH endpoints. Compare NEGOTIATED cipher suites with advertised SUPPORTED algorithms.',
    highlights: [
      'Real-time alerts for expiring certs, probe downgrades, and critical findings',
      'Active network probing highlighting NEGOTIATED vs SUPPORTED cipher suites',
      'Interactive alert acknowledgement mutations with optimistic UI updates',
    ],
  },
  {
    id: 5,
    screenNumber: 1,
    name: 'Scan Launcher & Target Ingestion',
    route: '/launcher',
    title: 'Deterministic Target Ingestion',
    script:
      'Dropzone and CLI scanner for compiled ELF/PE binaries, source trees, and container tarballs. Deterministic offline discovery computes CycloneDX 1.6 CBOM and Mosca quantum risk models.',
    highlights: [
      'Drag-and-drop bundle ingestion supporting ZIP, TAR, ELF, PE, and Mach-O',
      'Live stage pipeline progress (Ingestion -> Deep AST -> Mosca Scoring)',
      'CI/CD pipeline trigger configuration with honest roadmap annotations',
    ],
  },
  {
    id: 6,
    screenNumber: 2,
    name: 'Executive Quantum Exposure Overview',
    route: '/overview',
    title: 'Executive Quantum Exposure Dashboard',
    script:
      'High-level quantum vulnerability summary: Critical, High, Medium, Low risk breakdown, Harvest Now Decrypt Later (HNDL) active exposures, and throughput telemetry.',
    highlights: [
      'Executive risk posture breakdown across Critical, High, Medium, and Low bands',
      'HNDL threat tracker isolating high-value encrypted data at risk',
      'Scan throughput metrics and one-click CycloneDX 1.6 CBOM export',
    ],
  },
  {
    id: 7,
    screenNumber: 3,
    name: 'Interactive Mosca Quantum Risk Matrix',
    route: '/mosca',
    title: 'Mosca Quantum Risk Modeling (M = X + Y - Z)',
    script:
      'Interactive scatter plot mapping shelf-life (X) and migration time (Y) against CRQC arrival horizon (Z). Drag the Z slider from 5 to 15 years to observe dynamic quantum urgency recalculation.',
    highlights: [
      'Interactive D3 scatter plot with draggable CRQC arrival horizon slider (Z)',
      'Invariant: Classically broken algorithms (U=1) remain stationary regardless of Z',
      'Live region screen-reader announcements informing analysts of shifted findings',
    ],
  },
  {
    id: 8,
    screenNumber: 4,
    name: 'High-Density Cryptographic Inventory',
    route: '/inventory',
    title: 'High-Density Cryptographic Catalog & SoftHSM2',
    script:
      'Virtualized 60 fps catalog indexing 10,000+ assets with faceted filters, attack surface breakdowns, and real SoftHSM2 PKCS#11 partition slot enumeration.',
    highlights: [
      'Virtualized 60 fps scrolling supporting dense cryptographic inventories',
      'SoftHSM2 PKCS#11 hardware token slot partitions and key enumeration',
      'Direct filter presets: HNDL Threat, Classically Broken, Low Confidence',
    ],
  },
  {
    id: 9,
    screenNumber: 5,
    name: 'Deep-Dive Finding Inspection',
    route: '/inventory',
    title: 'V × F × U × E × K Risk Waterfall & NIST Remediation',
    script:
      'Detailed inspection drawer featuring code snippets, AST symbols, mathematical risk score waterfall, and direct NIST FIPS 203/204 PQC migration targets with byte/latency cost deltas.',
    highlights: [
      'Mathematical risk waterfall: V (Vulnerability) × F (Exposure) × U (Urgency) × E (Effort) × K (Asset Value)',
      'NIST FIPS 203/204 PQC migration target recommendations',
      'Calculated bandwidth and CPU latency deltas for PQC transitions',
    ],
  },
  {
    id: 10,
    screenNumber: 6,
    name: '3D Spatial Estate Topology Graph',
    route: '/graph',
    title: 'WebGL 3D Spatial Topology Engine',
    script:
      'Interactive Three.js 3D force-directed graph visualizing relationships from Systems to Files to Cryptographic Assets with real-time risk bloom shaders.',
    highlights: [
      'Hardware-accelerated Three.js WebGL force-directed spatial graph',
      'Dynamic bloom shaders color-coded by cryptographic semantic classes',
      'Instant 2D HTML5 canvas fallback for low-spec or headless environments',
    ],
  },
  {
    id: 11,
    screenNumber: 7,
    name: 'Surface × Family Exposure Heatmap',
    route: '/heatmap',
    title: 'Attack Surface Cross-Correlation Matrix',
    script:
      'Two-dimensional matrix correlating attack surfaces (Source AST, Binary Embedded, Network TLS, Hardware HSM) with cryptographic families to highlight concentrated exposures.',
    highlights: [
      'Cross-correlation matrix isolating critical cluster vulnerabilities',
      'Interactive cell inspection filtering inventory to matching assets',
      'Visual heat gradient utilizing accessible OKLCH color mappings',
    ],
  },
  {
    id: 12,
    screenNumber: 8,
    name: 'X.509 Certificate Validity Horizon',
    route: '/certificates',
    title: 'Public-Key Certificate Lifetimes',
    script:
      'Timeline analysis auditing X.509 certificate validity lifetimes against CRQC arrival, flagging certificates whose expiration extends beyond quantum decryption horizons.',
    highlights: [
      'Certificate expiration timelines plotted against projected CRQC arrival (Z)',
      'Automated flagging of SHA-1 and RSA-1024 legacy certificates in production',
      'Issuer CA trust chain audit and certificate inventory table',
    ],
  },
  {
    id: 13,
    screenNumber: 9,
    name: 'Post-Quantum Migration Roadmap',
    route: '/plan',
    title: 'Prioritized Remediations & CBOM Export',
    script:
      'Phase-by-phase migration sequence prioritizing critical HNDL assets, providing exact FIPS 203/204 drop-in replacements, wire byte deltas, and downloadable remediation plans.',
    highlights: [
      'Automated phased remediation scheduling based on Mosca quantum risk scores',
      'Per-phase network bandwidth and compute overhead impact estimates',
      'Downloadable remediation action plans in JSON format',
    ],
  },
  {
    id: 14,
    screenNumber: 10,
    name: 'Cryptographic Governance Policy Editor',
    route: '/policies',
    title: 'Cryptographic Policy Rules & Glob Overrides',
    script:
      'Enterprise governance policy definition allowing path-glob overrides, strict PQC enforcement rules, and automated CI/CD precision gate thresholds.',
    highlights: [
      'Custom path-glob contextual policy overrides with live finding matches',
      'Policy templates: Defense-in-Depth, Strict CNSA 2.0 PQC, and Legacy Audit',
      'Precision gate thresholds directly integrated with automated CI/CD workflows',
    ],
  },
];

export function DemoTour() {
  const router = useRouter();
  const pathname = usePathname();
  const { openDrawer } = useAppStore();

  const [isOpen, setIsOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [countdown, setCountdown] = useState(30);

  const currentStep = TOUR_STEPS[currentStepIndex];

  // Navigate to step route
  const goToStep = useCallback(
    (index: number) => {
      const targetIndex = Math.max(0, Math.min(index, TOUR_STEPS.length - 1));
      setCurrentStepIndex(targetIndex);
      setCountdown(30);

      const step = TOUR_STEPS[targetIndex];
      if (step.route && pathname !== step.route) {
        router.push(step.route);
      }

      // If step 9 (FindingDrawer inspection), open drawer
      if (step.id === 9) {
        setTimeout(() => {
          openDrawer({
            id: 'f-004',
            displayName: 'RSA-2048 key generation',
            family: 'RSA',
            surface: 'source',
            kind: 'algorithm',
            keySize: 2048,
            mode: null,
            curve: null,
            function: 'keygen',
            snippet: 'KeyPairGenerator gen = KeyPairGenerator.getInstance("RSA"); gen.initialize(2048);',
            source: 'ast',
            confidence: 0.95,
            location: {
              path: 'src/main/java/com/example/auth/KeyService.java',
              line: 42,
              offset: null,
              layer: null,
            },
            symbol: 'KeyPairGenerator.generateKeyPair',
            negotiated: false,
            triage: {
              status: 'open',
            },
            risk: {
              score: 76.95,
              band: 'critical',
              V: 1,
              F: 0.9,
              U: 1,
              E: 0.95,
              K: 0.9,
              X: 12,
              Y: 8,
              Z: 10,
              moscaMargin: 10,
              reason: 'Shor-vulnerable asymmetric keygen on an externally-exposed path; shelf life exceeds CRQC horizon.',
              classicallyBroken: false,
              hndl: true,
              needsReview: false,
            },
            recommendation: {
              action: 'Migrate to ML-KEM-768 for quantum-safe key encapsulation',
              target: 'ML-KEM-768',
              cost: {
                pkBytesDelta: 928,
                wireBytesDelta: 832,
                opMsDelta: 0.05,
              },
            },
          });
        }, 300);
      }
    },
    [router, pathname, openDrawer]
  );

  const nextStep = useCallback(() => {
    if (currentStepIndex < TOUR_STEPS.length - 1) {
      goToStep(currentStepIndex + 1);
    } else {
      setIsPlaying(false);
    }
  }, [currentStepIndex, goToStep]);

  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      goToStep(currentStepIndex - 1);
    }
  }, [currentStepIndex, goToStep]);

  // Auto-play timer
  useEffect(() => {
    if (!isPlaying || !isOpen) return;

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          nextStep();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [isPlaying, isOpen, nextStep]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
        setIsPlaying(false);
      } else if (e.key === ']') {
        nextStep();
      } else if (e.key === '[') {
        prevStep();
      } else if (e.key === ' ' && (e.target as HTMLElement).tagName !== 'INPUT') {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, nextStep, prevStep]);

  return (
    <>
      {/* Launch Trigger Button in Header / Navigation */}
      <button
        onClick={() => {
          setIsOpen(true);
          goToStep(currentStepIndex);
        }}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] hover:bg-[var(--crypto-pqc)] hover:text-[var(--surface-base)] text-xs font-mono font-bold transition-all shadow-sm"
        title="Start 7-Minute Guided Demo Tour across all 14 screens"
        aria-label="Start 7-Minute Guided Demo Tour"
      >
        <Sparkles className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">7-Min Demo Tour</span>
        <span className="sm:hidden">Tour</span>
      </button>

      {/* Floating Guided Tour Controller */}
      {isOpen && (
        <aside
          aria-label="7-Minute Guided Demo Tour Controller"
          className="fixed bottom-6 left-6 z-50 w-full max-w-md bg-[var(--surface-overlay)] border border-[var(--crypto-pqc-border)] rounded-2xl shadow-2xl backdrop-blur-xl p-4 font-mono text-xs animate-in fade-in slide-in-from-bottom-4 duration-200 select-none"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5 mb-3">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)] flex items-center justify-center">
                <Compass className="w-3.5 h-3.5" />
              </div>
              <div>
                <span className="text-[10px] uppercase font-bold text-[var(--crypto-pqc)] tracking-wider">
                  7-Minute Guided Demo Tour
                </span>
                <div className="font-bold text-[var(--text-primary)] text-xs">
                  Step {currentStepIndex + 1} of {TOUR_STEPS.length} · Screen {currentStep.screenNumber}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Auto-Play Toggle */}
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`px-2 py-1 rounded text-[10px] font-bold flex items-center gap-1 border transition-colors ${
                  isPlaying
                    ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] border-[var(--crypto-pqc)]'
                    : 'bg-[var(--surface-raised)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
                title={isPlaying ? 'Pause auto-play (Space)' : 'Start auto-play (Space)'}
              >
                {isPlaying ? <Pause className="w-3 h-3 fill-current" /> : <Play className="w-3 h-3 fill-current" />}
                <span>{isPlaying ? `${countdown}s` : 'Auto'}</span>
              </button>

              {/* Close Tour */}
              <button
                onClick={() => {
                  setIsOpen(false);
                  setIsPlaying(false);
                }}
                className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-colors"
                aria-label="Close tour controller"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Step Narrative & Script */}
          <div className="space-y-2.5 mb-3">
            <div>
              <h3 className="font-bold text-sm text-[var(--text-primary)]">
                {currentStep.title}
              </h3>
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed mt-1">
                {currentStep.script}
              </p>
            </div>

            {/* Talking Points / Highlights */}
            <div className="p-2.5 rounded-lg bg-[var(--surface-base)] border border-[var(--border-subtle)] space-y-1">
              <span className="text-[9px] uppercase font-bold text-[var(--text-muted)] flex items-center gap-1">
                <Volume2 className="w-3 h-3 text-[var(--crypto-pqc)]" />
                <span>Key Presentation Evidence:</span>
              </span>
              <ul className="list-disc list-inside text-[10px] text-[var(--text-primary)] space-y-0.5">
                {currentStep.highlights.map((h, i) => (
                  <li key={i} className="leading-tight">
                    {h}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--border-subtle)]">
            {/* Quick jump selector */}
            <select
              value={currentStepIndex}
              onChange={(e) => goToStep(Number(e.target.value))}
              aria-label="Jump to tour step"
              className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-[10px] text-[var(--text-secondary)] focus:outline-none"
            >
              {TOUR_STEPS.map((s, idx) => (
                <option key={s.id} value={idx}>
                  #{s.id}: Screen {s.screenNumber} ({s.name})
                </option>
              ))}
            </select>

            <div className="flex items-center gap-1.5">
              <button
                onClick={prevStep}
                disabled={currentStepIndex === 0}
                className="px-2 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-40 text-[10px] font-bold flex items-center gap-0.5"
                title="Previous step (Hotkey: [)"
              >
                <ChevronLeft className="w-3 h-3" />
                <span>Prev</span>
              </button>

              <button
                onClick={nextStep}
                disabled={currentStepIndex === TOUR_STEPS.length - 1}
                className="px-2.5 py-1 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] hover:opacity-90 disabled:opacity-40 text-[10px] font-bold flex items-center gap-0.5 shadow-sm"
                title="Next step (Hotkey: ])"
              >
                <span>Next</span>
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </aside>
      )}
    </>
  );
}
