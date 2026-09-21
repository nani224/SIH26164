import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import ResidueExplorerPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('SCR-16: Residue Explorer & Debt Ledger (M2 & M3)', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it('renders screen header, aggregate stats, and cluster list', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getByText(/Residue Explorer & Debt Ledger/i)).toBeInTheDocument();
      expect(screen.getByText(/Screen 16/i)).toBeInTheDocument();
      expect(screen.getByText(/Open Debt Mass:/i)).toBeInTheDocument();
      expect(screen.getAllByText(/cluster-res-001/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/cluster-res-002/i)[0]).toBeInTheDocument();
      expect(screen.getAllByText(/cluster-res-003/i)[0]).toBeInTheDocument();
    });
  });

  it('displays cluster details, firing extractor signals, and exact range code preview', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-001/i)[0]).toBeInTheDocument();
    });

    // Verify detail view for active cluster (first cluster by default)
    expect(screen.getByText(/Firing Extractor Signals/i)).toBeInTheDocument();
    expect(screen.getAllByText('constant_pool')[0]).toBeInTheDocument();
    expect(screen.getAllByText('entropy')[0]).toBeInTheDocument();
    expect(screen.getAllByText(/src\/crypto\/handshake\.c/i)[0]).toBeInTheDocument();

    // Verify exact byte/AST range code preview
    expect(screen.getByText(/Exact range match \[120:185\]/i)).toBeInTheDocument();
    expect(screen.getByText(/Extractor Signal Fired: constant_pool/i)).toBeInTheDocument();
  });

  it('enforces justification AND owner before enabling cluster exclusion in debt workflow', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-001/i)[0]).toBeInTheDocument();
    });

    // Click "Exclude Cluster" tab
    const excludeTabBtn = screen.getByRole('button', { name: /^Exclude Cluster$/i });
    fireEvent.click(excludeTabBtn);

    // Verify exclusion form is open
    expect(screen.getByText(/Exclude Cluster from Active Debt/i)).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /Confirm Exclusion/i });
    // Button MUST be disabled initially
    expect(confirmBtn).toBeDisabled();

    // Fill in only owner -> should still be disabled
    const ownerInput = screen.getByLabelText(/Accountable Owner \*/i);
    fireEvent.change(ownerInput, { target: { value: 'secops-team' } });
    expect(confirmBtn).toBeDisabled();

    // Fill in justification -> now enabled
    const justInput = screen.getByLabelText(/Technical Justification \*/i);
    fireEvent.change(justInput, { target: { value: 'Verified non-cryptographic pseudo-random seed table' } });
    expect(confirmBtn).toBeEnabled();

    // Submit exclusion
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cluster successfully updated to EXCLUDED/i)).toBeInTheDocument();
    });
  });

  it('supports promote to rule with engine scaffold preview', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-001/i)[0]).toBeInTheDocument();
    });

    // Click "Promote to Rule" tab
    const promoteTabBtn = screen.getByRole('button', { name: /^Promote to Rule$/i });
    fireEvent.click(promoteTabBtn);

    // Verify scaffold preview
    expect(screen.getByText(/Generated Rule Scaffold/i)).toBeInTheDocument();
    expect(screen.getByText(/ecdat-rule-cluster-/i)).toBeInTheDocument();
    expect(screen.getByText(/Copy YAML/i)).toBeInTheDocument();

    // Click confirm promotion
    const confirmPromoteBtn = screen.getByRole('button', { name: /Confirm Promotion to Engine Rule/i });
    fireEvent.click(confirmPromoteBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cluster successfully updated to PROMOTED/i)).toBeInTheDocument();
    });
  });

  it('supports accepting risk requiring operational reason on open cluster', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-002/i)[0]).toBeInTheDocument();
    });

    // Select open cluster-res-002
    fireEvent.click(screen.getAllByText(/cluster-res-002/i)[0]);

    // Click "Accept Risk" tab
    const acceptTabBtn = screen.getByRole('button', { name: /^Accept Risk$/i });
    fireEvent.click(acceptTabBtn);

    expect(screen.getByText(/Accept Residual Cryptographic Risk/i)).toBeInTheDocument();
    const confirmBtn = screen.getByRole('button', { name: /Confirm Accepted Risk/i });
    expect(confirmBtn).toBeDisabled();

    const reasonInput = screen.getByLabelText(/Operational Reason \*/i);
    fireEvent.change(reasonInput, { target: { value: 'Legacy test fixture known residue' } });
    expect(confirmBtn).toBeEnabled();

    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cluster successfully updated to ACCEPTED/i)).toBeInTheDocument();
    });
  });

  it('filters clusters by state and search query', async () => {
    renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-001/i)[0]).toBeInTheDocument();
    });

    // Filter by accepted state
    const stateFilter = screen.getByLabelText(/Ledger State/i);
    fireEvent.change(stateFilter, { target: { value: 'accepted' } });

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-003/i)[0]).toBeInTheDocument();
      expect(screen.queryByText(/cluster-res-001/i)).not.toBeInTheDocument();
    });

    // Reset to all and search
    fireEvent.change(stateFilter, { target: { value: 'all' } });
    const searchInput = screen.getByPlaceholderText(/Search clusters by ID/i);
    fireEvent.change(searchInput, { target: { value: 'asn1_parser' } });

    await waitFor(() => {
      expect(screen.getAllByText(/cluster-res-003/i)[0]).toBeInTheDocument();
      expect(screen.queryByText(/cluster-res-001/i)).not.toBeInTheDocument();
    });
  });

  it('passes accessibility audits on residue explorer screen', async () => {
    const { container } = renderWithClient(<ResidueExplorerPage />);

    await waitFor(() => {
      expect(screen.getByText(/Residue Explorer & Debt Ledger/i)).toBeInTheDocument();
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
