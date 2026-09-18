'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../lib/store';
import { fetchScanFindings } from '../lib/api';
import {
  Search,
  Layers,
  Calculator,
  ListFilter,
  Network,
  Grid,
  FileCheck,
  FileText,
  Settings,
  Sun,
  Moon,
  Download,
  Terminal,
} from 'lucide-react';

export function CommandPalette() {
  const router = useRouter();
  const { isCommandPaletteOpen, setCommandPaletteOpen, openDrawer, activeScanId } = useAppStore();
  const [query, setQuery] = useState('');

  const { data: findingsData } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
    enabled: isCommandPaletteOpen,
  });
  const findings = findingsData?.items ?? [];

  // Keyboard shortcut listener: Cmd+K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(!isCommandPaletteOpen);
      }
      if (e.key === 'Escape' && isCommandPaletteOpen) {
        setCommandPaletteOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isCommandPaletteOpen, setCommandPaletteOpen]);

  if (!isCommandPaletteOpen) return null;

  const routes = [
    { label: 'Overview Console', path: '/overview', icon: Layers, tag: 'Screen 2' },
    { label: 'Scan Launcher', path: '/launcher', icon: Terminal, tag: 'Screen 1' },
    { label: 'Mosca Quantum Risk Matrix', path: '/mosca', icon: Calculator, tag: 'Screen 3 (Signature)' },
    { label: 'Cryptographic Inventory', path: '/inventory', icon: ListFilter, tag: 'Screen 4' },
    { label: 'Crypto Estate Graph (3D)', path: '/graph', icon: Network, tag: 'Screen 6' },
    { label: 'Attack Surface Heatmap', path: '/heatmap', icon: Grid, tag: 'Screen 7' },
    { label: 'Certificates Timeline', path: '/certificates', icon: FileCheck, tag: 'Screen 8' },
    { label: 'Remediation Migration Plan', path: '/plan', icon: FileText, tag: 'Screen 9' },
    { label: 'Assessment Policy Editor', path: '/policies', icon: Settings, tag: 'Screen 10' },
    { label: 'Design System Specimen', path: '/specimen', icon: Layers, tag: 'Milestone 1' },
  ];

  const filteredRoutes = routes.filter((r) =>
    r.label.toLowerCase().includes(query.toLowerCase())
  );

  const matchedFindings = findings.filter((f) =>
    f.displayName.toLowerCase().includes(query.toLowerCase()) ||
    f.family.toLowerCase().includes(query.toLowerCase()) ||
    f.location.path.toLowerCase().includes(query.toLowerCase())
  );

  const navigateTo = (path: string) => {
    router.push(path);
    setCommandPaletteOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-20">
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={() => setCommandPaletteOpen(false)}
      />

      <div className="relative mx-auto max-w-xl rounded-xl border border-[var(--border-prominent)] bg-[var(--surface-overlay)] shadow-2xl backdrop-blur-xl overflow-hidden font-mono text-xs">
        {/* Search Input */}
        <div className="flex items-center border-b border-[var(--border-subtle)] px-3 py-3">
          <Search className="w-4 h-4 text-[var(--crypto-pqc)] mr-2 flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search console routes, cryptographic findings, or actions (ESC to close)..."
            className="w-full bg-transparent text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none text-xs"
            autoFocus
          />
          <kbd className="px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)]">
            ESC
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto p-2 space-y-3">
          {/* Navigation Routes */}
          <div>
            <div className="px-2 py-1 text-[10px] text-[var(--text-muted)] uppercase font-semibold">
              Console Routes
            </div>
            <div className="space-y-0.5">
              {filteredRoutes.map((route) => {
                const Icon = route.icon;
                return (
                  <button
                    key={route.path}
                    onClick={() => navigateTo(route.path)}
                    className="w-full flex items-center justify-between px-2.5 py-2 rounded hover:bg-[var(--surface-card-hover)] text-left text-[var(--text-primary)] transition-colors group"
                  >
                    <span className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                      <span>{route.label}</span>
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] group-hover:text-[var(--text-secondary)]">
                      {route.tag}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Finding Quick Matches */}
          {matchedFindings.length > 0 && query.length > 0 && (
            <div className="border-t border-[var(--border-subtle)] pt-2">
              <div className="px-2 py-1 text-[10px] text-[var(--text-muted)] uppercase font-semibold">
                Matching Cryptographic Findings
              </div>
              <div className="space-y-0.5">
                {matchedFindings.slice(0, 5).map((f) => (
                  <button
                    key={f.id}
                    onClick={() => {
                      openDrawer(f);
                      setCommandPaletteOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-2 rounded hover:bg-[var(--surface-card-hover)] text-left text-[var(--text-primary)] transition-colors"
                  >
                    <div>
                      <span className="font-bold text-[var(--crypto-pqc)]">{f.displayName}</span>
                      <span className="text-[var(--text-muted)] ml-2">in {f.location.path}:{f.location.line}</span>
                    </div>
                    <span className="text-[10px] uppercase font-bold text-[var(--band-critical)]">
                      Score {f.risk.score.toFixed(1)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
