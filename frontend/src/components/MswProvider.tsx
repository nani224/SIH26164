'use client';

import { useEffect, useState, type ReactNode } from 'react';

export function MswProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    async function initMsw() {
      // In air-gapped / standalone frontend development, enable MSW unless explicitly disabled
      if (process.env.NEXT_PUBLIC_ENABLE_MSW === 'false') {
        setReady(true);
        return;
      }

      if (typeof window !== 'undefined') {
        const { worker } = await import('../mocks/browser');
        if (worker) {
          try {
            await worker.start({
              onUnhandledRequest: 'bypass',
            });
          } catch (e) {
            console.warn('[MSW] Worker initialization warning:', e);
          }
        }
      }
      setReady(true);
    }

    initMsw();
  }, []);

  if (!ready) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[var(--surface-base)] text-[var(--text-muted)] font-mono text-sm">
        <div className="flex items-center space-x-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--crypto-pqc)] border-t-transparent" />
          <span>INITIALIZING CIPHER OBSERVATORY MSW...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
