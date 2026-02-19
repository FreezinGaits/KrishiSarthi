import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import ChatInterface from '../components/ChatInterface'
import VoiceRecorder from '../components/VoiceRecorder'
import ImageUpload from '../components/ImageUpload'
import DiagnosisCard from '../components/DiagnosisCard'
import VendorList from '../components/VendorList'
import MapView from '../components/MapView'
import { DemoButton } from '../components/DemoMode'
import { findVendors } from '../services/api'
import './Dashboard.css'

export default function Dashboard() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('chat')
  const [diagnosis, setDiagnosis] = useState(null)
  const [vendors, setVendors] = useState([])
  const [vendorStatus, setVendorStatus] = useState('idle') // idle | loading | loaded | error
  const [matchedDisease, setMatchedDisease] = useState(null)
  const [location, setLocation] = useState(null)
  const [sessionId] = useState(() => `session-${Date.now()}`)
  const [chatInput, setChatInput] = useState('')
  const chatRef = useRef()

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setLocation({ lat: 30.9, lng: 75.85 }) // Default: Ludhiana
    )
  }, [])

  // Fetch vendors — re-runs when location or diagnosis changes
  function fetchVendors(disease = null) {
    if (!location) return
    setVendorStatus('loading')
    findVendors(location.lat, location.lng, 'pesticide shop', 100, disease)
      .then((res) => {
        setVendors(res.vendors || [])
        setMatchedDisease(disease)
        setVendorStatus('loaded')
      })
      .catch((err) => {
        console.error('Vendor fetch failed:', err)
        setVendorStatus('error')
      })
  }

  useEffect(() => {
    if (location) {
      // If we already have a diagnosis, filter vendors by disease
      const diseaseClass = diagnosis?.class_name || diagnosis?.disease || null
      fetchVendors(diseaseClass)
    }
  }, [location])

  function handleTranscript(text) {
    setChatInput(text)
    setActiveTab('chat')
    if (chatRef.current?.sendMessage) {
      chatRef.current.sendMessage(text)
    }
  }

  function handleDiagnosis(data, meta = {}) {
    setDiagnosis(data)

    // Re-fetch vendors filtered by the diagnosed disease
    const diseaseClass = data?.class_name || data?.disease || null
    if (diseaseClass && location) {
      fetchVendors(diseaseClass)
    }

    // Only switch to the Results tab automatically when diagnosis came from the
    // ImageUpload (camera / file) or when explicitly requested.
    if (meta.from === 'image' || meta.autoOpen === true) {
      setActiveTab('results')
    }
  }


  return (
    <div className="dashboard">

      <nav className="dash-nav">
        <div className="dash-brand" onClick={() => navigate('/')}>
          <span className="dash-icon">🌾</span>
          <span>कृषि-सारथी</span>
        </div>
        <div className="dash-tabs">
          {[
            { id: 'chat', icon: '💬', label: 'Chat' },
            { id: 'voice', icon: '🎤', label: 'Voice' },
            { id: 'camera', icon: '📸', label: 'Scan' },
            { id: 'results', icon: '🔬', label: 'Results' },
            { id: 'vendors', icon: '📍', label: 'Vendors' },

          ].map((tab) => (
            <button
              key={tab.id}
              className={`dash-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
            </button>

          ))
}
        </div>
      </nav>
      <button className="dash-reset-btn" onClick={() => {
        // call child reset via ref
        if (chatRef.current?.sendMessage) {
          // trigger ChatInterface to reset by calling a new exposed method if you added one;
          // simpler: clear localStorage and reload page:
          localStorage.removeItem('chat_history');
          localStorage.removeItem('chat_session_id');
          window.location.reload();
        }
      }}>
        New Chat
      </button>

      <main className="dash-main">
        {activeTab === 'chat' && (
          <ChatInterface
            ref={chatRef}
            sessionId={sessionId}
            location={location}
            initialInput={chatInput}
            onDiagnosis={handleDiagnosis}
          />
        )}

        {activeTab === 'voice' && (
          <div className="dash-panel">
            <h2 className="panel-title">🎤 Voice Input</h2>
            <p className="panel-desc">हिंदी या English में बोलें — AI समझेगा</p>
            <VoiceRecorder onTranscript={handleTranscript} />
          </div>
        )}

        {activeTab === 'camera' && (
          <div className="dash-panel">
            <h2 className="panel-title">📸 Crop Photo Scan</h2>
            <p className="panel-desc">फसल की फोटो अपलोड करें — AI बीमारी पहचानेगा</p>
            <ImageUpload onDiagnosis={handleDiagnosis} />
          </div>
        )}

        {activeTab === 'results' && (
          <div className="dash-panel">
            <h2 className="panel-title">🔬 Diagnosis Results</h2>
            <DemoButton onDiagnosis={handleDiagnosis} sessionId={sessionId} location={location} />
            {diagnosis ? (
              <DiagnosisCard data={diagnosis} />
            ) : (
              <div className="empty-state">
                <span className="empty-icon">🌱</span>
                <p>No diagnosis yet. Upload a crop photo or click "Run Demo" above.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'vendors' && (
          <div className="dash-panel vendors-panel">
            <h2 className="panel-title">📍 {matchedDisease ? 'Recommended Vendors' : 'Nearby Vendors'}</h2>
            {matchedDisease && (
              <div className="disease-vendor-banner">
                <span>🎯 Showing vendors with pesticides for <strong>{matchedDisease.replace(/___/g, ' – ').replace(/_/g, ' ')}</strong></span>
                <button className="btn-show-all" onClick={() => fetchVendors(null)}>Show All</button>
              </div>
            )}
            <div className="vendors-layout">
              <VendorList vendors={vendors} status={vendorStatus} matchedDisease={matchedDisease} />
              <MapView vendors={vendors} center={location} />
            </div>
          </div>
        )}


      </main>
    </div>
  )
}
