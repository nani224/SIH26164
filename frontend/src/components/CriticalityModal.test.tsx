import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { CriticalityModal } from './CriticalityModal';
import { mockFindings } from '../mocks/data';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-04 Ext: CriticalityModal (M5 PS-Gap)', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithClient(
      <CriticalityModal isOpen={false} onClose={vi.fn()} findings={mockFindings} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders modal with Criticality Rule Editor tab and inputs', async () => {
    renderWithClient(
      <CriticalityModal isOpen={true} onClose={vi.fn()} findings={mockFindings} />
    );

    expect(screen.getByText(/Business Criticality & Finding Re-ranking/i)).toBeInTheDocument();
    expect(screen.getByText(/Criticality Rule Editor/i)).toBeInTheDocument();
    expect(screen.getByText(/CSV Import & Re-ranking Preview/i)).toBeInTheDocument();

    // Check form inputs exist
    expect(screen.getByLabelText(/Path Pattern/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Business Owner/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Target selection/i)).toBeInTheDocument();
  });

  it('allows switching to CSV Import tab, validating CSV, and showing preview', async () => {
    renderWithClient(
      <CriticalityModal isOpen={true} onClose={vi.fn()} findings={mockFindings} />
    );

    // Click CSV Import tab
    fireEvent.click(screen.getByText(/CSV Import & Re-ranking Preview/i));

    expect(screen.getByText(/Paste CSV Records/i)).toBeInTheDocument();

    // Fill CSV textarea using label
    const textarea = screen.getByLabelText(/Paste CSV Records/i);
    fireEvent.change(textarea, {
      target: {
        value: 'target-001,src/crypto/**,mission-critical,Payment Engineering,PCI-DSS,external\ntarget-002,src/docs/**,low,Internal Docs,PUBLIC,internal',
      },
    });

    // Projected re-ranking preview table appears automatically
    await waitFor(() => {
      expect(screen.getByText(/Projected Finding Re-ranking Impact Preview/i)).toBeInTheDocument();
    });

    // Apply button enabled
    const applyBtn = screen.getByRole('button', { name: /Apply CSV/i });
    expect(applyBtn).toBeEnabled();
  });

  it('displays CSV validation error on invalid criticality value', async () => {
    renderWithClient(
      <CriticalityModal isOpen={true} onClose={vi.fn()} findings={mockFindings} />
    );

    fireEvent.click(screen.getByText(/CSV Import & Re-ranking Preview/i));

    const textarea = screen.getByLabelText(/Paste CSV Records/i);
    fireEvent.change(textarea, {
      target: {
        value: 'target-001,src/**,INVALID_CRITICALITY,Security,RESTRICTED,internal',
      },
    });

    await waitFor(() => {
      expect(screen.getByText(/Invalid criticality "INVALID_CRITICALITY"/i)).toBeInTheDocument();
    });

    const applyBtn = screen.getByRole('button', { name: /Apply CSV/i });
    expect(applyBtn).toBeDisabled();
  });

  it('passes accessibility audits when opened', async () => {
    const { container } = renderWithClient(
      <CriticalityModal isOpen={true} onClose={vi.fn()} findings={mockFindings} />
    );

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false }, // tested in real browser Playwright
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
