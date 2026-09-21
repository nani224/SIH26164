import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../test/setup';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

import OverviewPage from './overview/page';
import ScanLauncherPage from './launcher/page';
import { AuthSettingsControl } from '../components/AuthSettingsControl';
import { UnauthorizedState } from '../components/UnauthorizedState';
import { setApiToken, setActor, getApiToken, getActor } from '../lib/auth';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

describe('Authentication & 401 Designed State Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    setApiToken('ecdat-dev-insecure-token');
    setActor('ecdat-operator');
  });

  it('renders designed 401 state on Overview screen when unauthorized', async () => {
    server.use(
      http.get('/api/v1/scans/:id', () => {
        return HttpResponse.json(
          { error: 'HTTPException', message: 'Unauthorized' },
          { status: 401, headers: { 'WWW-Authenticate': 'Bearer' } }
        );
      })
    );

    renderWithClient(<OverviewPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /API Authentication Required/i })).toBeInTheDocument();
      expect(screen.getAllByText(/HTTP 401/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('button', { name: /Configure API Token/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry Connection/i })).toBeInTheDocument();
    });
  });

  it('renders designed 401 state on Scan Launcher screen when unauthorized', async () => {
    server.use(
      http.get('/api/v1/policies', () => {
        return HttpResponse.json(
          { error: 'HTTPException', message: 'Unauthorized' },
          { status: 401, headers: { 'WWW-Authenticate': 'Bearer' } }
        );
      })
    );

    renderWithClient(<ScanLauncherPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /API Authentication Required/i })).toBeInTheDocument();
      expect(screen.getAllByText(/HTTP 401/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('button', { name: /Configure API Token/i })).toBeInTheDocument();
    });
  });

  it('opens AuthSettingsControl modal when clicking Configure Token button', async () => {
    renderWithClient(
      <div>
        <AuthSettingsControl />
        <UnauthorizedState context="Test Context" />
      </div>
    );

    const configureBtn = screen.getByRole('button', { name: /CONFIGURE.*TOKEN/i });
    fireEvent.click(configureBtn);

    await waitFor(() => {
      expect(screen.getByText(/API Authentication & Actor Identity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/API Bearer Token/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Operator Identity/i)).toBeInTheDocument();
    });
  });

  it('allows updating token and actor identity in AuthSettingsControl', async () => {
    renderWithClient(<AuthSettingsControl />);

    const openBtn = screen.getByRole('button', { name: /API Authentication and Identity Settings/i });
    fireEvent.click(openBtn);

    await waitFor(() => {
      expect(screen.getByLabelText(/API Bearer Token/i)).toBeInTheDocument();
    });

    const tokenInput = screen.getByLabelText(/API Bearer Token/i);
    const actorInput = screen.getByLabelText(/Operator Identity/i);

    fireEvent.change(tokenInput, { target: { value: 'custom-secret-token-xyz' } });
    fireEvent.change(actorInput, { target: { value: 'lead-cryptographer' } });

    const saveBtn = screen.getByRole('button', { name: /SAVE & APPLY/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(getApiToken()).toBe('custom-secret-token-xyz');
      expect(getActor()).toBe('lead-cryptographer');
    });
  });

  it('passes accessibility audits on 401 state in both light and dark themes', async () => {
    const { container } = renderWithClient(
      <div id="test-root" data-theme="dark">
        <UnauthorizedState context="Screen 2 · Cryptographic Overview Console" />
      </div>
    );

    // Dark theme audit
    let results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    let serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);

    // Light theme audit
    const root = container.querySelector('#test-root');
    root?.setAttribute('data-theme', 'light');

    results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
