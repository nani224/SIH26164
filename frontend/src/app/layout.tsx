import type { Metadata } from 'next';
import './globals.css';
import { MswProvider } from '../components/MswProvider';
import { ThemeToggle } from '../components/ThemeToggle';
import Link from 'next/link';
import { Shield, Eye, Layers } from 'lucide-react';

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
      <body className="lattice-bg min-h-screen antialiased selection:bg-[var(--crypto-pqc-bg)] selection:text-[var(--crypto-pqc)]">
        <MswProvider>
          {/* Top Console Navigation Bar */}
          <header className="sticky top-0 z-50 backdrop-blur-md bg-[var(--surface-overlay)] border-b border-[var(--border-subtle)] px-4 py-2.5">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              {/* Left branding */}
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded border border-[var(--crypto-pqc-border)] bg-[var(--crypto-pqc-bg)] text-[var(--crypto-pqc)] shadow-sm">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold tracking-tight text-[var(--text-primary)]">
                      ECDAT
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded border border-[var(--border-prominent)] bg-[var(--surface-raised)] text-[var(--text-secondary)]">
                      NTRO PS SIH26164
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--text-muted)] font-mono">
                    Cipher Observatory · Cryptographic Posture Console
                  </p>
                </div>
              </div>

              {/* Center navigation */}
              <nav className="flex items-center gap-1 font-mono text-xs">
                <Link
                  href="/specimen"
                  className="px-3 py-1.5 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] border border-transparent hover:border-[var(--border-subtle)] transition-all flex items-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
                  <span>SPECIMEN (LOOP F1)</span>
                </Link>
                <Link
                  href="/"
                  className="px-3 py-1.5 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-raised)] border border-transparent hover:border-[var(--border-subtle)] transition-all flex items-center gap-1.5"
                >
                  <Layers className="w-3.5 h-3.5 text-[var(--crypto-safe-classical)]" />
                  <span>SCAN CONSOLE</span>
                </Link>
              </nav>

              {/* Right controls */}
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] font-mono text-[10px] text-[var(--text-muted)]">
                  <span className="w-2 h-2 rounded-full bg-[var(--crypto-pqc)] animate-pulse" />
                  <span>MSW CONTRACT: ACTIVE</span>
                </div>
                <ThemeToggle />
              </div>
            </div>
          </header>

          {/* Main content */}
          <main className="max-w-7xl mx-auto p-4 sm:p-6 md:p-8">
            {children}
          </main>
        </MswProvider>
      </body>
    </html>
  );
}
