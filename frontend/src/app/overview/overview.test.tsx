import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import OverviewPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('SCR-02: Overview Component', () => {
  it('renders executive cryptographic summary and metric cards', async () => {
    renderWithClient(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE/i)).toBeInTheDocument();
      expect(screen.getByText(/Critical Risks/i)).toBeInTheDocument();
      expect(screen.getByText(/HNDL Active/i)).toBeInTheDocument();
      expect(screen.getByText(/Broken Today/i)).toBeInTheDocument();
    });
  });

  it('renders top risk items from query data', async () => {
    renderWithClient(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/Highest Urgency Cryptographic Assets/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on overview screen', async () => {
    const { container } = renderWithClient(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE/i)).toBeInTheDocument();
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
