import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { BenchmarkModal } from './BenchmarkModal';
import { renderWithClient } from '../test/test-utils';
import * as axe from 'axe-core';

describe('SCR-02 Ext: BenchmarkModal (M6 Proof Surfaces)', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithClient(
      <BenchmarkModal isOpen={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders public benchmark metrics, language matrix, and honest weakness disclosure', () => {
    renderWithClient(
      <BenchmarkModal isOpen={true} onClose={vi.fn()} />
    );

    expect(screen.getByText(/Public Cryptographic Benchmark & Empirical Validation/i)).toBeInTheDocument();
    expect(screen.getByText(/95.83%/i)).toBeInTheDocument();
    expect(screen.getByText(/82.14%/i)).toBeInTheDocument();
    expect(screen.getByText(/94.8%/i)).toBeInTheDocument();
    expect(screen.getAllByText(/ENFORCED/i).length).toBeGreaterThan(0);

    // Verify language entries
    expect(screen.getByText('Rust')).toBeInTheDocument();
    expect(screen.getByText('Go')).toBeInTheDocument();
    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('Java')).toBeInTheDocument();
    expect(screen.getByText('C / C++')).toBeInTheDocument();

    // Verify honest weakness disclosure
    expect(screen.getByText(/Honest Weakness Disclosure & Zero-Hallucination Policy/i)).toBeInTheDocument();
    expect(screen.getByText(/Why C\/C\+\+ recall is 76.0%:/i)).toBeInTheDocument();
  });

  it('passes accessibility audits when opened', async () => {
    const { container } = renderWithClient(
      <BenchmarkModal isOpen={true} onClose={vi.fn()} />
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
