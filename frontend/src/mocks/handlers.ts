import { http, HttpResponse } from 'msw';
import { mockFindings, mockScans, mockPqcCatalog } from './data';
import type { Finding, RiskBand } from '../types/crypto';

let findingsStore = [...mockFindings];

function computeBand(score: number): RiskBand {
  if (score >= 60) return 'critical';
  if (score >= 35) return 'high';
  if (score >= 15) return 'medium';
  return 'low';
}

export const handlers = [
  // Health
  http.get('/api/v1/health', () => {
    return HttpResponse.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
    });
  }),

  // List scans
  http.get('/api/v1/scans', () => {
    return HttpResponse.json(mockScans);
  }),

  // Get scan
  http.get('/api/v1/scans/:id', ({ params }) => {
    const scan = mockScans.find((s) => s.id === params.id) || mockScans[0];
    return HttpResponse.json(scan);
  }),

  // Get findings
  http.get('/api/v1/scans/:id/findings', ({ request }) => {
    const url = new URL(request.url);
    const band = url.searchParams.get('band');
    const q = url.searchParams.get('q')?.toLowerCase();
    const needsReview = url.searchParams.get('needsReview');

    let filtered = [...findingsStore];
    if (band) {
      filtered = filtered.filter((f) => f.risk.band === band);
    }
    if (q) {
      filtered = filtered.filter(
        (f) =>
          f.displayName.toLowerCase().includes(q) ||
          f.family.toLowerCase().includes(q) ||
          f.location.path.toLowerCase().includes(q)
      );
    }
    if (needsReview === 'true') {
      filtered = filtered.filter((f) => f.risk.needsReview);
    }

    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      nextCursor: null,
    });
  }),

  // Rescore endpoint: applies Mosca X + Y - Z formula
  http.post('/api/v1/scans/:id/rescore', async ({ request }) => {
    const body = (await request.json()) as { crqcYears?: number; policyId?: string };
    const z = body.crqcYears ?? 10;

    const changedFindings: Array<{
      id: string;
      displayName: string;
      previousBand: RiskBand;
      newBand: RiskBand;
      previousScore: number;
      newScore: number;
    }> = [];

    const bands = { critical: 0, high: 0, medium: 0, low: 0 };

    findingsStore = findingsStore.map((f) => {
      const prevScore = f.risk.score;
      const prevBand = f.risk.band;

      let newU = f.risk.U;
      let newScore = prevScore;
      let newBand = prevBand;
      const newMargin = f.risk.X + f.risk.Y - z;

      if (!f.risk.classicallyBroken) {
        // Quantum-sensitive assets recalculate U based on Mosca margin
        const rawU = 0.5 + newMargin / (2 * z);
        newU = Math.max(0.05, Math.min(1.0, rawU));
        newScore = Math.round(100 * f.risk.V * f.risk.F * newU * f.risk.E * f.risk.K * 10) / 10;
        newBand = computeBand(newScore);
      } else {
        // Classically broken assets have U = 1 invariant
        newU = 1.0;
      }

      bands[newBand]++;

      if (newBand !== prevBand || Math.abs(newScore - prevScore) > 0.1) {
        changedFindings.push({
          id: f.id,
          displayName: f.displayName,
          previousBand: prevBand,
          newBand: newBand,
          previousScore: prevScore,
          newScore: newScore,
        });
      }

      return {
        ...f,
        risk: {
          ...f.risk,
          Z: z,
          U: newU,
          moscaMargin: newMargin,
          score: newScore,
          band: newBand,
        },
      };
    });

    return HttpResponse.json({
      bands,
      changedFindings,
    });
  }),

  // Triage finding
  http.patch('/api/v1/findings/:id/triage', async ({ params, request }) => {
    const body = (await request.json()) as { status: Finding['triage']['status']; note?: string };
    const idx = findingsStore.findIndex((f) => f.id === params.id);
    if (idx === -1) {
      return new HttpResponse(null, { status: 404 });
    }

    findingsStore[idx] = {
      ...findingsStore[idx],
      triage: {
        status: body.status,
        note: body.note ?? findingsStore[idx].triage.note,
      },
    };

    return HttpResponse.json(findingsStore[idx]);
  }),

  // Catalog PQC
  http.get('/api/v1/catalog/pqc', () => {
    return HttpResponse.json(mockPqcCatalog);
  }),
];
