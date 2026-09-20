import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import AlertsPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

describe('Screen 14: Security Alerts & Protocol Probes', () => {
  it('renders alerts title, telemetry metrics, and bento summary cards', async () => {
    renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
      expect(screen.getAllByText(/Active Alerts/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Critical Alerts/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Probe Downgrades/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders alert items from API feed with severity and type badges', async () => {
    renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/New classical Shor-vulnerable RSA-2048 key detected in configs\/sshd_config/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Active probe detected cipher suite downgrade to TLS_RSA_WITH_AES_128_CBC_SHA/i)
      ).toBeInTheDocument();
    });
  });

  it('renders active protocol probes panel with NEGOTIATED and SUPPORTED badges', async () => {
    renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText('api.payments.internal:443')).toBeInTheDocument();
      expect(screen.getAllByText('NEGOTIATED').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('SUPPORTED').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('filters alerts by status tabs (Active, Acknowledged, All)', async () => {
    renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Acknowledged/i })).toBeInTheDocument();
    });

    const ackBtn = screen.getByRole('button', { name: /Acknowledged/i });
    fireEvent.click(ackBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Drift detected: 1 new algorithm added, 1 algorithm migrated to PQC/i)
      ).toBeInTheDocument();
    });
  });

  it('allows acknowledging an active alert', async () => {
    renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Acknowledge alert alt-001/i })).toBeInTheDocument();
    });

    const ackBtn = screen.getByRole('button', { name: /Acknowledge alert alt-001/i });
    fireEvent.click(ackBtn);

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Acknowledge alert alt-001/i })).not.toBeInTheDocument();
    });
  });

  it('passes accessibility audits on alerts screen', async () => {
    const { container } = renderWithClient(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Security Alerts & Protocol Probes/i)).toBeInTheDocument();
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
