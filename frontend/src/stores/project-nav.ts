import { create } from 'zustand'

interface ProjectNavState {
  activeConvId: number | string | null
  setActiveConvId: (id: number | string | null) => void
}

export const useProjectNavStore = create<ProjectNavState>()((set) => ({
  activeConvId: null,
  setActiveConvId: (id) => set({ activeConvId: id }),
}))
