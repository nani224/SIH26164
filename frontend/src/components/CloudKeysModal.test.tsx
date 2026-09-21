import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { CloudKeysModal } from './CloudKeysModal';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-04 Ext: CloudKeysModal (M5 PS-Gap)', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithClient(
      <CloudKeysModal isOpen={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders AWS KMS keys with rotation age and overdue indicators', async () => {
    renderWithClient(
      <CloudKeysModal isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText(/Cloud KMS Cryptographic Keys/i)).toBeInTheDocument();

    // Check roadmap notice
    expect(screen.getByText(/AWS KMS via LocalStack is actively supported in v1.0/i)).toBeInTheDocument();

    // Check KMS key content loaded from mocks
    await waitFor(() => {
      expect(screen.getByText(/AES-GCM/i)).toBeInTheDocument();
      expect(screen.getByText(/RSA_4096/i)).toBeInTheDocument();
    });

    // Overdue badge should be present for keys > 365 days
    expect(screen.getAllByText(/ROTATION OVERDUE/i).length).toBeGreaterThan(0);
  });

  it('passes accessibility audits when opened', async () => {
    const { container } = renderWithClient(
      <CloudKeysModal isOpen={true} onClose={vi.fn()} />
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
