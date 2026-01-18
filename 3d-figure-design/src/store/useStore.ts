import { create } from 'zustand'

interface MuscleVisibility {
  [key: string]: boolean
}

interface Store {
  viewMode: 'skin' | 'muscles' | 'skeleton' | 'combined' | 'detailed'
  setViewMode: (mode: 'skin' | 'muscles' | 'skeleton' | 'combined' | 'detailed') => void
  
  muscleVisibility: MuscleVisibility
  setMuscleVisibility: (muscle: string, visible: boolean) => void
  
  selectedMuscle: string | null
  setSelectedMuscle: (muscle: string | null) => void
  
  highlightedBone: string | null
  setHighlightedBone: (bone: string | null) => void
  
  animationState: 'idle' | 'walk' | 'run' | 'squat'
  setAnimationState: (state: 'idle' | 'walk' | 'run' | 'squat') => void
  
  showAnnotations: boolean
  toggleAnnotations: () => void
}

export const useStore = create<Store>((set) => ({
  viewMode: 'skin',
  setViewMode: (mode) => set({ viewMode: mode }),
  
  muscleVisibility: {
    quadriceps: true,
    hamstrings: true,
    calves: true,
    glutes: true,
    adductors: true,
    tibialis: true
  },
  setMuscleVisibility: (muscle, visible) => 
    set((state) => ({
      muscleVisibility: {
        ...state.muscleVisibility,
        [muscle]: visible
      }
    })),
  
  selectedMuscle: null,
  setSelectedMuscle: (muscle) => set({ selectedMuscle: muscle }),
  
  highlightedBone: null,
  setHighlightedBone: (bone) => set({ highlightedBone: bone }),
  
  animationState: 'idle',
  setAnimationState: (state) => set({ animationState: state }),
  
  showAnnotations: true,
  toggleAnnotations: () => set((state) => ({ showAnnotations: !state.showAnnotations }))
}))