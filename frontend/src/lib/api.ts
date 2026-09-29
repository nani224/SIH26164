import type {
  Finding,
  Scan,
  Policy,
  RemediationPlanItem,
  GraphNode,
  GraphEdge,
  RiskBands,
  Target,
  TargetCreate,
  TargetPatch,
  EstateSummary,
  EstateTrend,
  Drift,
  Alert,
  ProbeResult,
  HsmInventory,
  AuditVerifyResponse,
  CoverageCertificate,
  ArtifactCoverage,
  ResidueCluster,
  ResidueClusterState,
  ResidueClusterPatch,
  AssetCriticality,
  CriticalityImportResponse,
  CloudKeysResponse,
  EstateCoverage,
} from '../types/crypto';
import { ApiError, getAuthHeaders, isUnauthorizedError } from './auth';
import {
  mockScans,
  mockFindings,
  mockGraph,
  mockPlan,
  mockPolicies,
  mockEstateSummary,
  mockTargets,
} from '../mocks/data';

export { ApiError, isUnauthorizedError };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface FindingsFilterParams {
  band?: string;
  family?: string;
  surface?: string;
  q?: string;
  needsReview?: boolean;
}

// Matches contracts/openapi.yaml's RescoreResult exactly: {bands, changed}.
// changed is the list of Findings whose band or score actually moved -- the
// backend computes this server-side; the frontend must not fabricate a
// "previous" value from the same post-rescore record (see git history for
// why -- that used to make every real, non-mocked rescore show zero change).
export interface RescoreResult {
  bands: RiskBands;
  changed: Finding[];
}

/**
 * Central fetch wrapper attaching `Authorization: Bearer <token>` and `X-ECDAT-Actor: <actor>`
 * to all API requests made by the frontend.
 */
export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const authHeaders = getAuthHeaders();
  for (const [key, value] of Object.entries(authHeaders)) {
    if (!headers.has(key)) {
      headers.set(key, value);
    }
  }
  return fetch(input, {
    ...init,
    headers,
  });
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let bodyText = '';
    let parsedBody: unknown = undefined;
    try {
      bodyText = await res.text();
      parsedBody = JSON.parse(bodyText);
    } catch {
      // Body is not JSON or is empty
    }
    throw new ApiError(res.status, bodyText || res.statusText || `API Error ${res.status}`, parsedBody);
  }
  return res.json() as Promise<T>;
}

export async function fetchScans(): Promise<Scan[]> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans`);
    return await handleResponse<Scan[]>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to mock scans:', err);
    return mockScans;
  }
}

export async function fetchScan(id: string): Promise<Scan> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans/${id}`);
    return await handleResponse<Scan>(res);
  } catch (err) {
    console.warn(`[ECDAT API] Offline fallback to mock scan for ${id}:`, err);
    return mockScans.find((s) => s.id === id) || mockScans[0];
  }
}

export async function fetchScanFindings(
  id: string,
  params?: FindingsFilterParams
): Promise<{ items: Finding[]; total: number }> {
  try {
    const query = new URLSearchParams();
    if (params?.band && params.band !== 'all') query.set('band', params.band);
    if (params?.family && params.family !== 'all') query.set('family', params.family);
    if (params?.surface && params.surface !== 'all') query.set('surface', params.surface);
    if (params?.q) query.set('q', params.q);
    if (params?.needsReview !== undefined) query.set('needsReview', String(params.needsReview));

    const qs = query.toString();
    const url = `${API_BASE}/api/v1/scans/${id}/findings${qs ? `?${qs}` : ''}`;
    const res = await apiFetch(url);
    return await handleResponse<{ items: Finding[]; total: number }>(res);
  } catch (err) {
    console.warn(`[ECDAT API] Offline fallback to mock findings for ${id}:`, err);
    let items = mockFindings;
    if (params?.band && params.band !== 'all') items = items.filter((f) => f.risk?.band === params.band);
    if (params?.family && params.family !== 'all') items = items.filter((f) => f.family === params.family);
    if (params?.surface && params.surface !== 'all') items = items.filter((f) => f.surface === params.surface);
    return { items, total: items.length };
  }
}

export async function rescoreScan(
  id: string,
  payload: { crqcYears?: number; policyId?: string }
): Promise<RescoreResult> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans/${id}/rescore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return await handleResponse<RescoreResult>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to simulated rescore:', err);
    return {
      bands: { critical: 4, high: 6, medium: 9, low: 8 },
      changed: mockFindings.slice(0, 3),
    };
  }
}

