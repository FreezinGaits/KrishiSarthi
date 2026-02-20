import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../context/ThemeProvider'
import useChatSessions from '../hooks/useChatSessions'
import ChatSidebar from '../components/ChatSidebar'
import ChatInterface from '../components/ChatInterface'
import VoiceRecorder from '../components/VoiceRecorder'
import ImageUpload from '../components/ImageUpload'
import DiagnosisCard from '../components/DiagnosisCard'
import VendorList from '../components/VendorList'
import VendorChat from '../components/VendorChat'
import MapView from '../components/MapView'
import MandiRates from '../components/MandiRates'
import { DemoButton } from '../components/DemoMode'
import { findVendors } from '../services/api'
import './Dashboard.css'

export default function Dashboard() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const [activeTab, setActiveTab] = useState('chat')
  const [diagnosis, setDiagnosis] = useState(null)
  const [vendors, setVendors] = useState([])
  const [vendorStatus, setVendorStatus] = useState('idle')
  const [matchedDisease, setMatchedDisease] = useState(null)
  const [location, setLocation] = useState(null)
  const [chatInput, setChatInput] = useState('')
  const [chatVendor, setChatVendor] = useState(null) // vendor currently chatting
  const chatRef = useRef()

  // ── Multi-session hook ──
  const {
    sessions,
    activeSession,
    activeId,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    addMessage,
    setActiveMessages,
  } = useChatSessions()

  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      (pos) => setLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setLocation({ lat: 30.9, lng: 75.85 })
    )
  }, [])

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
    const diseaseClass = data?.class_name || data?.disease || null
    if (diseaseClass && location) {
      fetchVendors(diseaseClass)
    }
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
            { id: 'chat', icon: '💬', label: 'Chat', hindi: 'चैट' },
            { id: 'voice', icon: '🎤', label: 'Voice', hindi: 'आवाज़' },
            { id: 'camera', icon: '📸', label: 'Scan', hindi: 'स्कैन' },
            { id: 'results', icon: '🔬', label: 'Results', hindi: 'नतीजे' },
            { id: 'vendors', icon: '📍', label: 'Vendors', hindi: 'दुकानें' },
            { id: 'market', icon: '🏪', label: 'Market', hindi: 'मंडी' },
          ].map((tab) => (
            <button
              key={tab.id}
              className={`dash-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
              <span className="tab-hindi">{tab.hindi}</span>
            </button>
          ))}
        </div>
        <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </nav>

      <div className="dash-body">
        {/* ── Chat Sidebar (only visible on Chat tab) ── */}
        {activeTab === 'chat' && <ChatSidebar
          sessions={sessions}
          activeId={activeId}
          onCreateSession={createSession}
          onSwitchSession={(id) => {
            switchSession(id)
            setActiveTab('chat')
          }}
          onDeleteSession={deleteSession}
          onRenameSession={renameSession}
        />}

        {/* ── Main Content ── */}
        <main className="dash-main">
          {activeTab === 'chat' && (
            <ChatInterface
              ref={chatRef}
              messages={activeSession?.messages || []}
              sessionId={activeId}
              location={location}
              initialInput={chatInput}
              onDiagnosis={handleDiagnosis}
              onAddMessage={addMessage}
              onSetMessages={setActiveMessages}
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
              <DemoButton onDiagnosis={handleDiagnosis} sessionId={activeId} location={location} />
              {diagnosis ? (
              <DiagnosisCard
                data={diagnosis}
                onRequestMedicine={(info) => {
                  console.log('Medicine request sent:', info)
                  // Optionally switch to vendors tab
                  setActiveTab('vendors')
                }}
              />
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
                <VendorList
                  vendors={vendors}
                  status={vendorStatus}
                  matchedDisease={matchedDisease}
                  onChatVendor={(v) => setChatVendor(v)}
                />
                <MapView vendors={vendors} center={location} />
              </div>
            </div>
          )}

          {activeTab === 'market' && <MandiRates />}
        </main>
      </div>

      {/* ── Vendor Chat Modal ── */}
      {chatVendor && (
        <VendorChat
          vendor={chatVendor}
          onClose={() => setChatVendor(null)}
        />
      )}
    </div>
  )
}
