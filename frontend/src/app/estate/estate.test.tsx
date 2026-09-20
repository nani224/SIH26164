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

  it('renders CI/CD pipeline surfaces with honest roadmap annotations', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Estate Console/i)).toBeInTheDocument();
      expect(screen.getAllByText(/GitHub Actions/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/GitLab CI Runner/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Roadmap/i).length).toBeGreaterThanOrEqual(2);
    }, { timeout: 4000 });
  });

  it('renders cryptographic audit hash-chain integrity verification seal', async () => {
    renderWithClient(<EstatePage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Estate Console/i)).toBeInTheDocument();
      expect(screen.getByTestId('audit-verify-control')).toBeInTheDocument();
      expect(screen.getByText(/Audit Log Hash-Chain Integrity/i)).toBeInTheDocument();
      expect(screen.getByText(/CHAIN VALID/i)).toBeInTheDocument();
      expect(screen.getByText(/1,248/i)).toBeInTheDocument();
    }, { timeout: 4000 });
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
