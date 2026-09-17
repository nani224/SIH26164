'use client';

import { Search } from 'lucide-react';
import { useAppStore } from '../lib/store';

export function CommandPaletteButton() {
  const { toggleCommandPalette } = useAppStore();

  return (
    <button
      onClick={toggleCommandPalette}
      className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] font-mono text-[11px] transition-colors"
      title="Search console (⌘K or Ctrl+K)"
      aria-label="Open command search"
    >
      <Search className="w-3 h-3 text-[var(--crypto-pqc)]" />
      <span>Search</span>
      <kbd className="text-[9px] bg-[var(--surface-card)] px-1 rounded border border-[var(--border-subtle)]">
        ⌘K
      </kbd>
    </button>
  );
}
