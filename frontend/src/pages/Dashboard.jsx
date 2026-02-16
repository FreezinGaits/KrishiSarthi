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

  useEffect(() => {
    if (location) {
      findVendors(location.lat, location.lng)
        .then((res) => setVendors(res.vendors || []))
        .catch(() => {})
    }
  }, [location])

  function handleTranscript(text) {
    setChatInput(text)
    setActiveTab('chat')
    if (chatRef.current?.sendMessage) {
      chatRef.current.sendMessage(text)
    }
  }

  function handleDiagnosis(data) {
    setDiagnosis(data)
    setActiveTab('results')
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
          ))}
        </div>
      </nav>

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
            <h2 className="panel-title">📍 Nearby Vendors</h2>
            <div className="vendors-layout">
              <VendorList vendors={vendors} />
              <MapView vendors={vendors} center={location} />
            </div>
          </div>
        )}


      </main>
    </div>
  )
}
