import './DiagnosisCard.css'

export default function DiagnosisCard({ data, compact = false }) {
  if (!data) return null

  const disease = data.top_disease || data.disease || 'Unknown'
  const confidence = data.top_confidence || data.confidence || 0
  const confPercent = Math.round(confidence * 100)
  const treatment = data.treatment || ''
  const pesticide = data.pesticide || ''
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
          <h3>🔬 {disease}</h3>
          <span className="diag-scientific">{data.scientific_name || ''}</span>
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

      {treatment && (
        <div className="diag-section">
          <h4>💊 Treatment</h4>
          <p>{treatment}</p>
        </div>
      )}

      {pesticide && (
        <div className="diag-section">
          <h4>🧴 Recommended Pesticide</h4>
          <p>{pesticide}</p>
        </div>
      )}

      {data.prevention && (
        <div className="diag-section">
          <h4>🛡️ Prevention</h4>
          <p>{data.prevention}</p>
        </div>
      )}
    </div>
  )
}
