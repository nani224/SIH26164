import type { Metadata } from 'next';
import './globals.css';
import { MswProvider } from '../components/MswProvider';
import { ThemeToggle } from '../components/ThemeToggle';
import { FindingDrawer } from '../components/FindingDrawer';
import { CommandPalette } from '../components/CommandPalette';
import { CommandPaletteButton } from '../components/CommandPaletteButton';
import Link from 'next/link';
import {
  Shield,
  Eye,
  Layers,
  Terminal,
  Calculator,
  ListFilter,
  Network,
  Grid,
  FileCheck,
  FileText,
  Settings,
  Search,
} from 'lucide-react';

export const metadata: Metadata = {
  title: 'ECDAT — Enterprise Cryptographic Discovery & Analysis Tool',
  description: 'Signals-intelligence cryptographic console for quantum risk assessment (NTRO PS SIH26164)',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="lattice-bg min-h-screen antialiased selection:bg-[var(--crypto-pqc-bg)] selection:text-[var(--crypto-pqc)] text-[var(--text-primary)] bg-[var(--surface-base)]">
        <MswProvider>
          {/* Top Console Navigation Bar */}
          <header className="sticky top-0 z-40 backdrop-blur-md bg-[var(--surface-overlay)] border-b border-[var(--border-subtle)] px-4 py-2">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              {/* Left branding */}
              <div className="flex items-center gap-3">
                <Link href="/overview" className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 rounded border border-[var(--crypto-pqc-border)] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] shadow-sm">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold tracking-tight text-[var(--text-primary)]">
                        ECDAT
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded border border-[var(--border-prominent)] bg-[var(--surface-raised)] text-[var(--text-secondary)]">
                        NTRO SIH26164
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--text-muted)] font-mono">
                      Cipher Observatory
                    </p>
                  </div>
                </Link>
              </div>

              {/* Center navigation */}
              <nav className="hidden lg:flex items-center gap-1 font-mono text-xs">
                <Link
                  href="/overview"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Overview
                </Link>
                <Link
                  href="/launcher"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Launcher
                </Link>
                <Link
                  href="/mosca"
                  className="px-2.5 py-1 rounded text-[var(--crypto-pqc)] font-bold hover:bg-[var(--surface-raised)] transition-all"
                >
                  Mosca Matrix
                </Link>
                <Link
                  href="/inventory"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Inventory
                </Link>
                <Link
                  href="/graph"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  3D Graph
                </Link>
                <Link
                  href="/heatmap"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Heatmap
                </Link>
                <Link
                  href="/certificates"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Certs
                </Link>
                <Link
                  href="/plan"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Plan
                </Link>
                <Link
                  href="/policies"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Policies
                </Link>
                <Link
                  href="/specimen"
                  className="px-2.5 py-1 rounded text-[var(--crypto-grover)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Specimen
                </Link>
              </nav>

              {/* Right controls */}
              <div className="flex items-center gap-2">
                <CommandPaletteButton />
                <ThemeToggle />
              </div>
            </div>
          </header>

          {/* Main content */}
          <main className="max-w-7xl mx-auto p-4 sm:p-6 md:p-8">
            {children}
          </main>

          {/* Global Drawers & Palettes */}
          <FindingDrawer />
          <CommandPalette />
        </MswProvider>
      </body>
    </html>
  );
}
