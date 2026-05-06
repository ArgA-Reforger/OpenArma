import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface TutorialStep {
  id: string
  route: string
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  { id: 'step-1', route: '/llm-providers' },
  { id: 'step-2', route: '/agents' },
  { id: 'step-3', route: '/projects' },
  { id: 'step-4', route: '/projects/*/chat' },
  { id: 'step-5', route: '/knowledge' },
  { id: 'step-6', route: '/mcp-servers' },
  { id: 'step-7', route: '/projects/*/chat' },
  { id: 'step-8', route: '/usage' },
]

interface TutorialState {
  active: boolean
  currentStepIndex: number
  completedSteps: string[]

  startTutorial: (stepIndex?: number) => void
  stopTutorial: () => void
  completeStep: (stepId: string) => void
  goToStep: (index: number) => void
  nextStep: () => void
  resetProgress: () => void
  isStepCompleted: (stepId: string) => boolean
  getCurrentStep: () => TutorialStep | null
}

export const useTutorialStore = create<TutorialState>()(
  persist(
    (set, get) => ({
      active: false,
      currentStepIndex: 0,
      completedSteps: [],

      startTutorial: (stepIndex?: number) =>
        set({ active: true, currentStepIndex: stepIndex ?? get().currentStepIndex }),

      stopTutorial: () => set({ active: false }),

      completeStep: (stepId: string) => {
        const { completedSteps } = get()
        if (!completedSteps.includes(stepId)) {
          set({ completedSteps: [...completedSteps, stepId] })
        }
      },

      goToStep: (index: number) =>
        set({ currentStepIndex: Math.max(0, Math.min(index, TUTORIAL_STEPS.length - 1)) }),

      nextStep: () => {
        const { currentStepIndex } = get()
        if (currentStepIndex < TUTORIAL_STEPS.length - 1) {
          set({ currentStepIndex: currentStepIndex + 1 })
        } else {
          set({ active: false })
        }
      },

      resetProgress: () => set({ completedSteps: [], currentStepIndex: 0, active: false }),

      isStepCompleted: (stepId: string) => get().completedSteps.includes(stepId),

      getCurrentStep: () => {
        const { currentStepIndex } = get()
        return TUTORIAL_STEPS[currentStepIndex] ?? null
      },
    }),
    { name: 'openarma-tutorial' },
  ),
)
