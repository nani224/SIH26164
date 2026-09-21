'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  Compass,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  ShieldAlert,
  Calendar,
  GitPullRequest,
  TrendingDown,
  Layers,
  Sparkles,
  Lock,
  Award,
} from 'lucide-react';

interface DemoTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAttestation?: () => void;
  onOpenBenchmark?: () => void;
}

interface TourStep {
  title: string;
  badge: string;
  icon: typeof Compass;
  targetRoute?: string;
  actionName?: string;
  actionHandler?: 'attestation' | 'benchmark';
  description: string;
  keyTakeaway: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    title: '1. Blocked PR via CI Precision Gate',
    badge: 'CI / CD Gate',
    icon: GitPullRequest,
    targetRoute: '/alerts',
    description:
      'A developer introduces a cryptographic usage that fails the 0.95 precision floor or introduces unexplainable cryptographic residue. The CI pipeline fails automatically with an exit code 1, protecting the repository before merge.',
    keyTakeaway:
      'ECDAT enforces mathematical floors at the pull request boundary, not just post-deployment.',
  },
  {
    title: '2. Unprompted Scheduled Scan',
    badge: 'Automation',
    icon: Calendar,
    targetRoute: '/launcher',
    description:
      'The daemon scheduler fires on cron across all registered targets, refreshing cryptographic inventories, certificates, and residue debt ledgers without requiring human intervention.',
    keyTakeaway:
      'Continuous discovery eliminates the blind spots of quarterly manual audits.',
  },
  {
    title: '3. Drift Analysis with Coverage Drop',
    badge: 'Cryptographic Drift',
    icon: TrendingDown,
    targetRoute: '/drift',
    description:
      'A new release is deployed, causing cryptographic coverage to drop by -4.2%. The Drift screen immediately highlights the drop and lists the exact new residue clusters responsible.',
    keyTakeaway:
      'Coverage drops are tracked with the same visual urgency as critical vulnerability findings.',
  },
  {
    title: '4. Residue Explorer & Byte-Level Inspection',
    badge: 'Residue Explorer',
    icon: Layers,
    targetRoute: '/residue',
    description:
      'Drill down into Screen 16: Residue Explorer. View the exact byte range (e.g. bytes 412–448), AST node, firing extractor signals (constant_pool, entropy_spike), and raw source code preview.',
    keyTakeaway:
      'No competitor explains what they could NOT understand. ECDAT exposes residue down to the exact source line.',
  },
  {
    title: '5. Debt Workflow: Promote to Rule',
    badge: 'Engine Scaffolding',
    icon: Sparkles,
    targetRoute: '/residue',
    description:
      'From the residue cluster, click "Promote to Rule". The engine automatically generates an AST rule scaffold with pattern matchers and metadata, ready for engine inclusion.',
    keyTakeaway:
      'Unexplained residue is converted into codified detection rules in seconds.',
  },
  {
    title: '6. Coverage Certificate Rises',
    badge: 'Mass Conservation',
    icon: CheckCircle2,
    targetRoute: '/overview',
    description:
      'With the new rule in place, active scan coverage rises back to 96.4%. The mass conservation bar reflects the shift from residue mass to attributed mass.',
    keyTakeaway:
      'Every byte of cryptographic evidence is conserved: Attributed + Excluded + Residue = Total Evidence.',
  },
  {
    title: '7. Cryptographic Attestation & Evidence Proof',
    badge: 'CBOM 1.6 Integrity',
    icon: Lock,
    actionName: 'View Attestation Proof',
    actionHandler: 'attestation',
    description:
      'The Coverage Certificate is cryptographically signed with Ed25519 into the CycloneDX 1.6 CBOM digest. Verify the cryptographic proof with a single click.',
    keyTakeaway:
      'Attestation guarantees to regulators and auditors that zero unexplained crypto was hidden.',
  },
  {
    title: '8. Public Benchmark & Honest Gaps',
    badge: 'Empirical Proof',
    icon: Award,
    actionName: 'View Public Benchmark',
    actionHandler: 'benchmark',
    description:
      'Inspect real-world precision (95.8%), recall (82.1%), and mean coverage across 5 languages. We honestly document C/C++ dynamic string resolution weaknesses rather than hallucinating.',
    keyTakeaway:
      'Zero hallucinations: ECDAT prefers an honest residue report over fake 100% recall claims.',
  },
];

