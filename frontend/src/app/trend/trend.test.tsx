import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import TrendPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

describe('Screen 12: Estate Cryptographic Trend', () => {
  it('renders trend title, trajectory metrics, and time series chart', async () => {
    renderWithClient(<TrendPage />);

    await waitFor(() => {
      expect(screen.getByText(/Estate Cryptographic Trend/i)).toBeInTheDocument();
      expect(screen.getByText(/Risk Score Velocity/i)).toBeInTheDocument();
      expect(screen.getByText(/Critical Assets Delta/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Findings Delta/i)).toBeInTheDocument();
      expect(screen.getByText(/PQC Horizon Projection/i)).toBeInTheDocument();
    });
  });

  it('renders SVG chart with risk score trajectory and critical findings', async () => {
    renderWithClient(<TrendPage />);

    await waitFor(() => {
      expect(
        screen.getByRole('img', {
          name: /Trend line chart showing risk score and critical findings over time/i,
        })
      ).toBeInTheDocument();
    });
  });

  it('renders daily telemetry log table with snapshot rows', async () => {
    renderWithClient(<TrendPage />);

    await waitFor(() => {
      expect(screen.getByText(/Daily Cryptographic Telemetry Log/i)).toBeInTheDocument();
      expect(screen.getByText('2026-09-20')).toBeInTheDocument();
      expect(screen.getByText('2026-08-22')).toBeInTheDocument();
    });
  });

  it('allows switching time windows (7D, 30D, 90D)', async () => {
    renderWithClient(<TrendPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Show 7 days trend/i })).toBeInTheDocument();
    });

    const btn7d = screen.getByRole('button', { name: /Show 7 days trend/i });
    fireEvent.click(btn7d);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Show 7 days trend/i })).toHaveClass('font-bold');
    });
  });

  it('passes accessibility audits on trend screen', async () => {
    const { container } = renderWithClient(<TrendPage />);

    await waitFor(() => {
      expect(screen.getByText(/Estate Cryptographic Trend/i)).toBeInTheDocument();
    });

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false }, // Verified in real browser E2E test
      },
    });

    const serious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious).toHaveLength(0);
  });
});
