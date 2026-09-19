import type { Meta, StoryObj } from '@storybook/react';
import { MoscaMatrixView } from './MoscaMatrixView';
import { mockFindings } from '../../mocks/data';
import type { Finding } from '../../types/crypto';

// Generate synthetic 1000 items for dense scenario
const denseFindings: Finding[] = [];
for (let i = 0; i < 125; i++) {
  mockFindings.forEach((base, idx) => {
    // mockFindings fixtures are always fully scored -- base.risk! is safe here.
    const baseRisk = base.risk!;
    denseFindings.push({
      ...base,
      id: `f-dense-${i * 8 + idx}`,
      risk: {
        ...baseRisk,
        X: Math.max(1, (baseRisk.X + i) % 25),
        Y: Math.max(1, (baseRisk.Y + i * 2) % 15),
      },
    });
  });
}

const meta: Meta<typeof MoscaMatrixView> = {
  title: 'Screens/03-MoscaMatrix',
  component: MoscaMatrixView,
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof MoscaMatrixView>;

export const Typical: Story = {
  args: {
    findings: mockFindings,
    initialZ: 10,
    error: null,
  },
};

export const Empty: Story = {
  args: {
    findings: [],
    initialZ: 10,
    error: null,
  },
};

export const DenseDataset: Story = {
  args: {
    findings: denseFindings,
    initialZ: 10,
    error: null,
  },
};

export const ApiError: Story = {
  args: {
    findings: [],
    initialZ: 10,
    error: 'Failed to establish WebSocket link to /api/v1/scans/scan-7f8e1a/rescore. Gateway timed out (504).',
  },
};
