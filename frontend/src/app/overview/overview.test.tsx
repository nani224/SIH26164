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

  it('renders coverage certificate with mass conservation breakdown and residue CTA', async () => {
    renderWithClient(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/Crypto Mass Coverage/i)).toBeInTheDocument();
      expect(screen.getByTestId('coverage-ratio-metric')).toHaveTextContent('93.5%');
      expect(screen.getByText(/Crypto Mass Conservation Bar/i)).toBeInTheDocument();
      expect(screen.getByText(/8,850/i)).toBeInTheDocument(); // Attributed
      expect(screen.getByText(/650/i)).toBeInTheDocument(); // Residue
      expect(screen.getByText(/7 unexplained crypto residue clusters detected in this scan/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /Review Residue Ledger/i })).toHaveAttribute('href', '/residue');
    });
  });

  it('passes accessibility audits on overview screen', async () => {
    const { container } = renderWithClient(<OverviewPage />);
    await waitFor(() => {
      expect(screen.getByText(/SCREEN 2 · CRYPTOGRAPHIC OVERVIEW CONSOLE/i)).toBeInTheDocument();
      expect(screen.getByText(/Crypto Mass Coverage/i)).toBeInTheDocument();
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
