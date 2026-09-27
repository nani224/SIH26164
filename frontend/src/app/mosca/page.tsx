'use client';

import { Suspense, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScanFindings } from '../../lib/api';
import { MoscaMatrixView } from './MoscaMatrixView';
import { UnauthorizedState } from '../../components/UnauthorizedState';
import { isUnauthorizedError } from '../../lib/auth';
import { RefreshCw } from 'lucide-react';

function MoscaMatrixContent() {
  const { activeScanId, crqcZ, openDrawer } = useAppStore();
  const searchParams = useSearchParams();
  const state = searchParams.get('state');

  const { data: findingsData, isLoading, error: queryError, refetch } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
    enabled: state !== 'empty' && state !== 'error',
  });

  const findings = useMemo(() => findingsData?.items ?? [], [findingsData]);

  if (state === 'empty') {
    return (
      <MoscaMatrixView
        findings={[]}
        initialZ={crqcZ}
        scanId={activeScanId}
        onFindingSelect={openDrawer}
      />
    );
  }

  if (state === 'error' || queryError) {
    if (isUnauthorizedError(queryError)) {
      return (
        <UnauthorizedState
          onRetry={() => refetch()}
          context="Screen 3 · Mosca Quantum Risk Matrix"
        />
      );
    }
    return (
      <MoscaMatrixView
        findings={[]}
        initialZ={crqcZ}
        scanId={activeScanId}
        error={
          queryError instanceof Error
            ? queryError.message
            : 'Failed to establish WebSocket link to scanner daemon. Gateway timeout (504).'
        }
        onFindingSelect={openDrawer}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="p-16 text-center font-mono text-xs text-[var(--text-muted)] flex items-center justify-center gap-2">
        <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
        <span>ACQUIRING QUANTUM POSTURE TELEMETRY...</span>
      </div>
    );
  }

  return (
    <MoscaMatrixView
      findings={findings}
      initialZ={crqcZ}
      scanId={activeScanId}
      onFindingSelect={openDrawer}
    />
  );
}

export default function MoscaMatrixPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center font-mono text-xs text-[var(--text-muted)]">
          Loading Cipher Observatory...
        </div>
      }
    >
      <MoscaMatrixContent />
    </Suspense>
  );
}
