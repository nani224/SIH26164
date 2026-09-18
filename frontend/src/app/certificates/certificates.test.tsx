import { describe, it, expect } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import CertificatesPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-08: Certificates Component', () => {
  it('renders certificate & PKI trust discovery overview and metrics', async () => {
    renderWithClient(<CertificatesPage />);
    await waitFor(() => {
      expect(screen.getByText(/SCREEN 8 · X.509 CERTIFICATE TIMELINE & COMPLIANCE/i)).toBeInTheDocument();
      expect(screen.getByText(/Certificate Expiry Horizon vs. CRQC Horizon/i)).toBeInTheDocument();
      expect(screen.getByText(/Exceeds CRQC Horizon/i)).toBeInTheDocument();
      expect(screen.getByText(/Classically Broken Signatures/i)).toBeInTheDocument();
    });
  });

  it('renders certificate table entries with validity and algorithms', async () => {
    renderWithClient(<CertificatesPage />);
    await waitFor(() => {
      expect(screen.getByText(/gateway\.core\.ntro\.internal/i)).toBeInTheDocument();
      expect(screen.getByText(/legacy-vpn\.telecom\.gov\.in/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on certificates inventory', async () => {
    const { container } = renderWithClient(<CertificatesPage />);
    await waitFor(() => {
      expect(screen.getByText(/gateway\.core\.ntro\.internal/i)).toBeInTheDocument();
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
