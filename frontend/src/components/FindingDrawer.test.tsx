import { describe, it, expect, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { FindingDrawer } from './FindingDrawer';
import { useAppStore } from '../lib/store';
import { mockFindings } from '../mocks/data';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-05: Finding Drawer Component', () => {
  beforeEach(() => {
    useAppStore.setState({
      selectedFinding: null,
      isDrawerOpen: false,
    });
  });

  it('renders nothing when drawer is closed', () => {
    const { container } = renderWithClient(<FindingDrawer />);
    expect(container.firstChild).toBeNull();
  });

  it('renders cryptographic details and Mosca parameters when opened', () => {
    useAppStore.getState().openDrawer(mockFindings[0]);
    renderWithClient(<FindingDrawer />);

    expect(screen.getByText(mockFindings[0].displayName)).toBeInTheDocument();
    expect(screen.getByText(/Risk Score Mathematical Waterfall/i)).toBeInTheDocument();
    expect(screen.getByText(/Quantum & Classical Threat Assessment/i)).toBeInTheDocument();
  });

  it('closes drawer on escape key press', async () => {
    useAppStore.getState().openDrawer(mockFindings[0]);
    renderWithClient(<FindingDrawer />);

    expect(screen.getByText(mockFindings[0].displayName)).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(useAppStore.getState().isDrawerOpen).toBe(false);
    });
  });

  it('passes accessibility audits when opened', async () => {
    useAppStore.getState().openDrawer(mockFindings[0]);
    const { container } = renderWithClient(<FindingDrawer />);

    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    const serious = results.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
    expect(serious).toHaveLength(0);
  });
});
