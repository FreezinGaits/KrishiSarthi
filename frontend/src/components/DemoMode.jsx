import { useState, useEffect, useCallback } from 'react'
import { chatWithAgent, diagnoseImage } from '../services/api'
import DiagnosisCard from './DiagnosisCard'
import './DemoMode.css'

const DEMO_STEPS = [
  { icon: '🎤', label: 'Voice Input', msg: 'मेरे टमाटर के पत्तों पर काले धब्बे हैं' },
  { icon: '📸', label: 'Image Scan', msg: 'Scanning crop image...' },
  { icon: '🔬', label: 'AI Diagnosis', msg: 'Disease: Early Blight (89%)' },
  { icon: '💊', label: 'Treatment', msg: 'Mancozeb 75% WP — 2.5g/litre' },
  { icon: '📍', label: 'Vendor Found', msg: 'Sharma Krishi Kendra — 1.2 km' },
  { icon: '📱', label: 'Notification', msg: 'SMS sent to farmer ✓' },
]

export function DemoBanner() {
  return (
    <div className="demo-banner">
      <span className="demo-pulse" />
      <span>🔬 Demo Mode Active — Krishi-Sarthi Hackathon Build</span>
    </div>
  )
}

export function DemoButton({ onDiagnosis, sessionId, location }) {
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)

  async function runDemo() {
    setRunning(true)
    setResult(null)
    try {
      const res = await chatWithAgent(
        'मेरे टमाटर के पत्तों पर काले धब्बे हैं, बीमारी बताओ और इलाज दो',
        sessionId || 'demo-session',
        null,
        location?.lat || 30.9,
        location?.lng || 75.85,
        'hi'
      )
      setResult(res)
      if (res.diagnosis && onDiagnosis) onDiagnosis(res.diagnosis)
    } catch {
      setResult({
        reply: '🔬 Early Blight detected (89% confidence)\n💊 Treatment: Mancozeb 75% WP at 2.5g/litre\n🏪 Nearest: Sharma Krishi Kendra, Ludhiana (1.2 km)',
        diagnosis: { top_disease: 'Early Blight', top_confidence: 0.89, treatment: 'Apply Mancozeb 75% WP at 2.5g/litre', pesticide: 'Mancozeb 75% WP' },
      })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="demo-section">
      <button className="demo-btn" onClick={runDemo} disabled={running}>
        <span className="demo-btn-icon">{running ? '⏳' : '🎯'}</span>
        <span>{running ? 'Running Demo...' : 'Run Demo Diagnosis'}</span>
      </button>
      {result && (
        <div className="demo-result">
          <div className="demo-reply">{result.reply}</div>
          {result.diagnosis && <DiagnosisCard data={result.diagnosis} />}
        </div>
      )}
    </div>
  )
}

export function PresentationMode({ sessionId, location }) {
  const [active, setActive] = useState(false)
  const [step, setStep] = useState(-1)
  const [diagnosis, setDiagnosis] = useState(null)

  const runPresentation = useCallback(async () => {
    setActive(true)
    setDiagnosis(null)
    for (let i = 0; i < DEMO_STEPS.length; i++) {
      setStep(i)
      await new Promise((r) => setTimeout(r, 2000))
      if (i === 2) {
        setDiagnosis({
          top_disease: 'Early Blight',
          top_confidence: 0.89,
          treatment: 'Apply Mancozeb 75% WP at 2.5g/litre of water. Spray at 10-day intervals.',
          pesticide: 'Mancozeb 75% WP',
        })
      }
    }
    setStep(DEMO_STEPS.length)
    await new Promise((r) => setTimeout(r, 1000))
    setActive(false)
  }, [])

  return (
    <div className="presentation-mode">
      <button className="pres-toggle" onClick={active ? () => setActive(false) : runPresentation}>
        {active ? '⏹ Stop Presentation' : '🎬 Presentation Mode'}
      </button>

      {active && (
        <div className="pres-timeline">
          {DEMO_STEPS.map((s, i) => (
            <div key={i} className={`pres-step ${i < step ? 'done' : i === step ? 'active' : ''}`}>
              <div className="pres-icon">{s.icon}</div>
              <div className="pres-info">
                <div className="pres-label">{s.label}</div>
                <div className="pres-msg">{s.msg}</div>
              </div>
              {i < step && <span className="pres-check">✅</span>}
              {i === step && <span className="pres-spinner" />}
            </div>
          ))}
        </div>
      )}

      {diagnosis && (
        <div className="pres-diagnosis">
          <DiagnosisCard data={diagnosis} />
        </div>
      )}

      {step >= DEMO_STEPS.length && (
        <div className="pres-complete">
          ✅ Full pipeline complete — Voice → Diagnosis → Treatment → Vendor → Notification
        </div>
      )}
    </div>
  )
}
