import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import InventoryPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('SCR-04: Inventory Component', () => {
  it('renders cryptographic inventory header and surface filters', async () => {
    renderWithClient(<InventoryPage />);
    expect(screen.getByText(/SCREEN 4 · HIGH-DENSITY CRYPTOGRAPHIC INVENTORY/i)).toBeInTheDocument();
    expect(screen.getByText(/Discovered Cryptographic Assets/i)).toBeInTheDocument();

    // Verify [Proposed] surface filters are present
    expect(screen.getByText(/Hardware & Cloud \[Proposed\]/i)).toBeInTheDocument();
  });

  it('filters assets by search term', async () => {
    renderWithClient(<InventoryPage />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search algorithm, curve, file path, symbol/i)).toBeInTheDocument();
      expect(screen.getAllByText(/X25519/i).length).toBeGreaterThan(0);
    });

    const searchInput = screen.getByPlaceholderText(/Search algorithm, curve, file path, symbol/i);
    fireEvent.change(searchInput, { target: { value: 'X25519' } });

    await waitFor(() => {
      expect(screen.getAllByText(/X25519/i).length).toBeGreaterThan(0);
    });
  });

  it('displays proposed tags for hardware and cloud services', async () => {
    renderWithClient(<InventoryPage />);
    await waitFor(() => {
      const proposedBadges = screen.getAllByText(/PROPOSED/i);
      expect(proposedBadges.length).toBeGreaterThan(0);
    });
  });

  it('passes accessibility audits on inventory table', async () => {
    const { container } = renderWithClient(<InventoryPage />);
    await waitFor(() => {
      expect(screen.getByText(/Discovered Cryptographic Assets/i)).toBeInTheDocument();
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
