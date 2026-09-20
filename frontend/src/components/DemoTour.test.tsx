import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { DemoTour, TOUR_STEPS } from './DemoTour';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => '/estate',
}));

describe('7-Minute Guided Demo Tour Component', () => {
  it('renders tour launch button', () => {
    renderWithClient(<DemoTour />);
    expect(screen.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i })).toBeInTheDocument();
  });

  it('opens tour controller when button is clicked and displays step 1 notes', async () => {
    renderWithClient(<DemoTour />);
    const tourBtn = screen.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i });
    fireEvent.click(tourBtn);

    expect(screen.getByRole('complementary', { name: /7-Minute Guided Demo Tour Controller/i })).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 14 · Screen 11/i)).toBeInTheDocument();
    expect(screen.getByText(/Autonomous Telemetry & Cryptographic Estate/i)).toBeInTheDocument();
    expect(screen.getByText(/Key Presentation Evidence:/i)).toBeInTheDocument();
  });

  it('advances through steps with Next and Prev controls', async () => {
    renderWithClient(<DemoTour />);
    const tourBtn = screen.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i });
    fireEvent.click(tourBtn);

    // Click Next
    const nextBtn = screen.getByRole('button', { name: /Next/i });
    fireEvent.click(nextBtn);

    // Verify step 2 (Trend)
    expect(screen.getByText(/Step 2 of 14 · Screen 12/i)).toBeInTheDocument();
    expect(screen.getByText(/Dual-Axis Historical Risk & Critical Findings/i)).toBeInTheDocument();
    expect(mockPush).toHaveBeenCalledWith('/trend');

    // Click Prev
    const prevBtn = screen.getByRole('button', { name: /Prev/i });
    fireEvent.click(prevBtn);

    // Verify back to step 1
    expect(screen.getByText(/Step 1 of 14 · Screen 11/i)).toBeInTheDocument();
  });

  it('allows quick jumping to any of the 14 screens', async () => {
    renderWithClient(<DemoTour />);
    const tourBtn = screen.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i });
    fireEvent.click(tourBtn);

    const select = screen.getByRole('combobox', { name: /Jump to tour step/i });
    fireEvent.change(select, { target: { value: '6' } }); // Step 7: Mosca Matrix

    expect(screen.getByText(/Step 7 of 14 · Screen 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Mosca Quantum Risk Modeling/i)).toBeInTheDocument();
    expect(mockPush).toHaveBeenCalledWith('/mosca');
  });

  it('passes accessibility audits when tour controller is opened', async () => {
    const { container } = renderWithClient(<DemoTour />);
    const tourBtn = screen.getByRole('button', { name: /Start 7-Minute Guided Demo Tour/i });
    fireEvent.click(tourBtn);

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false }, // Verified via real browser E2E test
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
