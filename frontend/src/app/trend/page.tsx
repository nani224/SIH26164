'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { fetchEstateTrend } from '../../lib/api';
import type { EstateTrendPoint } from '../../types/crypto';
import {
  TrendingDown,
  TrendingUp,
  Activity,
  Calendar,
  AlertTriangle,
  Shield,
  Layers,
  Clock,
  Sparkles,
  ArrowDownRight,
  ArrowUpRight,
  Filter,
} from 'lucide-react';

export default function TrendPage() {
  const [selectedDays, setSelectedDays] = useState<number>(30);
  const [hoveredPoint, setHoveredPoint] = useState<EstateTrendPoint | null>(null);

  const {
    data: trendData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['estateTrend', selectedDays],
    queryFn: () => fetchEstateTrend(selectedDays),
    refetchInterval: 60000,
  });

  const points = useMemo(() => trendData?.points ?? [], [trendData]);

  // Derive metrics
  const firstPoint = points[0];
  const lastPoint = points[points.length - 1];

  const riskDelta = useMemo(() => {
    if (!firstPoint || !lastPoint) return 0;
    return Number((lastPoint.avgRiskScore - firstPoint.avgRiskScore).toFixed(1));
  }, [firstPoint, lastPoint]);

  const criticalDelta = useMemo(() => {
    if (!firstPoint || !lastPoint) return 0;
    return lastPoint.criticalCount - firstPoint.criticalCount;
  }, [firstPoint, lastPoint]);

  const findingsDelta = useMemo(() => {
    if (!firstPoint || !lastPoint) return 0;
    return lastPoint.totalFindings - firstPoint.totalFindings;
  }, [firstPoint, lastPoint]);

  // Projected zero-critical date (linear extrapolation)
  const projectionText = useMemo(() => {
    if (!firstPoint || !lastPoint || criticalDelta >= 0) return 'Linear Extrapolation: Inactive';
    const dailyRate = Math.abs(criticalDelta) / Math.max(points.length - 1, 1);
    if (dailyRate === 0) return 'Stable';
    const daysToZero = Math.ceil(lastPoint.criticalCount / dailyRate);
    const projDate = new Date();
    projDate.setDate(projDate.getDate() + daysToZero);
    return `Projected Zero-Critical: ${projDate.toLocaleDateString(undefined, {
      month: 'short',
      year: 'numeric',
    })} (~${daysToZero}d)`;
  }, [firstPoint, lastPoint, criticalDelta, points.length]);

  // SVG Chart dimensions
  const chartWidth = 900;
  const chartHeight = 260;
  const padding = { top: 20, right: 30, bottom: 35, left: 45 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  // Chart scales
  const maxRisk = 100;
  const minRisk = 0;

  const pointsWithCoords = useMemo(() => {
    if (points.length === 0) return [];
    return points.map((p, idx) => {
      const x = padding.left + (idx / Math.max(points.length - 1, 1)) * innerWidth;
      const yRisk = padding.top + innerHeight - (p.avgRiskScore / maxRisk) * innerHeight;
      const maxCrit = Math.max(...points.map((pt) => pt.criticalCount), 10);
      const yCrit = padding.top + innerHeight - (p.criticalCount / maxCrit) * innerHeight;
      return { ...p, x, yRisk, yCrit };
    });
  }, [points, innerWidth, innerHeight, padding.left, padding.top]);

  // Generate SVG paths
  const riskLinePath = useMemo(() => {
    if (pointsWithCoords.length === 0) return '';
    return pointsWithCoords.reduce((acc, p, idx) => {
      return `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.yRisk.toFixed(1)}`;
    }, '');
  }, [pointsWithCoords]);

  const riskAreaPath = useMemo(() => {
    if (pointsWithCoords.length === 0) return '';
    const line = pointsWithCoords.reduce((acc, p, idx) => {
      return `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.yRisk.toFixed(1)}`;
    }, '');
    const firstX = pointsWithCoords[0].x.toFixed(1);
    const lastX = pointsWithCoords[pointsWithCoords.length - 1].x.toFixed(1);
    const bottomY = (padding.top + innerHeight).toFixed(1);
    return `${line} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;
  }, [pointsWithCoords, padding.top, innerHeight]);

  const critLinePath = useMemo(() => {
    if (pointsWithCoords.length === 0) return '';
    return pointsWithCoords.reduce((acc, p, idx) => {
      return `${acc} ${idx === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.yCrit.toFixed(1)}`;
    }, '');
  }, [pointsWithCoords]);

  if (isLoading && points.length === 0) {
    return (
      <div className="space-y-6 font-mono animate-pulse" aria-label="Loading estate trend">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4 min-h-[72px]">
          <div>
            <div className="h-3 w-48 bg-[var(--surface-raised)] rounded mb-2" />
            <div className="h-6 w-72 bg-[var(--surface-raised)] rounded" />
          </div>
          <div className="h-8 w-40 bg-[var(--surface-raised)] rounded" />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 min-h-[110px]">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg h-[110px]"
            />
          ))}
        </div>
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 h-[300px]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-widest text-[var(--crypto-pqc)] font-bold">
              Historical Posture & Trajectory
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--crypto-pqc)]" />
              Active Trend Tracking
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1">
            Estate Cryptographic Trend
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Temporal analysis of cryptographic exposure, critical findings remediation, and PQC migration velocity.
          </p>
        </div>

        {/* Time Window Selector */}
        <div className="flex items-center gap-1.5 bg-[var(--surface-raised)] p-1 rounded-lg border border-[var(--border-subtle)] text-xs">
          <Calendar className="w-3.5 h-3.5 ml-2 mr-1 text-[var(--text-muted)]" />
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setSelectedDays(days)}
              className={`px-3 py-1 rounded transition-colors ${
                selectedDays === days
                  ? 'bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold shadow-sm'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
              aria-label={`Show ${days} days trend`}
            >
              {days}D
            </button>
          ))}
        </div>
      </header>

      {/* Trajectory Bento Cards */}
      <section aria-label="Trend Velocity Metrics" className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Net Risk Delta */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--border-prominent)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Risk Score Velocity</span>
            {riskDelta <= 0 ? (
              <TrendingDown className="w-4 h-4 text-[var(--crypto-pqc)]" />
            ) : (
              <TrendingUp className="w-4 h-4 text-[var(--crypto-shor)]" />
            )}
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span
              className={`text-2xl sm:text-3xl font-bold ${
                riskDelta <= 0 ? 'text-[var(--crypto-pqc)]' : 'text-[var(--crypto-shor)]'
              }`}
            >
              {riskDelta > 0 ? `+${riskDelta}` : riskDelta}
            </span>
            <span className="text-xs text-[var(--text-muted)]">pts / {selectedDays}d</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)] flex items-center gap-1">
            {riskDelta <= 0 ? (
              <>
                <ArrowDownRight className="w-3 h-3 text-[var(--crypto-pqc)]" />
                <span>Improving posture trajectory</span>
              </>
            ) : (
              <>
                <ArrowUpRight className="w-3 h-3 text-[var(--crypto-shor)]" />
                <span>Degrading posture</span>
              </>
            )}
          </div>
        </div>

        {/* Critical Findings Resolved */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-shor-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Critical Assets Delta</span>
            <AlertTriangle className="w-4 h-4 text-[var(--crypto-shor)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span
              className={`text-2xl sm:text-3xl font-bold ${
                criticalDelta <= 0 ? 'text-[var(--crypto-pqc)]' : 'text-[var(--crypto-shor)]'
              }`}
            >
              {criticalDelta > 0 ? `+${criticalDelta}` : criticalDelta}
            </span>
            <span className="text-xs text-[var(--text-muted)]">criticals</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span>{lastPoint?.criticalCount ?? 0} active critical risks remaining</span>
          </div>
        </div>

        {/* Total Findings Discovered */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-classical-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">Total Findings Delta</span>
            <Layers className="w-4 h-4 text-[var(--crypto-classical)]" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-bold text-[var(--text-primary)]">
              {findingsDelta > 0 ? `+${findingsDelta}` : findingsDelta}
            </span>
            <span className="text-xs text-[var(--text-muted)]">assets</span>
          </div>
          <div className="text-[10px] text-[var(--text-secondary)]">
            <span>Current inventory: {lastPoint?.totalFindings ?? 0} assets</span>
          </div>
        </div>

        {/* Migration Horizon Projection */}
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-4 rounded-lg flex flex-col justify-between hover:border-[var(--crypto-pqc-border)] transition-colors">
          <div className="flex items-center justify-between text-[var(--text-muted)]">
            <span className="text-[11px] uppercase tracking-wider">PQC Horizon Projection</span>
            <Sparkles className="w-4 h-4 text-[var(--crypto-pqc)]" />
          </div>
          <div className="my-2">
            <span className="text-sm sm:text-base font-bold text-[var(--crypto-pqc)]">
              {projectionText}
            </span>
          </div>
          <div className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Based on {selectedDays}-day burn rate</span>
          </div>
        </div>
      </section>

      {/* SVG Time Series Visualization */}
      <section
        aria-label="Temporal Risk and Findings Trajectory Chart"
        className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-4 sm:p-6 shadow-sm overflow-hidden"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <div>
            <h2 className="text-sm font-bold text-[var(--text-primary)]">
              Estate Risk Score & Critical Findings Trajectory
            </h2>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">
              Dual-axis temporal plot over {selectedDays} days. Hover over points for daily telemetry.
            </p>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-[var(--crypto-pqc)] rounded-full" />
              <span className="text-[var(--text-secondary)]">Avg Risk Score (0-100)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-[var(--crypto-shor)] rounded-full" />
              <span className="text-[var(--text-secondary)]">Critical Findings</span>
            </div>
          </div>
        </div>

        {/* Chart Viewport */}
        <div className="w-full overflow-x-auto">
          <div className="min-w-[640px]">
            <svg
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
              className="w-full h-auto overflow-visible select-none"
              role="img"
              aria-label="Trend line chart showing risk score and critical findings over time"
            >
              <defs>
                <linearGradient id="riskAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--crypto-pqc)" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="var(--crypto-pqc)" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Horizontal grid lines & Y-axis labels */}
              {[0, 25, 50, 75, 100].map((score) => {
                const y = padding.top + innerHeight - (score / maxRisk) * innerHeight;
                return (
                  <g key={score}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={padding.left + innerWidth}
                      y2={y}
                      stroke="var(--border-subtle)"
                      strokeDasharray="3 3"
                      strokeWidth="1"
                    />
                    <text
                      x={padding.left - 8}
                      y={y + 3}
                      textAnchor="end"
                      fontSize="9"
                      fill="var(--text-muted)"
                      fontFamily="monospace"
                    >
                      {score}
                    </text>
                  </g>
                );
              })}

              {/* Risk Area & Line */}
              {riskAreaPath && <path d={riskAreaPath} fill="url(#riskAreaGrad)" />}
              {riskLinePath && (
                <path
                  d={riskLinePath}
                  fill="none"
                  stroke="var(--crypto-pqc)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Critical Line */}
              {critLinePath && (
                <path
                  d={critLinePath}
                  fill="none"
                  stroke="var(--crypto-shor)"
                  strokeWidth="2"
                  strokeDasharray="4 3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Interactive Data Points */}
              {pointsWithCoords.map((p, idx) => {
                const isHovered = hoveredPoint?.date === p.date;
                return (
                  <g key={p.date}>
                    {/* Invisible hover capture column */}
                    <rect
                      x={p.x - 15}
                      y={padding.top}
                      width="30"
                      height={innerHeight}
                      fill="transparent"
                      className="cursor-pointer"
                      onMouseEnter={() => setHoveredPoint(p)}
                      onMouseLeave={() => setHoveredPoint(null)}
                    />

                    {/* Risk Circle */}
                    <circle
                      cx={p.x}
                      cy={p.yRisk}
                      r={isHovered ? 5 : 3.5}
                      fill="var(--surface-card)"
                      stroke="var(--crypto-pqc)"
                      strokeWidth={isHovered ? 2.5 : 2}
                      className="transition-all"
                    />

                    {/* Critical Circle */}
                    <circle
                      cx={p.x}
                      cy={p.yCrit}
                      r={isHovered ? 4.5 : 3}
                      fill="var(--surface-card)"
                      stroke="var(--crypto-shor)"
                      strokeWidth={isHovered ? 2.5 : 1.5}
                      className="transition-all"
                    />

                    {/* X-axis date label */}
                    {(idx === 0 ||
                      idx === pointsWithCoords.length - 1 ||
                      idx % Math.ceil(pointsWithCoords.length / 5) === 0) && (
                      <text
                        x={p.x}
                        y={padding.top + innerHeight + 18}
                        textAnchor="middle"
                        fontSize="9"
                        fill="var(--text-muted)"
                        fontFamily="monospace"
                      >
                        {p.date.substring(5)}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Hover Tooltip Overlay */}
              {hoveredPoint && (
                <g>
                  {(() => {
                    const match = pointsWithCoords.find((pt) => pt.date === hoveredPoint.date);
                    if (!match) return null;
                    const tooltipX = Math.min(Math.max(match.x - 70, 10), chartWidth - 150);
                    const tooltipY = Math.max(match.yRisk - 75, 10);
                    return (
                      <g>
                        <line
                          x1={match.x}
                          y1={padding.top}
                          x2={match.x}
                          y2={padding.top + innerHeight}
                          stroke="var(--crypto-pqc)"
                          strokeWidth="1"
                          strokeDasharray="2 2"
                          opacity="0.8"
                        />
                        <rect
                          x={tooltipX}
                          y={tooltipY}
                          width="140"
                          height="64"
                          rx="6"
                          fill="var(--surface-overlay)"
                          stroke="var(--border-prominent)"
                          strokeWidth="1"
                          className="shadow-lg backdrop-blur-md"
                        />
                        <text
                          x={tooltipX + 10}
                          y={tooltipY + 16}
                          fontSize="10"
                          fontWeight="bold"
                          fill="var(--text-primary)"
                          fontFamily="monospace"
                        >
                          {match.date}
                        </text>
                        <text
                          x={tooltipX + 10}
                          y={tooltipY + 34}
                          fontSize="9"
                          fill="var(--crypto-pqc)"
                          fontFamily="monospace"
                        >
                          Avg Risk: {match.avgRiskScore.toFixed(1)} pts
                        </text>
                        <text
                          x={tooltipX + 10}
                          y={tooltipY + 50}
                          fontSize="9"
                          fill="var(--crypto-shor)"
                          fontFamily="monospace"
                        >
                          Criticals: {match.criticalCount} | Total: {match.totalFindings}
                        </text>
                      </g>
                    );
                  })()}
                </g>
              )}
            </svg>
          </div>
        </div>
      </section>

      {/* Historical Breakdown Table */}
      <section
        aria-labelledby="historical-breakdown-heading"
        className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg overflow-hidden shadow-sm"
      >
        <div className="p-4 border-b border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-overlay)]">
          <div className="flex items-center gap-2">
            <h2 id="historical-breakdown-heading" className="text-sm font-bold text-[var(--text-primary)]">
              Daily Cryptographic Telemetry Log
            </h2>
            <span className="text-xs px-2 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
              {points.length} Snapshots
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse" role="table" aria-label="Daily Telemetry">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--surface-raised)] text-[var(--text-muted)] uppercase text-[10px] tracking-wider">
                <th scope="col" className="py-3 px-4 font-semibold">Snapshot Date</th>
                <th scope="col" className="py-3 px-3 font-semibold">Avg Risk Score</th>
                <th scope="col" className="py-3 px-3 font-semibold">Critical Assets</th>
                <th scope="col" className="py-3 px-3 font-semibold">Total Findings</th>
                <th scope="col" className="py-3 px-3 font-semibold">Risk Delta</th>
                <th scope="col" className="py-3 px-4 font-semibold text-right">Trend Posture</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {points.map((pt, idx) => {
                const prev = points[idx - 1];
                const dailyDelta = prev
                  ? Number((pt.avgRiskScore - prev.avgRiskScore).toFixed(1))
                  : 0;
                return (
                  <tr
                    key={pt.date}
                    className="hover:bg-[var(--surface-raised)] transition-colors"
                  >
                    <td className="py-2.5 px-4 font-semibold text-[var(--text-primary)]">
                      {pt.date}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-bold text-[var(--crypto-pqc)]">
                        {pt.avgRiskScore.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--crypto-shor-bg)] text-[var(--crypto-shor)] border border-[var(--crypto-shor-border)]">
                        {pt.criticalCount}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[var(--text-secondary)]">
                      {pt.totalFindings}
                    </td>
                    <td className="py-2.5 px-3">
                      {idx === 0 ? (
                        <span className="text-[var(--text-muted)]">—</span>
                      ) : dailyDelta <= 0 ? (
                        <span className="text-[var(--crypto-pqc)] flex items-center gap-0.5">
                          <ArrowDownRight className="w-3 h-3" />
                          <span>{dailyDelta}</span>
                        </span>
                      ) : (
                        <span className="text-[var(--crypto-shor)] flex items-center gap-0.5">
                          <ArrowUpRight className="w-3 h-3" />
                          <span>+{dailyDelta}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      {pt.avgRiskScore < 60 ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] border border-[var(--crypto-pqc-border)]">
                          Remediated
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-[var(--crypto-grover-bg)] text-[var(--crypto-grover)] border border-[var(--crypto-grover-border)]">
                          Migrating
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
