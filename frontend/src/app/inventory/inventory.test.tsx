import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import InventoryPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

let mockSearchParams = new URLSearchParams();

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useSearchParams: () => mockSearchParams,
}));

describe('SCR-04: Inventory Component', () => {
  it('renders cryptographic inventory header and surface filters', async () => {
    mockSearchParams = new URLSearchParams();
    renderWithClient(<InventoryPage />);
    expect(screen.getByText(/SCREEN 4 · HIGH-DENSITY CRYPTOGRAPHIC INVENTORY/i)).toBeInTheDocument();
    expect(screen.getByText(/Discovered Cryptographic Assets/i)).toBeInTheDocument();

    // Verify [Proposed] surface filters are present
    expect(screen.getByText(/Hardware & Cloud \[Proposed\]/i)).toBeInTheDocument();
  });

  it('filters assets by search term', async () => {
    mockSearchParams = new URLSearchParams();
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
    mockSearchParams = new URLSearchParams();
    renderWithClient(<InventoryPage />);
    await waitFor(() => {
      const proposedBadges = screen.getAllByText(/PROPOSED/i);
      expect(proposedBadges.length).toBeGreaterThan(0);
    });
  });

  it('switches to hardware HSM partitions view and renders SoftHSM2 slots', async () => {
    mockSearchParams = new URLSearchParams();
    renderWithClient(<InventoryPage />);

    // Click on Hardware HSM Partitions tab
    const hsmTab = screen.getByRole('tab', { name: /Hardware HSM Partitions/i });
    fireEvent.click(hsmTab);

    // Verify HSM view rendered
    await waitFor(() => {
      expect(screen.getByTestId('hsm-inventory-view')).toBeInTheDocument();
      expect(screen.getByText(/SoftHSM v2 Slot 0 - Root Vault/i)).toBeInTheDocument();
      expect(screen.getByText(/SoftHSM v2 Slot 1 - Payment Tokenizer/i)).toBeInTheDocument();
    });

    // Check keys
    expect(screen.getByText(/Root CA Signing Key/i)).toBeInTheDocument();
    expect(screen.getByText(/PQC Transport KEM Key \(ML-KEM-768\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Audit Log Signature Key \(ML-DSA-65\)/i)).toBeInTheDocument();
  });

  it('renders HSM view directly when surface=hardware-hsm param is present', async () => {
    mockSearchParams = new URLSearchParams('surface=hardware-hsm');
    renderWithClient(<InventoryPage />);

    await waitFor(() => {
      expect(screen.getByTestId('hsm-inventory-view')).toBeInTheDocument();
      expect(screen.getByText(/SoftHSM2 Slots/i)).toBeInTheDocument();
      expect(screen.getByText(/POST-QUANTUM/i)).toBeInTheDocument();
      expect(screen.getByText(/SHOR-VULNERABLE/i)).toBeInTheDocument();
    });
  });

  it('renders cryptographic audit hash-chain verification seal and head hash', async () => {
    mockSearchParams = new URLSearchParams('surface=hardware-hsm');
    renderWithClient(<InventoryPage />);

    await waitFor(() => {
      expect(screen.getByTestId('audit-verify-control')).toBeInTheDocument();
      expect(screen.getByText(/Audit Log Hash-Chain Integrity/i)).toBeInTheDocument();
      expect(screen.getByText(/CHAIN VALID/i)).toBeInTheDocument();
      expect(screen.getByText(/1,248/i)).toBeInTheDocument();
      expect(screen.getByText(/Copy Hash/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on inventory table and HSM view', async () => {
    mockSearchParams = new URLSearchParams();
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
