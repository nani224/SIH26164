import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';
import { Providers } from '../components/Providers';
import { ThemeToggle } from '../components/ThemeToggle';
import { FindingDrawer } from '../components/FindingDrawer';
import { CommandPalette } from '../components/CommandPalette';
import { AuthSettingsControl } from '../components/AuthSettingsControl';
import { CommandPaletteButton } from '../components/CommandPaletteButton';
import Link from 'next/link';

const ibmPlexSansCondensed = localFont({
  src: [
    {
      path: '../../public/fonts/ibm-plex-sans-condensed-latin-400-normal.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../../public/fonts/ibm-plex-sans-condensed-latin-600-normal.woff2',
      weight: '600',
      style: 'normal',
    },
    {
      path: '../../public/fonts/ibm-plex-sans-condensed-latin-700-normal.woff2',
      weight: '700',
      style: 'normal',
    },
  ],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = localFont({
  src: [
    {
      path: '../../public/fonts/jetbrains-mono-latin-400-normal.woff2',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../../public/fonts/jetbrains-mono-latin-600-normal.woff2',
      weight: '600',
      style: 'normal',
    },
    {
      path: '../../public/fonts/jetbrains-mono-latin-700-normal.woff2',
      weight: '700',
      style: 'normal',
    },
  ],
  variable: '--font-mono',
  display: 'swap',
});
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
      <body className={`${ibmPlexSansCondensed.variable} ${jetbrainsMono.variable} lattice-bg min-h-screen antialiased selection:bg-[var(--crypto-pqc-bg)] selection:text-[var(--crypto-pqc)] text-[var(--text-primary)] bg-[var(--surface-base)] font-sans`}>
        <Providers>
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
              <nav className="hidden lg:flex items-center gap-1 font-mono text-xs" aria-label="Main Navigation">
                <Link
                  href="/overview"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Overview
                </Link>
                <Link
                  href="/estate"
                  className="px-2.5 py-1 rounded text-[var(--crypto-pqc)] font-semibold hover:bg-[var(--surface-raised)] transition-all"
                >
                  Estate
                </Link>
                <Link
                  href="/residue"
                  className="px-2.5 py-1 rounded text-[var(--coverage-residue)] font-semibold hover:bg-[var(--surface-raised)] transition-all"
                >
                  Residue
                </Link>
                <Link
                  href="/trend"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Trend
                </Link>
                <Link
                  href="/drift"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Drift
                </Link>
                <Link
                  href="/alerts"
                  className="px-2.5 py-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Alerts
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
                <AuthSettingsControl />
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
        </Providers>
      </body>
    </html>
  );
}
