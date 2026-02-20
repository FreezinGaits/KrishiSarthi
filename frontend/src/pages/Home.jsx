import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthProvider'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()
  const { user, loading, signInWithGoogle, signOut } = useAuth()

  function handleStartDiagnosis() {
    if (user) {
      navigate('/dashboard')
    } else {
      signInWithGoogle()
    }
  }

  return (
    <div className="home">
      {/* Floating particles */}
      <div className="particles">
        {[...Array(20)].map((_, i) => (
          <span key={i} className="particle" style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 8}s`,
            animationDuration: `${6 + Math.random() * 8}s`,
          }} />
        ))}
      </div>

      <nav className="home-nav">
        <div className="nav-brand">
          <span className="nav-icon">🌾</span>
          <span>कृषि-सारथी</span>
        </div>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#how-it-works">How it Works</a>

          {loading ? null : user ? (
            <div className="nav-user">
              <img
                className="nav-avatar"
                src={user.user_metadata?.avatar_url || user.user_metadata?.picture}
                alt={user.user_metadata?.full_name || 'User'}
                referrerPolicy="no-referrer"
              />
              <span className="nav-user-name">
                {user.user_metadata?.full_name || user.email}
              </span>
              <button className="nav-logout" onClick={signOut}>
                Logout
              </button>
            </div>
          ) : (
            <button className="nav-cta google-signin" onClick={signInWithGoogle}>
              <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign in with Google
            </button>
          )}
        </div>
      </nav>

      <header className="hero">
        <div className="hero-badge">🤖 AI-Powered Agricultural Assistant</div>
        <h1 className="hero-title">
          <span className="hero-hindi">कृषि-सारथी</span>
          <span className="hero-sub">Krishi-Sarthi</span>
        </h1>
        <p className="hero-desc">
          Voice-enabled, AI-powered crop disease diagnosis for Indian farmers.
          Speak in Hindi, snap a photo — get instant treatment advice and nearby pesticide vendors.
        </p>
        <div className="hero-buttons">
          <button className="btn-primary" onClick={handleStartDiagnosis}>
            <span className="btn-icon">{user ? '🔬' : '🔑'}</span>
            {user ? 'Start Diagnosis' : 'Sign in to Start'}
          </button>
          <button className="btn-secondary" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>
            <span className="btn-icon">📖</span>
            Learn More
          </button>
        </div>
        <div className="hero-stats">
          <div className="stat">
            <span className="stat-value">30+</span>
            <span className="stat-label">Crop Diseases</span>
          </div>
          <div className="stat">
            <span className="stat-value">20+</span>
            <span className="stat-label">Punjab Vendors</span>
          </div>
          <div className="stat">
            <span className="stat-value">हिंदी</span>
            <span className="stat-label">Voice Support</span>
          </div>
          <div className="stat">
            <span className="stat-value">&lt;5s</span>
            <span className="stat-label">Diagnosis Time</span>
          </div>
        </div>
      </header>

      <section className="features" id="features">
        <h2 className="section-title">Key Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🎤</div>
            <h3>Voice Input</h3>
            <p>Speak in Hindi or English. Our Whisper AI transcribes and understands your crop problems.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📸</div>
            <h3>Image Diagnosis</h3>
            <p>Upload a photo of your crop. PyTorch AI classifies the disease with treatment advice.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💊</div>
            <h3>Treatment Advice</h3>
            <p>Get precise pesticide recommendations, dosages, and PAU-approved treatment plans.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📍</div>
            <h3>Vendor Finder</h3>
            <p>Find nearest pesticide shops with prices, phone numbers, and directions on map.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>AI Chat Agent</h3>
            <p>LangChain-powered agent that orchestrates tools to answer any farming question.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚡</div>
            <h3>n8n Automation</h3>
            <p>Auto-notifications, expert escalation, and price aggregation via n8n workflows.</p>
          </div>
        </div>
      </section>

      <section className="how-it-works" id="how-it-works">
        <h2 className="section-title">How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-num">1</div>
            <h3>Speak or Upload</h3>
            <p>Record voice in Hindi or upload a crop photo</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-num">2</div>
            <h3>AI Analysis</h3>
            <p>Whisper + PyTorch + LangChain process your input</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-num">3</div>
            <h3>Get Results</h3>
            <p>Disease diagnosis, treatment, and vendor locations</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <p>Built for Smart India Hackathon · Krishi-Sarthi &copy; 2026</p>
      </footer>
    </div>
  )
}
