import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { AttestationModal } from './AttestationModal';
import { mockCoverageCertificate } from '../mocks/data';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-02 Ext: AttestationModal (M6 Proof Surfaces)', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithClient(
      <AttestationModal isOpen={false} onClose={vi.fn()} certificate={mockCoverageCertificate} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders CBOM digest, run manifest, and bound coverage certificate', () => {
    renderWithClient(
      <AttestationModal isOpen={true} onClose={vi.fn()} certificate={mockCoverageCertificate} scanId="scan-001" />
    );

    expect(screen.getByText(/Cryptographic Attestation & Evidence Proof/i)).toBeInTheDocument();
    expect(screen.getByText(/Run Manifest Metadata/i)).toBeInTheDocument();
    expect(screen.getByText(/CBOM 1.6 Cryptographic Digest/i)).toBeInTheDocument();
    expect(screen.getByText(/Bound Coverage Certificate Evidence/i)).toBeInTheDocument();

    // Verify digest and coverage numbers from certificate (0.935 -> 93.5%)
    expect(screen.getByText(/sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855/i)).toBeInTheDocument();
    expect(screen.getByText(/93.5% Coverage Ratio/i)).toBeInTheDocument();
    expect(screen.getByText(/Ed25519 Signed/i)).toBeInTheDocument();
  });

  it('verifies cryptographic digest on button click', async () => {
    renderWithClient(
      <AttestationModal isOpen={true} onClose={vi.fn()} certificate={mockCoverageCertificate} scanId="scan-001" />
    );

    const verifyBtn = screen.getByRole('button', { name: /Verify Cryptographic Digest/i });
    expect(verifyBtn).toBeInTheDocument();
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic digest matches CBOM 1.6 manifest/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits when opened', async () => {
    const { container } = renderWithClient(
      <AttestationModal isOpen={true} onClose={vi.fn()} certificate={mockCoverageCertificate} />
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
