import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
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

// activeScanId is persisted to localStorage: every screen navigates via a
// full route change (page.goto / <a>/router.push all reload the route),
// and without persistence the in-memory store reset on each navigation,
// silently dropping back to the default scan and making "launch a scan,
// then visit another screen" lose its context. selectedFinding/drawer/
// palette state stay in-memory only (per-session UI state, not scan data).
export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Matches the real backend's seeded scan (api/db.py::init_db -> the
      // stub_data scan) as the first-ever-load default, before any real
      // scan has been launched.
      activeScanId: 'scan_stub_001',
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
    }),
    {
      name: 'ecdat-app-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ activeScanId: state.activeScanId, crqcZ: state.crqcZ }),
    }
  )
);
