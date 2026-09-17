import { create } from 'zustand';
import type { Finding } from '../types/crypto';

interface AppState {
  activeScanId: string;
  crqcZ: number;
  selectedFinding: Finding | null;
  isDrawerOpen: boolean;
  isCommandPaletteOpen: boolean;
  
  setActiveScanId: (id: string) => void;
  setCrqcZ: (z: number) => void;
  openDrawer: (finding: Finding) => void;
  closeDrawer: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  toggleCommandPalette: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeScanId: 'scan-7f8e1a',
  crqcZ: 10,
  selectedFinding: null,
  isDrawerOpen: false,
  isCommandPaletteOpen: false,

  setActiveScanId: (id) => set({ activeScanId: id }),
  setCrqcZ: (z) => set({ crqcZ: z }),
  openDrawer: (finding) => set({ selectedFinding: finding, isDrawerOpen: true }),
  closeDrawer: () => set({ selectedFinding: null, isDrawerOpen: false }),
  setCommandPaletteOpen: (open) => set({ isCommandPaletteOpen: open }),
  toggleCommandPalette: () => set((state) => ({ isCommandPaletteOpen: !state.isCommandPaletteOpen })),
}));
