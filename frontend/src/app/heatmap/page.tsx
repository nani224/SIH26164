'use client';

import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScanFindings } from '../../lib/api';
import { UnauthorizedState } from '../../components/UnauthorizedState';
import { isUnauthorizedError } from '../../lib/auth';
import { Grid, RefreshCw } from 'lucide-react';

export default function HeatmapPage() {
  const router = useRouter();
  const { activeScanId } = useAppStore();

  const { data: findingsData, isLoading, error, refetch } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  const findings = findingsData?.items ?? [];

  // Matches contracts/openapi.yaml's Surface enum exactly.
  const surfaces = ['source', 'binary', 'certificate', 'config', 'image', 'manifest'];

  const families = ['RSA', 'ECDH', 'DH', 'AES', 'SHA-1', 'DES', 'RC4', 'ML-KEM'];

  // Compute cell data
  const matrixData = surfaces.map((surface) => {
    return {
      surface,
      cells: families.map((family) => {
        const matches = findings.filter(
          (f) => f.surface === surface && f.risk !== null && f.risk !== undefined && (f.family ?? '').toUpperCase().includes(family)
        ) as Array<(typeof findings)[number] & { risk: NonNullable<(typeof findings)[number]['risk']> }>;
        if (matches.length === 0) return null;

        const worstScore = Math.max(...matches.map((m) => m.risk.score));
        const worstBand = matches.find((m) => m.risk.score === worstScore)?.risk.band || 'low';
        const isBroken = matches.some((m) => m.risk.classicallyBroken);

        return {
          family,
          count: matches.length,
          worstScore,
          worstBand,
          isBroken,
          items: matches,
        };
      }),
    };
  });

  const handleCellClick = (surface: string, family: string) => {
    router.push(`/inventory?surface=${surface}&family=${family}`);
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Grid className="w-3.5 h-3.5" />
            <span>SCREEN 7 · ATTACK SURFACE × CRYPTOGRAPHIC FAMILY HEATMAP</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Cryptographic Exposure Matrix
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Cell color = Worst Threat Score in cell · Hatch = Classically Broken. Click any cell to drill into Inventory.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center p-12 text-[var(--text-muted)] gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
          <span>LOADING EXPOSURE MATRIX TELEMETRY...</span>
        </div>
      ) : isUnauthorizedError(error) ? (
        <UnauthorizedState
          onRetry={() => refetch()}
          context="Screen 7 · Attack Surface Exposure Heatmap"
        />
      ) : error ? (
        <div className="p-8 text-center text-xs border border-[var(--band-critical)] rounded-lg bg-[var(--surface-card)]">
          <p className="text-[var(--band-critical)]">Failed to query exposure telemetry from API endpoint.</p>
        </div>
      ) : (
        /* Heatmap Matrix Grid */
        <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-xl p-5 overflow-x-auto shadow-xl">
          <table className="w-full text-center border-collapse">
            <thead>
              <tr>
                <th className="p-3 text-left font-bold text-[var(--text-secondary)] border-b border-[var(--border-subtle)]">
                  ATTACK SURFACE
                </th>
                {families.map((fam) => (
                  <th
                    key={fam}
                    className="p-3 font-bold text-[var(--text-primary)] border-b border-[var(--border-subtle)]"
                  >
                    {fam}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {matrixData.map(({ surface, cells }) => (
                <tr key={surface} className="hover:bg-[var(--surface-raised)] transition-colors">
                  <td className="p-3 text-left font-semibold text-[var(--text-primary)]">
                    {surface}
                  </td>
                  {cells.map((cell, idx) => {
                    const fam = families[idx];
                    if (!cell) {
                      return (
                        <td key={fam} className="p-3 text-[var(--text-muted)] opacity-30">
                          —
                        </td>
                      );
                    }

                    let bgClass = 'bg-[oklch(0.62_0.14_150_/_0.15)] text-[var(--band-low)] border-[var(--band-low)]';
                    if (cell.worstBand === 'critical') {
                      bgClass = 'bg-[var(--crypto-shor-bg)] text-[var(--band-critical)] border-[var(--band-critical)]';
                    } else if (cell.worstBand === 'high') {
                      bgClass = 'bg-[oklch(0.62_0.21_45_/_0.2)] text-[var(--band-high)] border-[var(--band-high)]';
                    } else if (cell.worstBand === 'medium') {
                      bgClass = 'bg-[var(--crypto-grover-bg)] text-[var(--band-medium)] border-[var(--band-medium)]';
                    }

                    return (
                      <td key={fam} className="p-2">
                        <button
                          onClick={() => handleCellClick(surface, fam)}
                          className={`w-full py-2.5 px-2 rounded border text-center transition-all hover:scale-105 ${bgClass} ${
                            cell.isBroken ? 'hatch-broken font-bold' : ''
                          }`}
                          title={`${surface} × ${fam}: ${cell.count} finding(s), Worst score: ${cell.worstScore.toFixed(1)}`}
                        >
                          <div className="font-bold text-xs num-tabular">
                            {cell.worstScore.toFixed(0)}
                          </div>
                          <div className="text-[9px] font-semibold mt-0.5">
                            {cell.count} asset{cell.count > 1 ? 's' : ''}
                          </div>
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
