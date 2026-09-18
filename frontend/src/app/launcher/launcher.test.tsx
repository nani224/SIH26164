import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import ScanLauncherPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

describe('SCR-01: Scan Launcher Component', () => {
  it('renders target ingestion dropzone and parameters', () => {
    renderWithClient(<ScanLauncherPage />);
    expect(screen.getByText(/SCREEN 1 · CRYPTOGRAPHIC SCAN LAUNCHER/i)).toBeInTheDocument();
    expect(screen.getByText(/Target Ingestion & Assessment Setup/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag and drop bundle archive or binary target/i)).toBeInTheDocument();
    expect(screen.getByText(/Assessment Parameters/i)).toBeInTheDocument();
  });

  it('allows changing policy and CRQC slider values', () => {
    renderWithClient(<ScanLauncherPage />);
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'policy-telecom-critical' } });
    expect(select).toHaveValue('policy-telecom-critical');

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '12' } });
    expect(screen.getByText(/12 YEARS/i)).toBeInTheDocument();
  });

  it('triggers enterprise scan execution upon clicking launch button', async () => {
    renderWithClient(<ScanLauncherPage />);
    const launchButton = screen.getByRole('button', { name: /START ENTERPRISE SCAN/i });
    expect(launchButton).toBeInTheDocument();

    fireEvent.click(launchButton);

    await waitFor(() => {
      expect(screen.getByText(/OPEN SCAN OVERVIEW CONSOLE/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on launcher interface', async () => {
    const { container } = renderWithClient(<ScanLauncherPage />);
    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
