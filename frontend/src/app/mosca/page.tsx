'use client';

import { useState, useMemo } from 'react';
import { useAppStore } from '../../lib/store';
import { mockFindings } from '../../mocks/data';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { classifyAlgorithm, type Finding, type RiskBand } from '../../types/crypto';
import {
  Calculator,
  Sliders,
  AlertTriangle,
  ShieldAlert,
  ArrowRight,
  Info,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

export default function MoscaMatrixPage() {
  const { crqcZ, setCrqcZ, openDrawer } = useAppStore();
  const [hoveredFinding, setHoveredFinding] = useState<Finding | null>(null);

  // Re-scoring computation across findings
  const { currentFindings, changedFindings, bands } = useMemo(() => {
    const changed: Array<{
      finding: Finding;
      oldBand: RiskBand;
      newBand: RiskBand;
      oldScore: number;
      newScore: number;
    }> = [];

    const bandCounts = { critical: 0, high: 0, medium: 0, low: 0 };

    const computed = mockFindings.map((f) => {
      const oldScore = f.risk.score;
      const oldBand = f.risk.band;

      let u = f.risk.U;
      let score = oldScore;
      let band: RiskBand = oldBand;
      const margin = f.risk.X + f.risk.Y - crqcZ;

      if (!f.risk.classicallyBroken) {
        // Quantum-sensitive: recalculate U
        const rawU = 0.5 + margin / (2 * crqcZ);
        u = Math.max(0.05, Math.min(1.0, rawU));
        score = Math.round(100 * f.risk.V * f.risk.F * u * f.risk.E * f.risk.K * 10) / 10;
        if (score >= 60) band = 'critical';
        else if (score >= 35) band = 'high';
        else if (score >= 15) band = 'medium';
        else band = 'low';
      } else {
        // Classically broken invariant: U = 1.0!
        u = 1.0;
        score = oldScore;
        band = oldBand;
      }

      bandCounts[band]++;

      if (band !== oldBand || Math.abs(score - oldScore) > 0.5) {
        changed.push({
          finding: f,
          oldBand,
          newBand: band,
          oldScore,
          newScore: score,
        });
      }

      return {
        ...f,
        calculatedU: u,
        calculatedScore: score,
        calculatedBand: band,
        calculatedMargin: margin,
      };
    });

    return { currentFindings: computed, changedFindings: changed, bands: bandCounts };
  }, [crqcZ]);

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

  return (
    <div className="space-y-6 font-mono">
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
                    x={padding.left - 8}
                    y={yScale(score) + 4}
                    fill="var(--text-muted)"
                    fontSize="10"
                    textAnchor="end"
                    fontFamily="monospace"
                  >
                    {score}
                  </text>
                </g>
              ))}

              {[5, 10, 15, 20, 25, 30].map((years) => (
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
                    y={height - padding.bottom + 16}
                    fill="var(--text-muted)"
                    fontSize="10"
                    textAnchor="middle"
                    fontFamily="monospace"
                  >
                    {years}y
                  </text>
                </g>
              ))}

              {/* Threat Threshold Backgrounds */}
              <rect
                x={padding.left}
                y={yScale(100)}
                width={chartWidth}
                height={yScale(60) - yScale(100)}
                fill="oklch(0.64 0.23 25 / 0.05)"
              />
              <line
                x1={padding.left}
                y1={yScale(60)}
                x2={width - padding.right}
                y2={yScale(60)}
                stroke="var(--band-critical)"
                strokeWidth="1"
                strokeDasharray="4,4"
              />
              <text
                x={width - padding.right - 6}
                y={yScale(60) - 6}
                fill="var(--band-critical)"
                fontSize="9"
                textAnchor="end"
                fontFamily="monospace"
              >
                CRITICAL THRESHOLD (Score ≥ 60)
              </text>

              {/* Vertical Draggable CRQC Horizon Line (Z) */}
              <line
                x1={xScale(crqcZ)}
                y1={padding.top}
                x2={xScale(crqcZ)}
                y2={height - padding.bottom}
                stroke="var(--crypto-pqc)"
                strokeWidth="2.5"
                strokeDasharray="6,3"
              />
              <polygon
                points={`${xScale(crqcZ) - 5},${padding.top} ${xScale(crqcZ) + 5},${padding.top} ${xScale(crqcZ)},${padding.top + 8}`}
                fill="var(--crypto-pqc)"
              />
              <text
                x={xScale(crqcZ)}
                y={padding.top - 8}
                fill="var(--crypto-pqc)"
                fontSize="11"
                fontWeight="bold"
                textAnchor="middle"
                fontFamily="monospace"
              >
                CRQC HORIZON: Z = {crqcZ}y
              </text>

              {/* Threat Zone Shading (X + Y > Z) */}
              <rect
                x={xScale(crqcZ)}
                y={padding.top}
                width={width - padding.right - xScale(crqcZ)}
                height={chartHeight}
                fill="oklch(0.64 0.23 25 / 0.07)"
              />

              {/* Scatter Points */}
              {currentFindings.map((f) => {
                const totalYears = f.risk.X + f.risk.Y;
                const cx = xScale(Math.min(maxXandY, totalYears));
                const cy = yScale(f.calculatedScore);
                const cls = classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken);

                let fillColor = 'var(--crypto-shor)';
                if (cls === 'classically-broken') fillColor = 'var(--crypto-broken)';
                else if (cls === 'pqc') fillColor = 'var(--crypto-pqc)';
                else if (cls === 'grover') fillColor = 'var(--crypto-grover)';
                else if (cls === 'quantum-safe-classical') fillColor = 'var(--crypto-safe-classical)';

                const isHovered = hoveredFinding?.id === f.id;

                return (
                  <g
                    key={f.id}
                    className="cursor-pointer transition-all duration-300"
                    onMouseEnter={() => setHoveredFinding(f)}
                    onMouseLeave={() => setHoveredFinding(null)}
                    onClick={() => openDrawer(f)}
                  >
                    <circle
                      cx={cx}
                      cy={cy}
                      r={isHovered ? 8 : 6}
                      fill={fillColor}
                      stroke="var(--surface-base)"
                      strokeWidth="2"
                      className={cls === 'classically-broken' ? 'hatch-broken' : ''}
                    />
                    {isHovered && (
                      <circle
                        cx={cx}
                        cy={cy}
                        r={12}
                        fill="none"
                        stroke={fillColor}
                        strokeWidth="1.5"
                        strokeDasharray="2,2"
                        className="animate-spin"
                      />
                    )}
                    <text
                      x={cx}
                      y={cy - 9}
                      fill="var(--text-primary)"
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      {f.displayName}
                    </text>
                  </g>
                );
              })}

              {/* Axis Titles */}
              <text
                x={width / 2}
                y={height - 10}
                fill="var(--text-secondary)"
                fontSize="11"
                textAnchor="middle"
                fontFamily="monospace"
              >
                Data Lifetime + Migration Time (X + Y in Years) →
              </text>
              <text
                x={-height / 2}
                y={18}
                transform="rotate(-90)"
                fill="var(--text-secondary)"
                fontSize="11"
                textAnchor="middle"
                fontFamily="monospace"
              >
                ← Quantum Threat Score (0 - 100)
              </text>
            </svg>
          </div>

          <div className="text-[11px] text-[var(--text-muted)] mt-2 flex items-center justify-between">
            <span>Click any node to open finding drawer and review full cryptographic parameters.</span>
            <span>Right of Z line = Critical quantum exposure ($X + Y &gt; Z$).</span>
          </div>
        </div>

        {/* Right Col: Side List of Findings That Changed Band */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
              <span className="font-bold text-xs text-[var(--text-primary)] uppercase flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                <span>Scenario Horizon Shifts</span>
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-raised)] text-[var(--crypto-grover)] font-bold">
                Z = {crqcZ} yrs
              </span>
            </div>

            <p className="text-[11px] text-[var(--text-secondary)]">
              When Z shifts, Mosca Urgency U = clamp(0.5 + M/(2Z), 0.05, 1) re-calculates for public key algorithms (RSA, ECC, DH).
              Classically broken algorithms visibly <strong className="text-[var(--crypto-broken)]">remain fixed at U = 1</strong>.
            </p>

            <div className="space-y-2 pt-1 max-h-72 overflow-y-auto">
              {changedFindings.length === 0 ? (
                <div className="p-4 text-center text-xs text-[var(--text-muted)] border border-dashed border-[var(--border-subtle)] rounded">
                  No band transitions at current horizon ($Z = {crqcZ}$). Drag slider to observe sensitivity shifts.
                </div>
              ) : (
                changedFindings.map(({ finding, oldBand, newBand, oldScore, newScore }) => (
                  <div
                    key={finding.id}
                    onClick={() => openDrawer(finding)}
                    className="p-2.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--border-focus)] cursor-pointer text-xs space-y-1.5 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[var(--text-primary)]">{finding.displayName}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">{finding.location.path}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px]">
                      <div className="flex items-center gap-1.5">
                        <RiskBandBadge band={oldBand} score={oldScore} showScore={false} />
                        <ArrowRight className="w-3 h-3 text-[var(--text-muted)]" />
                        <RiskBandBadge band={newBand} score={newScore} showScore={false} />
                      </div>
                      <span className="font-bold num-tabular text-[var(--text-primary)]">
                        {oldScore.toFixed(0)} → {newScore.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Active Band Distribution */}
          <div className="bg-[var(--surface-raised)] border border-[var(--border-subtle)] p-3 rounded-lg space-y-1.5 text-xs pt-3">
            <div className="text-[10px] uppercase font-bold text-[var(--text-muted)]">
              Current Band Counts at Z={crqcZ}y
            </div>
            <div className="grid grid-cols-4 gap-1 text-center font-bold">
              <div className="bg-[var(--surface-card)] p-1.5 rounded border border-[var(--border-subtle)] text-[var(--band-critical)]">
                <div className="text-[9px] text-[var(--text-muted)]">CRIT</div>
                <div>{bands.critical}</div>
              </div>
              <div className="bg-[var(--surface-card)] p-1.5 rounded border border-[var(--border-subtle)] text-[var(--band-high)]">
                <div className="text-[9px] text-[var(--text-muted)]">HIGH</div>
                <div>{bands.high}</div>
              </div>
              <div className="bg-[var(--surface-card)] p-1.5 rounded border border-[var(--border-subtle)] text-[var(--band-medium)]">
                <div className="text-[9px] text-[var(--text-muted)]">MED</div>
                <div>{bands.medium}</div>
              </div>
              <div className="bg-[var(--surface-card)] p-1.5 rounded border border-[var(--border-subtle)] text-[var(--band-low)]">
                <div className="text-[9px] text-[var(--text-muted)]">LOW</div>
                <div>{bands.low}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
