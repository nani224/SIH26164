'use client';

import { useState } from 'react';
import { mockFindings } from '../../mocks/data';
import { Settings, Plus, Trash2, Check, Shield, Layers, Save, Sliders } from 'lucide-react';

interface PolicyRuleState {
  id: string;
  glob: string;
  exposure: 'external' | 'internal' | 'isolated' | 'test';
  criticality: 'mission-critical' | 'high' | 'medium' | 'low';
  shelfLifeYears: number;
  migrationYears: number;
}

export default function PolicyEditorPage() {
  const [policyName, setPolicyName] = useState('National Defense Core (CNSA 2.0)');
  const [defaultExposure, setDefaultExposure] = useState<'external' | 'internal' | 'isolated' | 'test'>('internal');
  const [defaultCriticality, setDefaultCriticality] = useState<'mission-critical' | 'high' | 'medium' | 'low'>('high');
  const [defaultShelfLife, setDefaultShelfLife] = useState(10);
  const [defaultMigration, setDefaultMigration] = useState(5);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const [rules, setRules] = useState<PolicyRuleState[]>([
    {
      id: 'rule-1',
      glob: 'configs/**',
      exposure: 'external',
      criticality: 'mission-critical',
      shelfLifeYears: 15,
      migrationYears: 5,
    },
    {
      id: 'rule-2',
      glob: 'certs/**',
      exposure: 'external',
      criticality: 'mission-critical',
      shelfLifeYears: 12,
      migrationYears: 6,
    },
    {
      id: 'rule-3',
      glob: 'storage/**',
      exposure: 'isolated',
      criticality: 'high',
      shelfLifeYears: 20,
      migrationYears: 3,
    },
    {
      id: 'rule-4',
      glob: 'legacy/**',
      exposure: 'internal',
      criticality: 'medium',
      shelfLifeYears: 5,
      migrationYears: 2,
    },
  ]);

  // Live count helper for matching findings by glob
  const getMatchCount = (glob: string) => {
    const prefix = glob.replace('/**', '').replace('/*', '');
    return mockFindings.filter((f) => f.location.path.startsWith(prefix)).length;
  };

  const addRule = () => {
    setRules([
      ...rules,
      {
        id: `rule-${Date.now()}`,
        glob: 'services/**',
        exposure: 'internal',
        criticality: 'high',
        shelfLifeYears: 10,
        migrationYears: 4,
      },
    ]);
  };

  const removeRule = (id: string) => {
    setRules(rules.filter((r) => r.id !== id));
  };

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <div className="space-y-6 font-mono text-xs max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Settings className="w-3.5 h-3.5" />
            <span>SCREEN 10 · CRYPTOGRAPHIC ASSESSMENT POLICY EDITOR</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Mosca Parameter Context Policies
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Path-glob rules defining System Exposure ($E$), Criticality ($K$), Data Shelf Life ($X$), and Migration Time ($Y$).
          </p>
        </div>

        <button
          onClick={handleSave}
          className="px-4 py-2 rounded bg-[var(--crypto-pqc)] text-[var(--surface-base)] font-bold text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5 self-start sm:self-auto"
        >
          {savedSuccess ? (
            <>
              <Check className="w-3.5 h-3.5" />
              <span>SAVED POLICY</span>
            </>
          ) : (
            <>
              <Save className="w-3.5 h-3.5" />
              <span>SAVE & APPLY POLICY</span>
            </>
          )}
        </button>
      </div>

      {/* Policy Meta */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-5 rounded-xl space-y-4">
        <div className="font-bold text-xs uppercase tracking-wider text-[var(--text-primary)]">
          Policy Specification
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Policy Identifier & Name:</label>
            <input
              type="text"
              value={policyName}
              onChange={(e) => setPolicyName(e.target.value)}
              className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-xs text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
            />
          </div>
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Baseline Standard Reference:</label>
            <div className="p-2 bg-[var(--surface-raised)] border border-[var(--border-subtle)] rounded text-[var(--crypto-pqc)] font-bold">
              CNSA 2.0 (NSA) & NIST FIPS 203/204/205
            </div>
          </div>
        </div>
      </div>

      {/* Default Fallback Context */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-5 rounded-xl space-y-4">
        <div className="font-bold text-xs uppercase tracking-wider text-[var(--text-primary)]">
          Default Fallback Context (When no path rule matches)
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Exposure (E):</label>
            <select
              value={defaultExposure}
              onChange={(e) => setDefaultExposure(e.target.value as any)}
              className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
            >
              <option value="external">External (1.0)</option>
              <option value="internal">Internal (0.8)</option>
              <option value="isolated">Isolated (0.5)</option>
              <option value="test">Test / Dev (0.2)</option>
            </select>
          </div>
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Criticality (K):</label>
            <select
              value={defaultCriticality}
              onChange={(e) => setDefaultCriticality(e.target.value as any)}
              className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)]"
            >
              <option value="mission-critical">Mission-Critical (1.0)</option>
              <option value="high">High (0.85)</option>
              <option value="medium">Medium (0.6)</option>
              <option value="low">Low (0.3)</option>
            </select>
          </div>
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Shelf Life (X yrs):</label>
            <input
              type="number"
              value={defaultShelfLife}
              onChange={(e) => setDefaultShelfLife(Number(e.target.value))}
              className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] num-tabular"
            />
          </div>
          <div>
            <label className="text-[var(--text-muted)] block mb-1">Migration Time (Y yrs):</label>
            <input
              type="number"
              value={defaultMigration}
              onChange={(e) => setDefaultMigration(Number(e.target.value))}
              className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-2 text-[var(--text-primary)] num-tabular"
            />
          </div>
        </div>
      </div>

      {/* Path Glob Rules */}
      <div className="bg-[var(--surface-card)] border border-[var(--border-subtle)] p-5 rounded-xl space-y-4">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-3">
          <div className="font-bold text-xs uppercase tracking-wider text-[var(--text-primary)]">
            Path-Glob Context Overrides
          </div>
          <button
            onClick={addRule}
            className="px-2.5 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] hover:border-[var(--crypto-pqc)] text-[var(--text-primary)] flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
            <span>ADD RULE</span>
          </button>
        </div>

        <div className="space-y-3">
          {rules.map((rule, idx) => {
            const matches = getMatchCount(rule.glob);

            return (
              <div
                key={rule.id}
                className="p-3.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center gap-2 flex-1">
                    <span className="text-[var(--text-muted)]">Rule #{idx + 1}:</span>
                    <input
                      type="text"
                      value={rule.glob}
                      onChange={(e) => {
                        const next = [...rules];
                        next[idx].glob = e.target.value;
                        setRules(next);
                      }}
                      className="bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-xs text-[var(--text-primary)] font-bold flex-1 max-w-sm"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] text-[11px] font-bold border border-[var(--crypto-pqc-border)] num-tabular">
                      {matches} finding{matches !== 1 ? 's' : ''} captured
                    </span>
                    <button
                      onClick={() => removeRule(rule.id)}
                      className="p-1 text-[var(--text-muted)] hover:text-[var(--band-critical)] transition-colors"
                      title="Delete Rule"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                  <div>
                    <label className="text-[var(--text-muted)] block mb-0.5">Exposure:</label>
                    <select
                      value={rule.exposure}
                      onChange={(e) => {
                        const next = [...rules];
                        next[idx].exposure = e.target.value as any;
                        setRules(next);
                      }}
                      className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-1.5 text-[var(--text-primary)]"
                    >
                      <option value="external">External</option>
                      <option value="internal">Internal</option>
                      <option value="isolated">Isolated</option>
                      <option value="test">Test / Dev</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[var(--text-muted)] block mb-0.5">Criticality:</label>
                    <select
                      value={rule.criticality}
                      onChange={(e) => {
                        const next = [...rules];
                        next[idx].criticality = e.target.value as any;
                        setRules(next);
                      }}
                      className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-1.5 text-[var(--text-primary)]"
                    >
                      <option value="mission-critical">Mission-Critical</option>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-[var(--text-muted)] block mb-0.5">Shelf Life (X yrs):</label>
                    <input
                      type="number"
                      value={rule.shelfLifeYears}
                      onChange={(e) => {
                        const next = [...rules];
                        next[idx].shelfLifeYears = Number(e.target.value);
                        setRules(next);
                      }}
                      className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-1.5 text-[var(--text-primary)] num-tabular"
                    />
                  </div>

                  <div>
                    <label className="text-[var(--text-muted)] block mb-0.5">Migration (Y yrs):</label>
                    <input
                      type="number"
                      value={rule.migrationYears}
                      onChange={(e) => {
                        const next = [...rules];
                        next[idx].migrationYears = Number(e.target.value);
                        setRules(next);
                      }}
                      className="w-full bg-[var(--surface-base)] border border-[var(--border-subtle)] rounded p-1.5 text-[var(--text-primary)] num-tabular"
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
