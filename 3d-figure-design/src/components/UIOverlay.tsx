import { useStore } from '../store/useStore'

export default function UIOverlay() {
  const { 
    viewMode, 
    setViewMode, 
    muscleVisibility, 
    setMuscleVisibility,
    selectedMuscle,
    setSelectedMuscle 
  } = useStore()

  const muscleGroups = [
    { id: 'quadriceps', name: 'Quadriceps' },
    { id: 'hamstrings', name: 'Hamstrings' },
    { id: 'calves', name: 'Calves' },
    { id: 'glutes', name: 'Glutes' },
    { id: 'adductors', name: 'Adductors' },
    { id: 'tibialis', name: 'Tibialis Anterior' }
  ]

  return (
    <div className="ui-overlay">
      <h2>3D Figure - Leg Anatomy</h2>
      
      <div className="section">
        <label>View Mode</label>
        <select 
          value={viewMode} 
          onChange={(e) => setViewMode(e.target.value as any)}
        >
          <option value="skin">Skin Surface</option>
          <option value="muscles">Muscle System</option>
          <option value="skeleton">Skeletal System</option>
          <option value="combined">Combined View</option>
          <option value="detailed">Detailed Leg Mesh</option>
        </select>
      </div>

      {viewMode === 'muscles' && (
        <div className="section">
          <label>Muscle Groups</label>
          {muscleGroups.map(muscle => (
            <div key={muscle.id} style={{ marginBottom: 8 }}>
              <label style={{ 
                display: 'flex', 
                alignItems: 'center', 
                fontSize: 14,
                cursor: 'pointer',
                color: selectedMuscle === muscle.id ? '#3b82f6' : '#ffffff'
              }}>
                <input 
                  type="checkbox" 
                  checked={muscleVisibility[muscle.id] || false}
                  onChange={(e) => setMuscleVisibility(muscle.id, e.target.checked)}
                  style={{ marginRight: 8 }}
                />
                {muscle.name}
              </label>
            </div>
          ))}
        </div>
      )}

      <div className="section">
        <label>Muscle Opacity</label>
        <input 
          type="range" 
          min="0" 
          max="1" 
          step="0.1" 
          defaultValue="0.8"
          onChange={(e) => {
            // Update muscle material opacity
            console.log('Opacity:', e.target.value)
          }}
        />
      </div>

      <div className="button-group">
        <button onClick={() => {
          // Reset camera position
          console.log('Reset view')
        }}>
          Reset View
        </button>
        <button className="secondary" onClick={() => {
          // Export current view
          console.log('Export view')
        }}>
          Export
        </button>
      </div>
    </div>
  )
}