export function DemoTourModal({
  isOpen,
  onClose,
  onOpenAttestation,
  onOpenBenchmark,
}: DemoTourModalProps) {
  const router = useRouter();
  const [currentStepIdx, setCurrentStepIdx] = useState(0);

  if (!isOpen) return null;

  const currentStep = TOUR_STEPS[currentStepIdx];
  const Icon = currentStep.icon;
  const isFirst = currentStepIdx === 0;
  const isLast = currentStepIdx === TOUR_STEPS.length - 1;

  const handleAction = () => {
    if (currentStep.targetRoute) {
      router.push(currentStep.targetRoute);
      onClose();
    } else if (currentStep.actionHandler === 'attestation') {
      onClose();
      onOpenAttestation?.();
    } else if (currentStep.actionHandler === 'benchmark') {
      onClose();
      onOpenBenchmark?.();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="ECDAT Product Tour"
      className="fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-12 flex items-center justify-center font-mono text-xs"
    >
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/75 backdrop-blur-sm" onClick={onClose} />

      {/* Modal Container */}
      <div className="relative w-full max-w-2xl bg-[var(--surface-base)] border border-[var(--border-prominent)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-[var(--crypto-pqc-bg)] border border-[var(--crypto-pqc-border)] text-[var(--crypto-pqc)]">
              <Compass className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-[var(--text-primary)]">
                  ECDAT v1.0 Guided Product Tour
                </h2>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
                  Step {currentStepIdx + 1} of {TOUR_STEPS.length}
                </span>
              </div>
              <p className="text-[11px] text-[var(--text-muted)]">
                The Complete 7-Minute Story: Blocked PR to Verified Attestation (NTRO SIH26164)
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
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {/* Progress bar */}
          <div className="w-full bg-[var(--surface-card)] h-1.5 rounded-full overflow-hidden border border-[var(--border-subtle)]">
            <div
              className="h-full bg-gradient-to-r from-[var(--crypto-pqc)] to-[var(--coverage-attributed)] transition-all duration-300"
              style={{ width: `${((currentStepIdx + 1) / TOUR_STEPS.length) * 100}%` }}
            />
          </div>

          {/* Current Step Card */}
          <div className="p-5 rounded-lg bg-[var(--surface-card)] border border-[var(--border-subtle)] space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--crypto-pqc)]">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase text-[var(--crypto-shor)]">
                    {currentStep.badge}
                  </span>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">
                    {currentStep.title}
                  </h3>
                </div>
              </div>
            </div>

            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
              {currentStep.description}
            </p>

            <div className="p-3 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-primary)] space-y-1">
              <div className="font-bold text-[var(--crypto-pqc)] text-[10px] uppercase">
                Key Strategic Takeaway
              </div>
              <p className="italic text-[var(--text-secondary)]">{currentStep.keyTakeaway}</p>
            </div>
          </div>

          {/* Direct Route / Action Jump */}
          {(currentStep.targetRoute || currentStep.actionName) && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)]">
              <span className="text-[11px] text-[var(--text-muted)]">
                {currentStep.targetRoute
                  ? `Navigate directly to ${currentStep.targetRoute}`
                  : 'Open interactive proof panel'}
              </span>
              <button
                id="tour-jump-action-btn"
                onClick={handleAction}
                className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity flex items-center gap-1.5"
              >
                <span>{currentStep.actionName ?? `Go to ${currentStep.targetRoute}`}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={() => setCurrentStepIdx((prev) => Math.max(0, prev - 1))}
              disabled={isFirst}
              className="px-3.5 py-1.5 rounded border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--surface-raised)] disabled:opacity-40 transition-colors flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Previous</span>
            </button>

            <div className="flex items-center gap-1.5">
              {TOUR_STEPS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentStepIdx(i)}
                  aria-label={`Go to step ${i + 1}`}
                  className={`w-2 h-2 rounded-full transition-all ${
                    i === currentStepIdx
                      ? 'w-6 bg-[var(--crypto-pqc)]'
                      : 'bg-[var(--border-prominent)] hover:bg-[var(--text-muted)]'
                  }`}
                />
              ))}
            </div>

            {isLast ? (
              <button
                onClick={onClose}
                className="px-4 py-1.5 rounded bg-[var(--coverage-attributed)] text-[var(--surface-base)] font-bold hover:opacity-90 transition-opacity"
              >
                Finish Tour
              </button>
            ) : (
              <button
                id="tour-next-btn"
                onClick={() => setCurrentStepIdx((prev) => Math.min(TOUR_STEPS.length - 1, prev + 1))}
                className="px-3.5 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] text-[var(--text-primary)] font-bold hover:bg-[var(--surface-card-hover)] transition-colors flex items-center gap-1.5"
              >
                <span>Next</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
