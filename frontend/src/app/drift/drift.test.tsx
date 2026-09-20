import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import DriftPage from './page';
import { renderWithClient } from '../../test/test-utils';
import { useAppStore } from '../../lib/store';
import * as axe from 'axe-core';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn().mockReturnValue('target-001'),
  }),
}));

describe('Screen 13: Cryptographic Drift Analysis', () => {
  it('renders drift title, comparison badges, and summary bento cards', async () => {
    renderWithClient(<DriftPage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Drift Analysis/i)).toBeInTheDocument();
      expect(screen.getByText(/Added Assets/i)).toBeInTheDocument();
      expect(screen.getByText(/Resolved Assets/i)).toBeInTheDocument();
      expect(screen.getByText(/Changed Bands/i)).toBeInTheDocument();
      expect(screen.getByText(/Net Risk Delta/i)).toBeInTheDocument();
    });
  });

  it('renders added, resolved, and changed findings sections', async () => {
    renderWithClient(<DriftPage />);

    await waitFor(() => {
      expect(screen.getByText(/Newly Added Cryptographic Assets/i)).toBeInTheDocument();
      expect(screen.getByText(/Resolved \/ Remediated Assets/i)).toBeInTheDocument();
      expect(screen.getByText(/Changed Severity Postures/i)).toBeInTheDocument();
      expect(screen.getByText('X25519')).toBeInTheDocument();
    });
  });

  it('filters drift items using category tabs', async () => {
    renderWithClient(<DriftPage />);

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /Added/i })).toBeInTheDocument();
    });

    const addedTab = screen.getByRole('tab', { name: /Added/i });
    fireEvent.click(addedTab);

    expect(screen.getByText(/Newly Added Cryptographic Assets/i)).toBeInTheDocument();
    expect(screen.queryByText(/Resolved \/ Remediated Assets/i)).not.toBeInTheDocument();
  });

  it('opens finding drawer when an added finding is clicked', async () => {
    renderWithClient(<DriftPage />);

    await waitFor(() => {
      expect(screen.getByText('X25519')).toBeInTheDocument();
    });

    const row = screen.getByLabelText(/Inspect finding X25519/i);
    fireEvent.click(row);

    const store = useAppStore.getState();
    expect(store.isDrawerOpen).toBe(true);
    expect(store.selectedFinding?.displayName).toBe('X25519');
  });

  it('passes accessibility audits on drift screen', async () => {
    const { container } = renderWithClient(<DriftPage />);

    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Drift Analysis/i)).toBeInTheDocument();
    });

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false }, // Handled in real browser E2E test
      },
    });

    const serious = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    expect(serious).toHaveLength(0);
  });
});