export async function fetchScanGraph(id: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans/${id}/graph`);
    return await handleResponse<{ nodes: GraphNode[]; edges: GraphEdge[] }>(res);
  } catch (err) {
    console.warn(`[ECDAT API] Offline fallback to mock 3D graph for ${id}:`, err);
    return mockGraph;
  }
}

export async function fetchScanCbom(id: string): Promise<any> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans/${id}/cbom`);
    return await handleResponse<any>(res);
  } catch (err) {
    const { mockCbom } = await import('../mocks/data');
    return mockCbom;
  }
}

export async function fetchScanPlan(id: string): Promise<RemediationPlanItem[]> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/scans/${id}/plan`);
    const data = await handleResponse<{ scanId: string; generatedAt: string; items: RemediationPlanItem[] }>(res);
    return data.items;
  } catch (err) {
    console.warn(`[ECDAT API] Offline fallback to mock remediation plan:`, err);
    return mockPlan;
  }
}

export async function fetchPolicies(): Promise<Policy[]> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/policies`);
    return await handleResponse<Policy[]>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to mock policies:', err);
    return mockPolicies;
  }
}

export async function fetchPolicy(id: string): Promise<Policy> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/policies/${id}`);
    return await handleResponse<Policy>(res);
  } catch (err) {
    console.warn(`[ECDAT API] Offline fallback to mock policy ${id}:`, err);
    return mockPolicies.find((p) => p.id === id) || mockPolicies[0];
  }
}

export async function updatePolicy(id: string, policy: Policy): Promise<Policy> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/policies/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(policy),
    });
    return await handleResponse<Policy>(res);
  } catch {
    return policy;
  }
}

export async function createPolicy(policy: Policy): Promise<Policy> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/policies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(policy),
    });
    return await handleResponse<Policy>(res);
  } catch {
    return policy;
  }
}

export async function createScan(
  data: { path?: string; policyId?: string; crqcYears?: number } | FormData
): Promise<Scan> {
  let options: RequestInit = { method: 'POST' };
  let url = `${API_BASE}/api/v1/scans`;
  if (typeof FormData !== 'undefined' && data instanceof FormData) {
    url = `${API_BASE}/api/v1/scans/upload`;
    options.body = data;
  } else {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  try {
    const res = await apiFetch(url, options);
    return await handleResponse<Scan>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to instant scan simulation:', err);
    return mockScans[0];
  }
}

export async function triageFinding(
  id: string,
  payload: { status: Finding['triage']['status']; note?: string }
): Promise<Finding> {
  const res = await apiFetch(`${API_BASE}/api/v1/findings/${id}/triage`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Finding>(res);
}

// Continuous Operation Endpoints (v0.3.0)

export async function fetchEstateSummary(): Promise<EstateSummary> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/estate/summary`);
    return await handleResponse<EstateSummary>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to mock estate summary:', err);
    return mockEstateSummary;
  }
}

export async function fetchTargets(): Promise<Target[]> {
  try {
    const res = await apiFetch(`${API_BASE}/api/v1/targets`);
    return await handleResponse<Target[]>(res);
  } catch (err) {
    console.warn('[ECDAT API] Offline fallback to mock targets:', err);
    return mockTargets;
  }
}

export async function fetchTarget(id: string): Promise<Target> {
  const res = await apiFetch(`${API_BASE}/api/v1/targets/${id}`);
  return handleResponse<Target>(res);
}

export async function createTarget(payload: TargetCreate): Promise<Target> {
  const res = await apiFetch(`${API_BASE}/api/v1/targets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Target>(res);
}

export async function patchTarget(id: string, payload: TargetPatch): Promise<Target> {
  const res = await apiFetch(`${API_BASE}/api/v1/targets/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Target>(res);
}

export async function deleteTarget(id: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/v1/targets/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text || res.statusText);
  }
}

export async function scanTargetNow(id: string): Promise<Scan> {
  const res = await apiFetch(`${API_BASE}/api/v1/targets/${id}/scan-now`, {
    method: 'POST',
  });
  return handleResponse<Scan>(res);
}

export async function fetchTargetDrift(
  id: string,
  params?: { fromScanId?: string; toScanId?: string }
): Promise<Drift> {
  const query = new URLSearchParams();
  if (params?.fromScanId) query.set('fromScanId', params.fromScanId);
  if (params?.toScanId) query.set('toScanId', params.toScanId);
  const qs = query.toString();
  const url = `${API_BASE}/api/v1/targets/${id}/drift${qs ? `?${qs}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<Drift>(res);
}

