import { describe, it, expect } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import PolicyEditorPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-10: Policy Editor Component', () => {
  it('renders cryptographic policy editor and parameters', async () => {
    renderWithClient(<PolicyEditorPage />);
    expect(screen.getByText(/SCREEN 10 · CRYPTOGRAPHIC POLICY & MOSCA CONTEXT ENGINE/i)).toBeInTheDocument();
    expect(screen.getByText(/Policy Contexts & Path Matchers/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /COMMIT POLICY/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Default Baseline Policy Parameters/i)).toBeInTheDocument();
    });
  });

  it('saves policy modifications when clicking commit button', async () => {
    renderWithClient(<PolicyEditorPage />);
    await waitFor(() => {
      expect(screen.getByDisplayValue(/National Defense Core/i)).toBeInTheDocument();
    });

    const saveButton = screen.getByRole('button', { name: /COMMIT POLICY/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/COMMITTED TO API/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility audits on policy editor', async () => {
    const { container } = renderWithClient(<PolicyEditorPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /COMMIT POLICY/i })).toBeInTheDocument();
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
