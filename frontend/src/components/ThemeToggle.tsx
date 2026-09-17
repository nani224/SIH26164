'use client';

import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    // Default to dark mode for signals-intelligence console
    const saved = localStorage.getItem('ecdat-theme');
    if (saved === 'light') {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    } else {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggle = () => {
    const next = !isDark;
    setIsDark(next);
    if (next) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('ecdat-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('ecdat-theme', 'light');
    }
  };

  return (
    <button
      onClick={toggle}
      className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded text-xs font-mono border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:bg-[var(--surface-card-hover)] text-[var(--text-secondary)] transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--border-focus)]"
      title={`Switch to ${isDark ? 'Light (Cipher Clean Room)' : 'Dark (Observatory Deep Void)'}`}
      aria-label="Toggle visual theme"
    >
      {isDark ? (
        <>
          <Moon className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
          <span>OBSERVATORY DARK</span>
        </>
      ) : (
        <>
          <Sun className="w-3.5 h-3.5 text-[var(--crypto-grover)]" />
          <span>CLEAN ROOM LIGHT</span>
        </>
      )}
    </button>
  );
}
