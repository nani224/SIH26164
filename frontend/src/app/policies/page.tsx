'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchPolicies, updatePolicy, fetchScanFindings } from '../../lib/api';
import type { Policy, PolicyRule } from '../../types/crypto';
import { Settings, Plus, Trash2, Check, Shield, Layers, Save, Sliders, RefreshCw } from 'lucide-react';

export default function PolicyEditorPage() {
  const { activeScanId } = useAppStore();
  const queryClient = useQueryClient();

  const { data: policies, isLoading: policiesLoading } = useQuery({
    queryKey: ['policies'],
    queryFn: fetchPolicies,
  });

  const { data: findingsData } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  const findings = useMemo(() => findingsData?.items ?? [], [findingsData]);

  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('policy-default-defense');
  const activePolicy = useMemo(
    () => policies?.find((p) => p.id === selectedPolicyId) || policies?.[0],
    [policies, selectedPolicyId]
  );

  const [policyName, setPolicyName] = useState('');
  const [defaultExposure, setDefaultExposure] = useState<'external' | 'internal' | 'isolated' | 'test'>('internal');
  const [defaultCriticality, setDefaultCriticality] = useState<'mission-critical' | 'high' | 'medium' | 'low'>('high');
  const [defaultShelfLife, setDefaultShelfLife] = useState(10);
  const [defaultMigration, setDefaultMigration] = useState(5);
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (activePolicy) {
      setPolicyName(activePolicy.name);
      setDefaultExposure(activePolicy.default.exposure);
      setDefaultCriticality(activePolicy.default.criticality);
      setDefaultShelfLife(activePolicy.default.shelfLifeYears);
      setDefaultMigration(activePolicy.default.migrationYears);
      setRules(activePolicy.contexts || []);
    }
  }, [activePolicy]);

  const saveMutation = useMutation({
    mutationFn: (updated: Policy) => updatePolicy(updated.id, updated),
    onSuccess: (data) => {
      queryClient.setQueryData(['policies'], (old: Policy[] | undefined) =>
        old ? old.map((p) => (p.id === data.id ? data : p)) : [data]
      );
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    },
  });

  // Live count helper for matching findings by glob
  const getMatchCount = (glob: string) => {
    const cleanGlob = glob.replace('/**', '').replace('/*', '');
    return findings.filter((f) => f.location.path.startsWith(cleanGlob)).length;
  };

  const handleAddRule = () => {
    const newRule: PolicyRule = {
      glob: 'new_subsystem/**',
      exposure: 'internal',
      criticality: 'medium',
      shelfLifeYears: 5,
      migrationYears: 3,
    };
    setRules([...rules, newRule]);
  };

  const handleRemoveRule = (index: number) => {
    setRules(rules.filter((_, idx) => idx !== index));
  };

  const handleSave = () => {
    if (!activePolicy) return;
    const updated: Policy = {
      ...activePolicy,
      name: policyName,
      default: {
        exposure: defaultExposure,
        criticality: defaultCriticality,
        shelfLifeYears: defaultShelfLife,
        migrationYears: defaultMigration,
      },
      contexts: rules,
    };
    saveMutation.mutate(updated);
  };

  return (
    <div className="space-y-6 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-4">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Settings className="w-3.5 h-3.5" />
            <span>SCREEN 10 · CRYPTOGRAPHIC POLICY & MOSCA CONTEXT ENGINE</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-[var(--text-primary)]">
            Policy Contexts & Path Matchers
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Configure system criticality, exposure tiers, data shelf life (X), and migration windows (Y). Live API binding.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="px-3 py-1.5 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            {saveMutation.isPending ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : savedSuccess ? (
              <Check className="w-3.5 h-3.5" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            <span>{savedSuccess ? 'COMMITTED TO API' : 'COMMIT POLICY'}</span>
          </button>
        </div>
      </div>

      {policiesLoading ? (
        <div className="p-12 text-center text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
          <span>SYNCHRONIZING POLICIES FROM BACKEND...</span>
        </div>
      ) : (
        <>
          {/* Policy Picker */}
          {policies && policies.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-[var(--text-muted)] uppercase font-bold">Select Policy:</span>
              <select
                value={selectedPolicyId}
                onChange={(e) => setSelectedPolicyId(e.target.value)}
                aria-label="Select active policy"
                className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded px-2.5 py-1 text-xs text-[var(--text-primary)]"
              >
                {policies.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.id})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Policy Baseline Setting */}
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
              <Shield className="w-4 h-4 text-[var(--crypto-pqc)]" />
              <span>Default Baseline Policy Parameters</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                  Policy Name
                </label>
                <input
                  type="text"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                  aria-label="Policy Name"
                  className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none focus:border-[var(--border-prominent)]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                  Default Exposure (E)
                </label>
                <select
                  value={defaultExposure}
                  onChange={(e) => setDefaultExposure(e.target.value as any)}
                  aria-label="Default Exposure"
                  className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none"
                >
                  <option value="external">External (Perimeter / Internet)</option>
                  <option value="internal">Internal (Service Mesh)</option>
                  <option value="isolated">Isolated (Air-Gapped Enclave)</option>
                  <option value="test">Test / Sandbox</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                  Default Criticality (K)
                </label>
                <select
                  value={defaultCriticality}
                  onChange={(e) => setDefaultCriticality(e.target.value as any)}
                  aria-label="Default Criticality"
                  className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] focus:outline-none"
                >
                  <option value="mission-critical">Mission-Critical (K = 1.0)</option>
                  <option value="high">High (K = 0.8)</option>
                  <option value="medium">Medium (K = 0.5)</option>
                  <option value="low">Low (K = 0.2)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                    Shelf Life (X)
                  </label>
                  <input
                    type="number"
                    value={defaultShelfLife}
                    onChange={(e) => setDefaultShelfLife(parseInt(e.target.value, 10))}
                    aria-label="Default Shelf Life in years"
                    className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] num-tabular"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[var(--text-muted)] uppercase block mb-1">
                    Migration (Y)
                  </label>
                  <input
                    type="number"
                    value={defaultMigration}
                    onChange={(e) => setDefaultMigration(parseInt(e.target.value, 10))}
                    aria-label="Default Migration in years"
                    className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2.5 py-1.5 text-xs text-[var(--text-primary)] num-tabular"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Path-Glob Context Override Rules */}
          <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded-lg p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-[var(--text-primary)] flex items-center gap-2">
                  <Layers className="w-4 h-4 text-[var(--crypto-pqc)]" />
                  <span>Subsystem Path-Glob Context Overrides</span>
                </h2>
                <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                  Assets matching these file-path patterns inherit localized exposure and criticality parameters.
                </p>
              </div>
              <button
                onClick={handleAddRule}
                className="px-2.5 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] text-[var(--text-primary)] text-xs flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                <span>Add Override Rule</span>
              </button>
            </div>

            <div className="space-y-3">
              {rules.map((rule, idx) => {
                const matches = getMatchCount(rule.glob);
                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] grid grid-cols-1 md:grid-cols-12 gap-3 items-center"
                  >
                    {/* Glob Path */}
                    <div className="md:col-span-4">
                      <label className="text-[9px] text-[var(--text-muted)] uppercase block mb-0.5">
                        Path Glob Matcher
                      </label>
                      <input
                        type="text"
                        value={rule.glob}
                        onChange={(e) => {
                          const updated = [...rules];
                          updated[idx] = { ...updated[idx], glob: e.target.value };
                          setRules(updated);
                        }}
                        aria-label={`Rule ${idx + 1} Path Glob Matcher`}
                        className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-xs text-[var(--crypto-pqc)] font-bold font-mono"
                      />
                    </div>

                    {/* Exposure */}
                    <div className="md:col-span-2">
                      <label className="text-[9px] text-[var(--text-muted)] uppercase block mb-0.5">Exposure</label>
                      <select
                        value={rule.exposure}
                        onChange={(e) => {
                          const updated = [...rules];
                          updated[idx] = { ...updated[idx], exposure: e.target.value as any };
                          setRules(updated);
                        }}
                        aria-label={`Rule ${idx + 1} Exposure`}
                        className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-xs text-[var(--text-primary)]"
                      >
                        <option value="external">External</option>
                        <option value="internal">Internal</option>
                        <option value="isolated">Isolated</option>
                        <option value="test">Test</option>
                      </select>
                    </div>

                    {/* Criticality */}
                    <div className="md:col-span-2">
                      <label className="text-[9px] text-[var(--text-muted)] uppercase block mb-0.5">Criticality</label>
                      <select
                        value={rule.criticality}
                        onChange={(e) => {
                          const updated = [...rules];
                          updated[idx] = { ...updated[idx], criticality: e.target.value as any };
                          setRules(updated);
                        }}
                        aria-label={`Rule ${idx + 1} Criticality`}
                        className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-xs text-[var(--text-primary)]"
                      >
                        <option value="mission-critical">Mission-Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                    </div>

                    {/* Shelf Life & Migration */}
                    <div className="md:col-span-2 grid grid-cols-2 gap-1.5">
                      <div>
                        <label className="text-[9px] text-[var(--text-muted)] uppercase block mb-0.5">X (yrs)</label>
                        <input
                          type="number"
                          value={rule.shelfLifeYears}
                          onChange={(e) => {
                            const updated = [...rules];
                            updated[idx] = { ...updated[idx], shelfLifeYears: parseInt(e.target.value, 10) };
                            setRules(updated);
                          }}
                          aria-label={`Rule ${idx + 1} Shelf Life X in years`}
                          className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-1.5 py-1 text-xs text-[var(--text-primary)] num-tabular"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-[var(--text-muted)] uppercase block mb-0.5">Y (yrs)</label>
                        <input
                          type="number"
                          value={rule.migrationYears}
                          onChange={(e) => {
                            const updated = [...rules];
                            updated[idx] = { ...updated[idx], migrationYears: parseInt(e.target.value, 10) };
                            setRules(updated);
                          }}
                          aria-label={`Rule ${idx + 1} Migration Y in years`}
                          className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-1.5 py-1 text-xs text-[var(--text-primary)] num-tabular"
                        />
                      </div>
                    </div>

                    {/* Live Match Count & Remove */}
                    <div className="md:col-span-2 flex items-center justify-between gap-2">
                      <div className="px-2 py-1 rounded bg-[var(--surface-base)] border border-[var(--border-subtle)] text-[10px] text-[var(--text-secondary)]">
                        Matches: <span className="font-bold text-[var(--crypto-pqc)] num-tabular">{matches}</span> assets
                      </div>
                      <button
                        onClick={() => handleRemoveRule(idx)}
                        aria-label={`Delete Rule ${idx + 1}`}
                        className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--band-critical)] hover:bg-[var(--surface-base)]"
                        title="Delete Rule"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
