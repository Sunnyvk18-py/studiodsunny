import { create } from "zustand";

type UIState = {
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  quickCreateOpen: boolean;
  toggleSidebar: () => void;
  setCommandOpen: (open: boolean) => void;
  setQuickCreateOpen: (open: boolean) => void;
};

export const useUI = create<UIState>((set) => ({
  sidebarCollapsed: false,
  commandOpen: false,
  quickCreateOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setCommandOpen: (open) => set({ commandOpen: open }),
  setQuickCreateOpen: (open) => set({ quickCreateOpen: open }),
}));
