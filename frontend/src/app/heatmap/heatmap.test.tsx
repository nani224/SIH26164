import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import HeatmapPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('SCR-07: Heatmap Component', () => {
  it('renders attack surface × cryptographic family exposure matrix', async () => {
    renderWithClient(<HeatmapPage />);
    expect(screen.getByText(/SCREEN 7 · ATTACK SURFACE × CRYPTOGRAPHIC FAMILY HEATMAP/i)).toBeInTheDocument();
    expect(screen.getByText(/Cryptographic Exposure Matrix/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /RSA/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /ECDH/i })).toBeInTheDocument();
    });
  });

  it('navigates to inventory with filters upon cell click', async () => {
    renderWithClient(<HeatmapPage />);
    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument();
    });

    const buttons = await screen.findAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
    fireEvent.click(buttons[0]);
    expect(mockPush).toHaveBeenCalledWith(expect.stringContaining('/inventory?surface='));
  });

  it('passes accessibility audits on exposure table', async () => {
    const { container } = renderWithClient(<HeatmapPage />);
    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Exposure Matrix/i)).toBeInTheDocument();
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
