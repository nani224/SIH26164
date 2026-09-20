import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import EstatePage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe('Screen 11: Continuous Estate Console', () => {
  it('renders estate console title, telemetry badge, and bento metric cards', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Estate Console/i)).toBeInTheDocument();
      expect(screen.getByText(/Continuous Operation Monitor/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Targets/i)).toBeInTheDocument();
      expect(screen.getByText(/Total Scans/i)).toBeInTheDocument();
      expect(screen.getByText(/PQC Readiness/i)).toBeInTheDocument();
      expect(screen.getByText(/Active Alerts/i)).toBeInTheDocument();
    });
  });

  it('renders monitored targets table with data from API', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText('Core Payment Gateway')).toBeInTheDocument();
      expect(screen.getByText('Gateway Firmware Binary')).toBeInTheDocument();
      expect(screen.getByText('Production Ingress TLS')).toBeInTheDocument();
    });
  });

  it('filters targets by search query', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText('Core Payment Gateway')).toBeInTheDocument();
    });

    const searchInput = screen.getByLabelText(/Search targets/i);
    fireEvent.change(searchInput, { target: { value: 'Payment' } });

    expect(screen.getByText('Core Payment Gateway')).toBeInTheDocument();
    expect(screen.queryByText('Gateway Firmware Binary')).not.toBeInTheDocument();
  });

  it('opens register target modal on button click', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Register Target/i })).toBeInTheDocument();
    });

    const registerBtn = screen.getByRole('button', { name: /Register Target/i });
    fireEvent.click(registerBtn);

    expect(screen.getByRole('dialog', { name: /Register Cryptographic Target/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. Core Payment Gateway/i)).toBeInTheDocument();
  });

  it('passes accessibility audits on estate console screen', async () => {
    const { container } = renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Estate Console/i)).toBeInTheDocument();
    });

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false }, // Handled in real-browser E2E suite
      },
    });

    const serious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious).toHaveLength(0);
  });
});
