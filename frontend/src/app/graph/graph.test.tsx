import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import CryptoEstateGraphPage from './page';
import { renderWithClient } from '../../test/test-utils';
import * as axe from 'axe-core';

// Mock Three.js to prevent WebGL context errors in JSDOM
vi.mock('three', () => {
  return {
    Scene: vi.fn().mockImplementation(() => ({
      background: null,
      add: vi.fn(),
      rotation: { x: 0, y: 0 },
    })),
    Color: vi.fn(),
    PerspectiveCamera: vi.fn().mockImplementation(() => ({
      position: { z: 0 },
    })),
    WebGLRenderer: vi.fn().mockImplementation(() => ({
      setSize: vi.fn(),
      setPixelRatio: vi.fn(),
      render: vi.fn(),
      dispose: vi.fn(),
    })),
    AmbientLight: vi.fn(),
    PointLight: vi.fn().mockImplementation(() => ({
      position: { set: vi.fn() },
    })),
    SphereGeometry: vi.fn(),
    MeshStandardMaterial: vi.fn(),
    Mesh: vi.fn().mockImplementation(() => ({
      position: { set: vi.fn() },
    })),
    LineBasicMaterial: vi.fn(),
    BufferGeometry: vi.fn().mockImplementation(() => ({
      setFromPoints: vi.fn(),
    })),
    Vector3: vi.fn(),
    Line: vi.fn(),
    Raycaster: vi.fn().mockImplementation(() => ({
      setFromCamera: vi.fn(),
      intersectObjects: vi.fn().mockReturnValue([]),
    })),
    Vector2: vi.fn(),
  };
});

describe('SCR-06: Crypto Estate Graph Component', () => {
  it('renders spatial estate graph header and switch button', async () => {
    renderWithClient(<CryptoEstateGraphPage />);
    expect(screen.getByText(/SCREEN 6 · CRYPTO ESTATE GRAPH/i)).toBeInTheDocument();
    expect(screen.getByText(/System → File → Cryptographic Asset Topology/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /SWITCH TO 2D CANVAS FALLBACK/i })).toBeInTheDocument();
  });

  it('switches to 2D hierarchical projection mode upon toggle', async () => {
    renderWithClient(<CryptoEstateGraphPage />);
    const toggleButton = screen.getByRole('button', { name: /SWITCH TO 2D CANVAS FALLBACK/i });

    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(screen.getByText(/2D Hierarchical Projection Mode/i)).toBeInTheDocument();
      expect(screen.getByText(/Accessible 2D fallback mode enabled for screen readers/i)).toBeInTheDocument();
    });
  });

  it('passes accessibility checks in 2D mode', async () => {
    const { container } = renderWithClient(<CryptoEstateGraphPage />);
    const toggleButton = screen.getByRole('button', { name: /SWITCH TO 2D CANVAS FALLBACK/i });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(screen.getByText(/2D Hierarchical Projection Mode/i)).toBeInTheDocument();
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