export async function fetchAlerts(params?: {
  targetId?: string;
  type?: string;
  acknowledged?: boolean;
}): Promise<Alert[]> {
  const query = new URLSearchParams();
  if (params?.targetId) query.set('targetId', params.targetId);
  if (params?.type) query.set('type', params.type);
  if (params?.acknowledged !== undefined) query.set('acknowledged', String(params.acknowledged));
  const qs = query.toString();
  const url = `${API_BASE}/api/v1/alerts${qs ? `?${qs}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<Alert[]>(res);
}

export async function acknowledgeAlert(id: string): Promise<Alert> {
  const res = await apiFetch(`${API_BASE}/api/v1/alerts/${id}/ack`, {
    method: 'PATCH',
  });
  return handleResponse<Alert>(res);
}

export async function fetchProbes(targetId?: string): Promise<ProbeResult[]> {
  const query = new URLSearchParams();
  if (targetId) query.set('targetId', targetId);
  const qs = query.toString();
  const url = `${API_BASE}/api/v1/probes${qs ? `?${qs}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<ProbeResult[]>(res);
}

export async function fetchHsmInventory(): Promise<HsmInventory> {
  const res = await apiFetch(`${API_BASE}/api/v1/hsm/inventory`);
  return handleResponse<HsmInventory>(res);
}

export async function fetchEstateTrend(days?: number): Promise<EstateTrend> {
  const url = `${API_BASE}/api/v1/estate/trend${days ? `?days=${days}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<EstateTrend>(res);
}

export async function verifyAudit(): Promise<AuditVerifyResponse> {
  const res = await apiFetch(`${API_BASE}/api/v1/audit/verify`);
  return handleResponse<AuditVerifyResponse>(res);
}

// --- v1.0.0 Crypto Mass Conservation (CMC) API Functions ---

export async function fetchScanCoverage(scanId: string): Promise<CoverageCertificate> {
  const res = await apiFetch(`${API_BASE}/api/v1/scans/${scanId}/coverage`);
  return handleResponse<CoverageCertificate>(res);
}

export async function fetchScanArtifactCoverage(scanId: string): Promise<ArtifactCoverage[]> {
  const res = await apiFetch(`${API_BASE}/api/v1/scans/${scanId}/coverage/artifacts`);
  return handleResponse<ArtifactCoverage[]>(res);
}

export async function fetchResidueClusters(params?: {
  state?: ResidueClusterState;
  targetId?: string;
}): Promise<ResidueCluster[]> {
  const query = new URLSearchParams();
  if (params?.state) query.set('state', params.state);
  if (params?.targetId) query.set('targetId', params.targetId);
  const qs = query.toString();
  const url = `${API_BASE}/api/v1/residue${qs ? `?${qs}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<ResidueCluster[]>(res);
}

export async function fetchResidueCluster(id: string): Promise<ResidueCluster> {
  const res = await apiFetch(`${API_BASE}/api/v1/residue/${id}`);
  return handleResponse<ResidueCluster>(res);
}

export async function patchResidueCluster(
  id: string,
  patch: ResidueClusterPatch
): Promise<ResidueCluster> {
  const res = await apiFetch(`${API_BASE}/api/v1/residue/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  return handleResponse<ResidueCluster>(res);
}

export async function fetchAssetCriticalities(targetId?: string): Promise<AssetCriticality[]> {
  const url = `${API_BASE}/api/v1/criticality${targetId ? `?targetId=${targetId}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<AssetCriticality[]>(res);
}

export async function setAssetCriticality(criticality: AssetCriticality): Promise<AssetCriticality> {
  const res = await apiFetch(`${API_BASE}/api/v1/criticality`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(criticality),
  });
  return handleResponse<AssetCriticality>(res);
}

export async function importCriticalityCsv(fileOrText: File | string): Promise<CriticalityImportResponse> {
  const formData = new FormData();
  if (typeof fileOrText === 'string') {
    const blob = new Blob([fileOrText], { type: 'text/csv' });
    formData.append('file', blob, 'criticality.csv');
  } else {
    formData.append('file', fileOrText);
  }
  const res = await apiFetch(`${API_BASE}/api/v1/criticality/import`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<CriticalityImportResponse>(res);
}

export async function fetchCloudKeys(provider?: string): Promise<CloudKeysResponse> {
  const url = `${API_BASE}/api/v1/cloud/keys${provider ? `?provider=${provider}` : ''}`;
  const res = await apiFetch(url);
  return handleResponse<CloudKeysResponse>(res);
}

export async function fetchEstateCoverage(): Promise<EstateCoverage> {
  const res = await apiFetch(`${API_BASE}/api/v1/estate/coverage`);
  return handleResponse<EstateCoverage>(res);
}
