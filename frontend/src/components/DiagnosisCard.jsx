import './DiagnosisCard.css'

export default function DiagnosisCard({ data, compact = false }) {
  if (!data) return null

  const disease = data.top_disease || data.disease || ''

  // Hide card completely if disease invalid
  if (!disease || disease === 'Unknown') {
    return null
  }
  const confidence = data.top_confidence || data.confidence || 0
  const confPercent = Math.round(confidence * 100)
  
  // 🔥 Read metadata correctly
  const meta = data.metadata || {}
  
  const summary = meta.summary || ''
  const symptoms = meta.symptoms || ''
  const causes = meta.causes || ''
  const treatment = meta.treatment || ''
  const pesticide = meta.pesticide || ''
  const prevention = meta.prevention || ''
  
  const severity = confPercent >= 80 ? 'high' : confPercent >= 50 ? 'medium' : 'low'

  if (compact) {
    return (
      <div className="diag-compact">
        <span className="diag-badge" data-severity={severity}>{confPercent}%</span>
        <strong>{disease}</strong>
        {treatment && <span className="diag-treatment-mini">💊 {treatment.slice(0, 80)}...</span>}
      </div>
    )
  }

  return (
    <div className="diag-card" data-severity={severity}>
      <div className="diag-header">
        <div className="diag-disease">
          <h3>🔬 {meta.common_name || disease.replace(/___/g, ' ')}</h3>
          {meta.scientific_name && (
            <span className="diag-scientific">
              {meta.scientific_name}
            </span>
          )}
        </div>
  
        <div className="confidence-ring" data-severity={severity}>
          <svg viewBox="0 0 36 36" className="ring-svg">
            <path
              className="ring-bg"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path
              className="ring-fill"
              strokeDasharray={`${confPercent}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <span className="ring-text">{confPercent}%</span>
        </div>
      </div>
  
      {meta.pathogen_type && (
        <div className="diag-section">
          <h4>🦠 Pathogen Type</h4>
          <p>{meta.pathogen_type}</p>
        </div>
      )}
  
      {meta.key_symptoms && (
        <div className="diag-section">
          <h4>🌿 Key Symptoms</h4>
          <ul>
            {meta.key_symptoms.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
  
      {meta.transmission && (
        <div className="diag-section">
          <h4>🔁 Transmission</h4>
          <ul>
            {meta.transmission.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
  
      {meta.cultural_controls && (
        <div className="diag-section">
          <h4>🌾 Cultural Controls</h4>
          <ul>
            {meta.cultural_controls.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
  
      {meta.chemical_controls_examples && (
        <div className="diag-section">
          <h4>💊 Chemical Controls</h4>
          <ul>
            {meta.chemical_controls_examples.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
  
      {meta.prevention && (
        <div className="diag-section">
          <h4>🛡️ Prevention</h4>
          <ul>
            {meta.prevention.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
