'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAppStore } from '../../lib/store';
import { mockFindings } from '../../mocks/data';
import { MoscaMatrixView } from './MoscaMatrixView';

function MoscaMatrixContent() {
  const { crqcZ, openDrawer } = useAppStore();
  const searchParams = useSearchParams();
  const state = searchParams.get('state');

  if (state === 'empty') {
    return (
      <MoscaMatrixView
        findings={[]}
        initialZ={crqcZ}
        onFindingSelect={openDrawer}
      />
    );
  }

  if (state === 'error') {
    return (
      <MoscaMatrixView
        findings={[]}
        initialZ={crqcZ}
        error="Failed to establish WebSocket link to scanner daemon. Gateway timeout (504)."
        onFindingSelect={openDrawer}
      />
    );
  }

  return (
    <MoscaMatrixView
      findings={mockFindings}
      initialZ={crqcZ}
      onFindingSelect={openDrawer}
    />
  );
}

export default function MoscaMatrixPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center font-mono text-xs text-[var(--text-muted)]">Loading Cipher Observatory...</div>}>
      <MoscaMatrixContent />
    </Suspense>
  );
}

