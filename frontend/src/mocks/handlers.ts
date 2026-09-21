import { http, HttpResponse } from 'msw';
import {
  mockFindings,
  mockScans,
  mockPqcCatalog,
  mockPolicies,
  mockGraph,
  mockCbom,
  mockPlan,
  mockTargets,
  mockEstateSummary,
  mockEstateTrend,
  mockDrifts,
  mockAlerts,
  mockProbes,
  mockHsmInventory,
  mockAuditVerify,
} from './data';
import type {
  Finding,
  RiskBand,
  Scan,
  Policy,
  Target,
  TargetCreate,
  TargetPatch,
  EstateSummary,
  Alert,
} from '../types/crypto';

let findingsStore = [...mockFindings];
let scansStore = [...mockScans];
let policiesStore = [...mockPolicies];
let targetsStore = [...mockTargets];
let estateSummaryStore = { ...mockEstateSummary };
let alertsStore = [...mockAlerts];

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
    return HttpResponse.json(scansStore);
  }),

  // Create / Launch scan
  http.post('/api/v1/scans', async ({ request }) => {
    let target = 'uploaded-bundle.tar.gz';
    let policyId = 'policy-default-defense';
    let crqcYears = 10;

    const contentType = request.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const body = (await request.json()) as { path?: string; policyId?: string; crqcYears?: number };
      if (body.path) target = body.path;
      if (body.policyId) policyId = body.policyId;
      if (body.crqcYears) crqcYears = body.crqcYears;
    } else if (contentType.includes('multipart/form-data')) {
      try {
        const formData = await request.formData();
        const file = formData.get('file') as File | null;
        if (file) target = file.name;
        const pol = formData.get('policyId') as string | null;
        if (pol) policyId = pol;
        const crqc = formData.get('crqcYears') as string | null;
        if (crqc) crqcYears = parseInt(crqc, 10);
      } catch {
        // Fallback to defaults
      }
    }

    const newScan: Scan = {
      id: `scan-${Math.random().toString(16).substring(2, 8)}`,
      target,
      status: 'ingesting',
      stats: {
        files: 1420,
        bytes: 28450190,
        seconds: 3.42,
        mbPerSec: 8.3,
        errors: 0,
        skippedPrefilter: 312,
      },
      bands: {
        critical: 7,
        high: 9,
        medium: 14,
        low: 22,
      },
      policyId,
      crqcYears,
      startedAt: new Date().toISOString(),
      finishedAt: new Date(Date.now() + 4000).toISOString(),
    };

    scansStore.unshift(newScan);
    return HttpResponse.json(newScan, { status: 202 });
  }),

  // Upload scan archive
  http.post('/api/v1/scans/upload', async ({ request }) => {
    let target = 'uploaded-bundle.tar.gz';
    let policyId = 'policy-default-defense';
    let crqcYears = 10;

    try {
      const formData = await request.formData();
      const file = formData.get('file') as File | null;
      if (file) target = file.name;
      const pol = formData.get('policyId') as string | null;
      if (pol) policyId = pol;
      const crqc = formData.get('crqcYears') as string | null;
      if (crqc) crqcYears = parseInt(crqc, 10);
    } catch {
      // Fallback to defaults
    }

    const newScan: Scan = {
      id: `scan-${Math.random().toString(16).substring(2, 8)}`,
      target,
      status: 'done',
      stats: {
        files: 1420,
        bytes: 28450190,
        seconds: 3.42,
        mbPerSec: 8.3,
        errors: 0,
        skippedPrefilter: 312,
      },
      bands: {
        critical: 7,
        high: 9,
        medium: 14,
        low: 22,
      },
      policyId,
      crqcYears,
      startedAt: new Date().toISOString(),
      finishedAt: new Date().toISOString(),
    };

    scansStore.unshift(newScan);
    return HttpResponse.json(newScan, { status: 201 });
  }),

  // Get scan
  http.get('/api/v1/scans/:id', ({ params }) => {
    const scan = scansStore.find((s) => s.id === params.id) || scansStore[0];
    return HttpResponse.json(scan);
  }),

  // Get findings
  http.get('/api/v1/scans/:id/findings', ({ request }) => {
    const url = new URL(request.url);
    const band = url.searchParams.get('band');
    const family = url.searchParams.get('family');
    const surface = url.searchParams.get('surface');
    const q = url.searchParams.get('q')?.toLowerCase();
    const needsReview = url.searchParams.get('needsReview');

    let filtered = [...findingsStore];
    if (band && band !== 'all') {
      filtered = filtered.filter((f) => f.risk?.band === band);
    }
    if (surface && surface !== 'all') {
      filtered = filtered.filter((f) => f.surface === surface);
    }
    if (family && family !== 'all') {
      filtered = filtered.filter((f) => (f.family ?? '').toLowerCase().includes(family.toLowerCase()));
    }
    if (q) {
      filtered = filtered.filter(
        (f) =>
          f.displayName.toLowerCase().includes(q) ||
          (f.family ?? '').toLowerCase().includes(q) ||
          f.location.path.toLowerCase().includes(q) ||
          f.surface.toLowerCase().includes(q)
      );
    }
    if (needsReview === 'true') {
      filtered = filtered.filter((f) => f.risk?.needsReview);
    }

    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      nextCursor: null,
    });
  }),

  // Rescore endpoint: applies Mosca X + Y - Z formula.
  // Response shape matches contracts/openapi.yaml's RescoreResult exactly:
  // {bands, changed}. changed carries the NEW Finding state only -- same
  // as the real backend (api/store.py::rescore_scan_findings) -- so the
  // frontend must diff against its own pre-rescore snapshot for "previous"
  // values, never trust a fabricated previousBand/previousScore from here.
  http.post('/api/v1/scans/:id/rescore', async ({ request }) => {
    const body = (await request.json()) as { crqcYears?: number; policyId?: string };
    const z = body.crqcYears ?? 10;

    const changed: Finding[] = [];
    const bands = { critical: 0, high: 0, medium: 0, low: 0 };

    findingsStore = findingsStore.map((f) => {
      if (!f.risk) {
        return f;
      }
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
        // Classically broken assets strictly preserve U = 1 invariant
        newU = 1.0;
      }

      bands[newBand]++;

      const updated: Finding = {
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

      if (newBand !== prevBand || Math.abs(newScore - prevScore) > 0.1) {
        changed.push(updated);
      }

      return updated;
    });

    return HttpResponse.json({ bands, changed });
  }),

  // Get crypto estate hierarchy graph
  http.get('/api/v1/scans/:id/graph', () => {
    return HttpResponse.json(mockGraph);
  }),

  // Download CycloneDX 1.6 CBOM
  http.get('/api/v1/scans/:id/cbom', () => {
    return HttpResponse.json(mockCbom);
  }),

  // Get remediation plan. Matches contracts/openapi.yaml's RemediationPlan
  // exactly: {scanId, generatedAt, items} -- not a bare array.
  http.get('/api/v1/scans/:id/plan', ({ params }) => {
    return HttpResponse.json({
      scanId: params.id,
      generatedAt: new Date().toISOString(),
      items: mockPlan,
    });
  }),

  // Policies CRUD
  http.get('/api/v1/policies', () => {
    return HttpResponse.json(policiesStore);
  }),

  http.post('/api/v1/policies', async ({ request }) => {
    const newPolicy = (await request.json()) as Policy;
    policiesStore.push(newPolicy);
    return HttpResponse.json(newPolicy, { status: 201 });
  }),

  http.get('/api/v1/policies/:id', ({ params }) => {
    const policy = policiesStore.find((p) => p.id === params.id);
    if (!policy) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(policy);
  }),

  http.put('/api/v1/policies/:id', async ({ params, request }) => {
    const updated = (await request.json()) as Policy;
    const idx = policiesStore.findIndex((p) => p.id === params.id);
    if (idx === -1) {
      policiesStore.push(updated);
    } else {
      policiesStore[idx] = updated;
    }
    return HttpResponse.json(updated);
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

  // Estate Summary
  http.get('/api/v1/estate/summary', () => {
    return HttpResponse.json(estateSummaryStore);
  }),

  // Estate Trend
  http.get('/api/v1/estate/trend', () => {
    return HttpResponse.json(mockEstateTrend);
  }),

  // Targets CRUD
  http.get('/api/v1/targets', () => {
    return HttpResponse.json(targetsStore);
  }),

  http.post('/api/v1/targets', async ({ request }) => {
    const body = (await request.json()) as TargetCreate;
    const newTarget: Target = {
      id: `target-${Math.random().toString(16).substring(2, 8)}`,
      name: body.name,
      kind: body.kind,
      uri: body.uri,
      policyId: body.policyId,
      schedule: body.schedule,
      enabled: body.enabled ?? true,
      lastScanId: null,
      lastScanAt: null,
      createdAt: new Date().toISOString(),
    };
    targetsStore.unshift(newTarget);
    estateSummaryStore.totalTargets = targetsStore.length;
    return HttpResponse.json(newTarget, { status: 201 });
  }),

  http.get('/api/v1/targets/:id', ({ params }) => {
    const target = targetsStore.find((t) => t.id === params.id);
    if (!target) return new HttpResponse(null, { status: 404 });
    return HttpResponse.json(target);
  }),

  http.patch('/api/v1/targets/:id', async ({ params, request }) => {
    const idx = targetsStore.findIndex((t) => t.id === params.id);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    const patch = (await request.json()) as TargetPatch;
    targetsStore[idx] = {
      ...targetsStore[idx],
      ...(patch.name !== undefined && patch.name !== null ? { name: patch.name } : {}),
      ...(patch.policyId !== undefined && patch.policyId !== null ? { policyId: patch.policyId } : {}),
      ...(patch.schedule !== undefined && patch.schedule !== null ? { schedule: patch.schedule } : {}),
      ...(patch.enabled !== undefined && patch.enabled !== null ? { enabled: patch.enabled } : {}),
    };
    return HttpResponse.json(targetsStore[idx]);
  }),

  http.delete('/api/v1/targets/:id', ({ params }) => {
    const idx = targetsStore.findIndex((t) => t.id === params.id);
    if (idx === -1) return new HttpResponse(null, { status: 404 });
    targetsStore.splice(idx, 1);
    estateSummaryStore.totalTargets = targetsStore.length;
    return new HttpResponse(null, { status: 204 });
  }),

  // Target Scan Now
  http.post('/api/v1/targets/:id/scan-now', ({ params }) => {
    const target = targetsStore.find((t) => t.id === params.id);
    if (!target) return new HttpResponse(null, { status: 404 });

    const scanId = `scan-${Math.random().toString(16).substring(2, 8)}`;
    const newScan: Scan = {
      id: scanId,
      target: target.name,
      status: 'ingesting',
      stats: {
        files: 1420,
        bytes: 28450190,
        seconds: 3.42,
        mbPerSec: 8.3,
        errors: 0,
        skippedPrefilter: 312,
      },
      bands: {
        critical: 5,
        high: 7,
        medium: 12,
        low: 18,
      },
      policyId: target.policyId,
      crqcYears: 10,
      startedAt: new Date().toISOString(),
      finishedAt: new Date(Date.now() + 4000).toISOString(),
    };

    scansStore.unshift(newScan);
    target.lastScanId = scanId;
    target.lastScanAt = new Date().toISOString();
    estateSummaryStore.totalScans += 1;

    return HttpResponse.json(newScan, { status: 202 });
  }),

  // Target Drift
  http.get('/api/v1/targets/:id/drift', ({ params }) => {
    const targetId = params.id as string;
    const drift = mockDrifts[targetId] || {
      targetId,
      fromSnapshotId: 'snap-prev',
      toSnapshotId: 'snap-curr',
      added: [],
      resolved: [],
      changed: [],
      summary: {
        addedCount: 0,
        resolvedCount: 0,
        changedCount: 0,
        netRiskDelta: 0,
      },
    };
    return HttpResponse.json(drift);
  }),

  // Alerts
  http.get('/api/v1/alerts', ({ request }) => {
    const url = new URL(request.url);
    const targetId = url.searchParams.get('targetId');
    const type = url.searchParams.get('type');
    const acknowledged = url.searchParams.get('acknowledged');

    let result = [...alertsStore];
    if (targetId) result = result.filter((a) => a.targetId === targetId);
    if (type) result = result.filter((a) => a.type === type);
    if (acknowledged !== null) {
      const isAck = acknowledged === 'true';
      result = result.filter((a) => a.acknowledged === isAck);
    }
    return HttpResponse.json(result);
  }),

  http.patch('/api/v1/alerts/:id/ack', ({ params }) => {
    const alert = alertsStore.find((a) => a.id === params.id);
    if (!alert) return new HttpResponse(null, { status: 404 });
    alert.acknowledged = true;
    estateSummaryStore.activeAlerts = alertsStore.filter((a) => !a.acknowledged).length;
    return HttpResponse.json(alert);
  }),

  // Probes
  http.get('/api/v1/probes', ({ request }) => {
    const url = new URL(request.url);
    const targetId = url.searchParams.get('targetId');
    if (targetId) {
      return HttpResponse.json(mockProbes.filter((p) => p.targetId === targetId));
    }
    return HttpResponse.json(mockProbes);
  }),

  // HSM Inventory
  http.get('/api/v1/hsm/inventory', () => {
    return HttpResponse.json(mockHsmInventory);
  }),

  // Audit Verify Chain
  http.get('/api/v1/audit/verify', () => {
    return HttpResponse.json(mockAuditVerify);
  }),
];
