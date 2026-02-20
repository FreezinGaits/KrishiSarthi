import { useState, useRef, useCallback } from 'react'
import { createMedicineRequest } from '../services/api'
import './DiagnosisCard.css'

const DEMO_FARMER_ID = 'demo-farmer-001'
const DEMO_VENDOR_ID = 'demo-vendor-001'

// ── Speech helper ──
function speakText(text) {
  if (!window.speechSynthesis) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'hi-IN'
  utterance.rate = 0.9
  // Try to pick a Hindi voice
  const voices = window.speechSynthesis.getVoices()
  const hindiVoice = voices.find(v => v.lang.startsWith('hi'))
  if (hindiVoice) utterance.voice = hindiVoice
  window.speechSynthesis.speak(utterance)
}

function SpeakButton({ text }) {
  const [playing, setPlaying] = useState(false)

  const handleSpeak = (e) => {
    e.stopPropagation()
    if (playing) {
      window.speechSynthesis.cancel()
      setPlaying(false)
      return
    }
    setPlaying(true)
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'hi-IN'
    utterance.rate = 0.9
    const voices = window.speechSynthesis.getVoices()
    const hindiVoice = voices.find(v => v.lang.startsWith('hi'))
    if (hindiVoice) utterance.voice = hindiVoice
    utterance.onend = () => setPlaying(false)
    utterance.onerror = () => setPlaying(false)
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
  }

  return (
    <button
      className={`speak-btn ${playing ? 'speaking' : ''}`}
      onClick={handleSpeak}
      title="सुनें"
      aria-label="बोलकर सुनें"
    >
      {playing ? '⏹️' : '🔊'}
    </button>
  )
}

export default function DiagnosisCard({ data, compact = false, onRequestMedicine }) {
  const [medReqStatus, setMedReqStatus] = useState({}) // { medicineName: 'idle'|'loading'|'success'|'error' }

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
  
  const severity = confPercent >= 80 ? 'high' : confPercent >= 50 ? 'medium' : 'low'

  // Use Hindi fields with English fallback
  const commonName = meta.common_name_hi || meta.common_name || disease.replace(/___/g, ' ')
  const pathogenType = meta.pathogen_type_hi || meta.pathogen_type
  const keySymptoms = meta.key_symptoms_hi || meta.key_symptoms
  const transmission = meta.transmission_hi || meta.transmission
  const culturalControls = meta.cultural_controls_hi || meta.cultural_controls
  const chemicalControls = meta.chemical_controls_examples_hi || meta.chemical_controls_examples
  const prevention = meta.prevention_hi || meta.prevention

  if (compact) {
    return (
      <div className="diag-compact">
        <span className="diag-badge" data-severity={severity}>{confPercent}%</span>
        <strong>{commonName}</strong>
        {chemicalControls && <span className="diag-treatment-mini">💊 {(Array.isArray(chemicalControls) ? chemicalControls[0] : chemicalControls).slice(0, 80)}...</span>}
      </div>
    )
  }

  // Build full card text for top-level speak button
  const fullCardText = [
    commonName,
    pathogenType && `रोगज़नक़ का प्रकार: ${pathogenType}`,
    keySymptoms && `प्रमुख लक्षण: ${keySymptoms.join(', ')}`,
    transmission && `फैलाव: ${transmission.join(', ')}`,
    culturalControls && `फसल प्रबंधन: ${culturalControls.join(', ')}`,
    chemicalControls && `रासायनिक उपचार: ${chemicalControls.join(', ')}`,
    prevention && `रोकथाम: ${prevention.join(', ')}`
  ].filter(Boolean).join('। ')

  return (
    <div className="diag-card" data-severity={severity}>
      <div className="diag-header">
        <div className="diag-disease">
          <h3>🔬 {commonName}</h3>
          {meta.scientific_name && (
            <span className="diag-scientific">
              {meta.scientific_name}
            </span>
          )}
        </div>
  
        <div className="diag-header-right">
          <SpeakButton text={fullCardText} />
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
      </div>
  
      {pathogenType && (
        <div className="diag-section">
          <div className="section-header">
            <h4>🦠 रोगज़नक़ का प्रकार</h4>
            <SpeakButton text={`रोगज़नक़ का प्रकार: ${pathogenType}`} />
          </div>
          <p>{pathogenType}</p>
        </div>
      )}
  
      {keySymptoms && (
        <div className="diag-section">
          <div className="section-header">
            <h4>🌿 प्रमुख लक्षण</h4>
            <SpeakButton text={`प्रमुख लक्षण: ${keySymptoms.join('। ')}`} />
          </div>
          <ul>
            {keySymptoms.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
  
      {transmission && (
        <div className="diag-section">
          <div className="section-header">
            <h4>🔁 फैलाव</h4>
            <SpeakButton text={`फैलाव: ${transmission.join('। ')}`} />
          </div>
          <ul>
            {transmission.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}
  
      {culturalControls && (
        <div className="diag-section">
          <div className="section-header">
            <h4>🌾 फसल प्रबंधन</h4>
            <SpeakButton text={`फसल प्रबंधन: ${culturalControls.join('। ')}`} />
          </div>
          <ul>
            {culturalControls.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
  
      {chemicalControls && (
        <div className="diag-section">
          <div className="section-header">
            <h4>💊 रासायनिक उपचार</h4>
            <SpeakButton text={`रासायनिक उपचार: ${chemicalControls.join('। ')}`} />
          </div>
          <ul>
            {chemicalControls.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
  
      {prevention && (
        <div className="diag-section">
          <div className="section-header">
            <h4>🛡️ रोकथाम</h4>
            <SpeakButton text={`रोकथाम: ${prevention.join('। ')}`} />
          </div>
          <ul>
            {prevention.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Check Availability Buttons ── */}
      {chemicalControls && chemicalControls.length > 0 && (
        <div className="diag-section diag-availability">
          <div className="section-header">
            <h4>🛒 दवाई उपलब्धता जांचें / Check Availability</h4>
          </div>
          <div className="avail-btn-list">
            {chemicalControls.map((med, i) => {
              const medName = (typeof med === 'string' ? med : String(med)).slice(0, 80)
              const status = medReqStatus[medName] || 'idle'
              return (
                <button
                  key={i}
                  className={`avail-btn avail-${status}`}
                  disabled={status === 'loading' || status === 'success'}
                  onClick={async () => {
                    setMedReqStatus(prev => ({ ...prev, [medName]: 'loading' }))
                    try {
                      const res = await createMedicineRequest(
                        DEMO_FARMER_ID,
                        DEMO_VENDOR_ID,
                        commonName,
                        medName
                      )
                      setMedReqStatus(prev => ({ ...prev, [medName]: 'success' }))
                      onRequestMedicine?.({
                        requestId: res.id,
                        medicineName: medName,
                        diseaseName: commonName,
                      })
                    } catch {
                      setMedReqStatus(prev => ({ ...prev, [medName]: 'error' }))
                    }
                  }}
                >
                  <span className="avail-icon">
                    {status === 'loading' ? '⏳'
                      : status === 'success' ? '✅'
                        : status === 'error' ? '❌'
                          : '🔍'}
                  </span>
                  <span className="avail-text">
                    {status === 'loading' ? 'Sending…'
                      : status === 'success' ? 'Sent!'
                        : status === 'error' ? 'Failed — Retry'
                          : medName}
                  </span>
                  {status === 'idle' && (
                    <span className="avail-sub">उपलब्धता जांचें</span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
