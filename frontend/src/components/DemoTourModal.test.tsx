import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { DemoTourModal } from './DemoTourModal';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('SCR-02 Ext: DemoTourModal (M6 Demo Mode v3)', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithClient(
      <DemoTourModal isOpen={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders step 1 and navigates through tour steps', () => {
    renderWithClient(
      <DemoTourModal isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText(/ECDAT v1.0 Guided Product Tour/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 8/i)).toBeInTheDocument();
    expect(screen.getByText(/1. Blocked PR via CI Precision Gate/i)).toBeInTheDocument();

    // Click Next
    const nextBtn = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextBtn);

    expect(screen.getByText(/Step 2 of 8/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Unprompted Scheduled Scan/i)).toBeInTheDocument();

    // Click Previous
    const prevBtn = screen.getByRole('button', { name: /Previous/i });
    fireEvent.click(prevBtn);

    expect(screen.getByText(/Step 1 of 8/i)).toBeInTheDocument();
  });

  it('passes accessibility audits when opened', async () => {
    const { container } = renderWithClient(
      <DemoTourModal isOpen={true} onClose={vi.fn()} />
    );

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
