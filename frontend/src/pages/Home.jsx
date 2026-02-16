import { useNavigate } from 'react-router-dom'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()

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
          <button className="nav-cta" onClick={() => navigate('/dashboard')}>
            Launch App
          </button>
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
          <button className="btn-primary" onClick={() => navigate('/dashboard')}>
            <span className="btn-icon">🔬</span>
            Start Diagnosis
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
