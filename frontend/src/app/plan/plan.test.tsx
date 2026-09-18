import { describe, it, expect } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import MigrationPlanPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-09: Migration Plan Component', () => {
  it('renders migration roadmap header and plan download action', async () => {
    renderWithClient(<MigrationPlanPage />);
    expect(screen.getByText(/SCREEN 9 · POST-QUANTUM MIGRATION ROADMAP/i)).toBeInTheDocument();
    expect(screen.getByText(/Prioritized Cryptographic Remediation Sequence/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /EXPORT PLAN \(JSON\)/i })).toBeInTheDocument();
  });

  it('renders prioritized work package items from query data', async () => {
    renderWithClient(<MigrationPlanPage />);
    await waitFor(() => {
      expect(screen.getByText(/STAGE 1/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on migration plan', async () => {
    const { container } = renderWithClient(<MigrationPlanPage />);
    await waitFor(() => {
      expect(screen.getByText(/STAGE 1/i)).toBeInTheDocument();
    });

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
