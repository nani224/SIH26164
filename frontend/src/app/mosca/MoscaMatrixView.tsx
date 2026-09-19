'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { rescoreScan, type RescoreResult } from '../../lib/api';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { classifyAlgorithm, type Finding, type RiskBand, type RiskBands } from '../../types/crypto';
import {
  Calculator,
  Sliders,
  RefreshCw,
  Layers,
  ArrowRight,
  AlertCircle,
  FolderOpen,
} from 'lucide-react';

export interface MoscaMatrixViewProps {
  findings: Finding[];
  initialZ?: number;
  scanId?: string;
  error?: string | null;
  onFindingSelect?: (finding: Finding) => void;
  onZRescore?: (z: number) => Promise<RescoreResult>;
}

export function MoscaMatrixView({
  findings,
  initialZ = 10,
  scanId = 'scan-7f8e1a',
  error = null,
  onFindingSelect,
  onZRescore,
}: MoscaMatrixViewProps) {
  const [crqcZ, setCrqcZ] = useState<number>(initialZ);
  const [hoveredFinding, setHoveredFinding] = useState<Finding | null>(null);

  // risk is nullable per contract (an unscored finding); this matrix plots
  // by risk score/band, so unscored findings have nothing to plot.
  const scoredFindings = useMemo(
    () => findings.filter((f): f is Finding & { risk: NonNullable<Finding['risk']> } => f.risk != null),
    [findings]
  );

  // Server-driven re-scoring state (ZERO local formula calculation)
  const [serverBands, setServerBands] = useState<RiskBands | null>(null);
  const [changedFindingsList, setChangedFindingsList] = useState<
    Array<{
      id: string;
      displayName: string;
      previousBand: RiskBand;
      newBand: RiskBand;
      previousScore: number;
      newScore: number;
    }>
  >([]);

  // Mutation to call real POST /api/v1/scans/{id}/rescore endpoint
  const rescoreMutation = useMutation({
    mutationFn: async (z: number) => {
      if (onZRescore) {
        return onZRescore(z);
      }
      return rescoreScan(scanId, { crqcYears: z });
    },
    onSuccess: (data) => {
      setServerBands(data.bands);
      // `data.changed` (contract shape) only carries the NEW state. The
      // `findings` prop is the pre-rescore snapshot (fetched once, not
      // re-fetched on rescore), so it's the source of the "previous" side
      // of the diff -- never derive both sides from the same response.
      const previousById = new Map(scoredFindings.map((f) => [f.id, f]));
      setChangedFindingsList(
        data.changed
          .filter((f): f is Finding & { risk: NonNullable<Finding['risk']> } => f.risk != null)
          .map((f) => {
            const previous = previousById.get(f.id);
            return {
              id: f.id,
              displayName: f.displayName,
              previousBand: previous?.risk.band ?? f.risk.band,
              newBand: f.risk.band,
              previousScore: previous?.risk.score ?? f.risk.score,
              newScore: f.risk.score,
            };
          })
      );
    },
  });

  const lastTriggeredZ = useRef<number>(initialZ);
  useEffect(() => {
    if (crqcZ !== lastTriggeredZ.current) {
      lastTriggeredZ.current = crqcZ;
      rescoreMutation.mutate(crqcZ);
    }
  }, [crqcZ, rescoreMutation]);

  // Map server-returned changed scores onto current findings for plotting
  const currentFindings = useMemo(() => {
    const changeMap = new Map(changedFindingsList.map((c) => [c.id, c]));

    return scoredFindings.map((f) => {
      const change = changeMap.get(f.id);
      const score = change ? change.newScore : f.risk.score;
      const band = change ? change.newBand : f.risk.band;

      return {
        ...f,
        calculatedScore: score,
        calculatedBand: band,
      };
    });
  }, [scoredFindings, changedFindingsList]);

  // Derive band counts from server response or fallback to findings
  const bands = useMemo(() => {
    if (serverBands) return serverBands;
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    scoredFindings.forEach((f) => counts[f.risk.band]++);
    return counts;
  }, [scoredFindings, serverBands]);

  // Matrix dimensions for SVG scatter plot
  const width = 800;
  const height = 450;
  const padding = { top: 30, right: 40, bottom: 50, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const maxXandY = 30; // 0 to 30 years
  const maxScore = 100;

  const xScale = (val: number) => padding.left + (val / maxXandY) * chartWidth;
  const yScale = (val: number) => padding.top + (1 - val / maxScore) * chartHeight;

  // Handle Error State
  if (error) {
    return (
      <div className="p-8 bg-[var(--surface-card)] border border-[var(--crypto-broken-border)] rounded-xl text-center space-y-3 font-mono">
        <AlertCircle className="w-8 h-8 text-[var(--crypto-broken)] mx-auto" />
        <h2 className="text-sm font-bold text-[var(--crypto-broken)] uppercase">
          Failed to Load Cryptographic Posture Telemetry
        </h2>
        <p className="text-xs text-[var(--text-muted)] max-w-md mx-auto">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] hover:border-[var(--border-focus)]"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Handle Empty State
  if (findings.length === 0) {
    return (
      <div className="p-12 bg-[var(--surface-card)] border border-dashed border-[var(--border-subtle)] rounded-xl text-center space-y-3 font-mono">
        <FolderOpen className="w-8 h-8 text-[var(--text-muted)] mx-auto" />
        <h2 className="text-sm font-bold text-[var(--text-primary)]">
          No Cryptographic Assets Discovered in Active Scan
        </h2>
        <p className="text-xs text-[var(--text-muted)] max-w-md mx-auto">
          The scanner completed successfully without detecting public-key, symmetric, or hash primitives matching current policy rules.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Screen reader live region for scenario horizon announcements */}
      <div className="sr-only" aria-live="polite">
        CRQC horizon updated to {crqcZ} years. {changedFindingsList.length} cryptographic assets shifted risk bands based on live server re-score.
      </div>

      {/* Header briefing */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Calculator className="w-3.5 h-3.5" />
            <span>SCREEN 3 · SIGNATURE MOSCA QUANTUM RISK MATRIX</span>
          </div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Mosca Horizon Assessment ($X + Y &gt; Z$)
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-0.5 max-w-3xl">
            Where $X$ = Data Shelf Life, $Y$ = Migration Time, $Z$ = Years to CRQC.
            Points to the right of the vertical $Z$ line represent cryptographic assets that will be compromised by quantum adversaries before migration completes.
            Classically-broken assets remain fixed at U = 1.
          </p>
        </div>

        {/* Live Z Horizon Slider Control */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-prominent)] p-3 rounded-lg flex items-center gap-4">
          <Sliders className="w-4 h-4 text-[var(--crypto-grover)] flex-shrink-0" />
          <div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-muted)]">CRQC Horizon (Z):</span>
              <span className="font-bold text-[var(--crypto-grover)] num-tabular text-sm ml-2">
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
              className="w-48 accent-[var(--crypto-pqc)] cursor-pointer mt-1"
              aria-label="CRQC Horizon in years"
              aria-valuemin={5}
              aria-valuemax={15}
              aria-valuenow={crqcZ}
            />
            <div className="flex justify-between text-[9px] text-[var(--text-muted)]">
              <span>5 yrs (Hostile)</span>
              <span>10 yrs (NIST)</span>
              <span>15 yrs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Screen Layout: 2D Scientific Matrix + Re-banded Findings Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: D3/SVG Scientific Scatter Matrix */}
        <div className="lg:col-span-2 bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs mb-2">
            <span className="font-bold text-[var(--text-primary)] uppercase flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              <span>Interactive Scatter Plot: Exposure (X+Y) vs Threat Score</span>
            </span>
            <div className="flex items-center gap-2 text-[10px] text-[var(--text-muted)]">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-shor)] inline-block" /> Shor
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-broken)] inline-block hatch-broken" /> Broken
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-pqc)] inline-block" /> PQC
              </span>
            </div>
          </div>

          {/* SVG Plot */}
          <div className="w-full overflow-x-auto bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded-lg p-2">
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto select-none">
              {/* Grid Lines */}
              {[0, 20, 40, 60, 80, 100].map((score) => (
                <g key={`y-grid-${score}`}>
                  <line
                    x1={padding.left}
                    y1={yScale(score)}
                    x2={width - padding.right}
                    y2={yScale(score)}
                    stroke="var(--border-subtle)"
                    strokeDasharray="2,4"
                  />
                  <text
                    x={padding.left - 10}
                    y={yScale(score) + 4}
                    textAnchor="end"
                    fontSize="10"
                    fill="var(--text-muted)"
                    className="font-mono"
                  >
                    {score}
                  </text>
                </g>
              ))}

              {[0, 5, 10, 15, 20, 25, 30].map((years) => (
                <g key={`x-grid-${years}`}>
                  <line
                    x1={xScale(years)}
                    y1={padding.top}
                    x2={xScale(years)}
                    y2={height - padding.bottom}
                    stroke="var(--border-subtle)"
                    strokeDasharray="2,4"
                  />
                  <text
                    x={xScale(years)}
                    y={height - padding.bottom + 18}
                    textAnchor="middle"
                    fontSize="10"
                    fill="var(--text-muted)"
                    className="font-mono"
                  >
                    {years}y
                  </text>
                </g>
              ))}

              {/* Critical Risk Zone Shading (Y >= 60) */}
              <rect
                x={padding.left}
                y={padding.top}
                width={chartWidth}
                height={yScale(60) - padding.top}
                fill="var(--band-critical-bg)"
                opacity="0.3"
              />

              {/* Quantum Jeopardy Zone Shading (X+Y > Z) */}
              <rect
                x={xScale(crqcZ)}
                y={padding.top}
                width={chartWidth - (xScale(crqcZ) - padding.left)}
                height={chartHeight}
                fill="var(--crypto-shor-bg)"
                opacity="0.15"
              />

              {/* Vertical Draggable CRQC Horizon Line (Z) */}
              <g className="cursor-ew-resize">
                <line
                  x1={xScale(crqcZ)}
                  y1={padding.top}
                  x2={xScale(crqcZ)}
                  y2={height - padding.bottom}
                  stroke="var(--crypto-pqc)"
                  strokeWidth="2.5"
                  strokeDasharray="4,4"
                />
                <text
                  x={xScale(crqcZ)}
                  y={padding.top - 10}
                  textAnchor="middle"
                  fill="var(--crypto-pqc)"
                  fontSize="11"
                  fontWeight="bold"
                  className="font-mono"
                >
                  CRQC HORIZON: Z = {crqcZ}y
                </text>
              </g>

              {/* Scatter Points */}
              {currentFindings.map((f) => {
                const totalExposure = f.risk.X + f.risk.Y;
                const cx = xScale(totalExposure);
                const cy = yScale(f.calculatedScore);
                const cryptoClass = classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken);
                const isHovered = hoveredFinding?.id === f.id;

                let fill = 'var(--crypto-shor)';
                if (cryptoClass === 'classically-broken') fill = 'var(--crypto-broken)';
                else if (cryptoClass === 'pqc') fill = 'var(--crypto-pqc)';
                else if (cryptoClass === 'grover') fill = 'var(--crypto-grover)';
                else if (cryptoClass === 'quantum-safe-classical') fill = 'var(--crypto-safe-classical)';

                return (
                  <g
                    key={f.id}
                    data-testid={`scatter-node-${f.id}`}
                    tabIndex={0}
                    role="button"
                    aria-label={`${f.displayName} at ${f.location.path}, score ${f.calculatedScore}, band ${f.calculatedBand}`}
                    onMouseEnter={() => setHoveredFinding(f)}
                    onMouseLeave={() => setHoveredFinding(null)}
                    onFocus={() => setHoveredFinding(f)}
                    onBlur={() => setHoveredFinding(null)}
                    onClick={() => onFindingSelect?.(f)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onFindingSelect?.(f);
                      }
                    }}
                    className="cursor-pointer transition-all duration-300 focus:outline-none"
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={isHovered ? 8 : f.calculatedScore >= 60 ? 6 : 4.5}
                      fill={fill}
                      stroke={
                        isHovered
                          ? 'var(--text-primary)'
                          : f.risk.needsReview
                          ? 'var(--band-medium)'
                          : 'var(--surface-base)'
                      }
                      strokeWidth={isHovered ? 2.5 : f.risk.needsReview ? 1.5 : 1}
                      strokeDasharray={f.risk.needsReview ? '2,2' : undefined}
                      className={
                        f.calculatedScore >= 60
                          ? 'filter drop-shadow-[0_0_6px_var(--band-critical)]'
                          : ''
                      }
                    />
                    {findings.length <= 50 && (
                      <text
                        x={cx + 8}
                        y={cy + 3}
                        fontSize="9"
                        fill="var(--text-muted)"
                        className="pointer-events-none font-mono select-none"
                      >
                        {f.displayName}
                      </text>
                    )}
                    {isHovered && (
                      <text
                        x={cx}
                        y={cy - 12}
                        textAnchor="middle"
                        fontSize="10"
                        fill="var(--text-primary)"
                        fontWeight="bold"
                        className="pointer-events-none font-mono"
                      >
                        {f.displayName} ({f.calculatedScore})
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Axis Titles */}
              <text
                x={width / 2}
                y={height - 12}
                textAnchor="middle"
                fontSize="11"
                fill="var(--text-secondary)"
                className="font-mono font-bold"
              >
                Mosca Exposure: X + Y (Years: Shelf Life + Migration Time)
              </text>
              <text
                x={-height / 2}
                y={18}
                transform="rotate(-90)"
                textAnchor="middle"
                fontSize="11"
                fill="var(--text-secondary)"
                className="font-mono font-bold"
              >
                Computed Risk Score (0–100)
              </text>
            </svg>
          </div>

          {/* Bottom Invariant Rule Reminder */}
          <div className="mt-3 flex items-center justify-between text-[11px] text-[var(--text-muted)] bg-[var(--surface-base)] border border-[var(--border-subtle)] p-2.5 rounded-lg">
            <span>
              <strong>Domain Invariant:</strong> Classically broken assets (MD5, SHA-1, DES, RC4) remain fixed at $U = 1.0$ and never change score when $Z$ is moved.
            </span>
            <span className="text-[var(--crypto-pqc)] font-bold">
              {rescoreMutation.isPending ? 'RE-SCORING VIA API...' : 'SERVER SYNCHRONIZED'}
            </span>
          </div>
        </div>

        {/* Right 1 Col: Dynamic Findings Affected by Z-Movement */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3 mb-3">
              <span className="font-bold text-[var(--text-primary)] uppercase flex items-center gap-1.5">
                <RefreshCw
                  className={`w-3.5 h-3.5 text-[var(--crypto-pqc)] ${
                    rescoreMutation.isPending ? 'animate-spin' : ''
                  }`}
                />
                <span>Scenario Horizon Shifts</span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)] num-tabular">
                {changedFindingsList.length} Affected
              </span>
            </div>

            <p className="text-[11px] text-[var(--text-muted)] mb-3">
              Findings where Mosca urgency ($U$) recalculation altered risk scores under $Z = {crqcZ}$y scenario horizon (via live POST /rescore).
            </p>

            {/* List of Affected Assets */}
            <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
              {changedFindingsList.length === 0 ? (
                <div className="p-6 text-center text-[var(--text-muted)] border border-dashed border-[var(--border-subtle)] rounded-lg">
                  No findings changed risk bands at baseline horizon $Z = {crqcZ}$y.
                </div>
              ) : (
                changedFindingsList.map((item) => (
                  <div
                    key={item.id}
                    className="p-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-base)] hover:border-[var(--border-prominent)] transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[var(--text-primary)]">{item.displayName}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">ID: {item.id}</span>
                    </div>
                    <div className="flex items-center justify-between mt-2 pt-1 border-t border-[var(--border-subtle)] text-[10px]">
                      <div className="flex items-center gap-1.5">
                        <RiskBandBadge band={item.previousBand} size="sm" />
                        <ArrowRight className="w-3 h-3 text-[var(--text-muted)]" />
                        <RiskBandBadge band={item.newBand} size="sm" />
                      </div>
                      <div className="num-tabular font-bold text-[var(--text-primary)]">
                        {item.previousScore.toFixed(1)} → {item.newScore.toFixed(1)}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Band Distribution Metric Counter */}
          <div className="border-t border-[var(--border-subtle)] pt-3 mt-4">
            <span className="text-[10px] uppercase text-[var(--text-muted)] font-bold block mb-2">
              Current Posture Distribution (Z = {crqcZ}y)
            </span>
            <div className="grid grid-cols-4 gap-2 text-center text-[10px]">
              <div className="p-1.5 rounded bg-[var(--surface-raised)] border border-[var(--band-critical)]/30">
                <span className="text-[var(--band-critical)] font-bold num-tabular text-xs">
                  {bands.critical}
                </span>
                <span className="block text-[var(--text-muted)] mt-0.5">Critical</span>
              </div>
              <div className="p-1.5 rounded bg-[var(--surface-raised)] border border-[var(--band-high)]/30">
                <span className="text-[var(--band-high)] font-bold num-tabular text-xs">
                  {bands.high}
                </span>
                <span className="block text-[var(--text-muted)] mt-0.5">High</span>
              </div>
              <div className="p-1.5 rounded bg-[var(--surface-raised)] border border-[var(--band-medium)]/30">
                <span className="text-[var(--band-medium)] font-bold num-tabular text-xs">
                  {bands.medium}
                </span>
                <span className="block text-[var(--text-muted)] mt-0.5">Med</span>
              </div>
              <div className="p-1.5 rounded bg-[var(--surface-raised)] border border-[var(--band-low)]/30">
                <span className="text-[var(--band-low)] font-bold num-tabular text-xs">
                  {bands.low}
                </span>
                <span className="block text-[var(--text-muted)] mt-0.5">Low</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
