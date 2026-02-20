import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthProvider'
import { useTheme } from '../context/ThemeProvider'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()
  const { user, loading, signInWithGoogle, signOut } = useAuth()
  const { theme, toggleTheme } = useTheme()

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
          <a href="#features">Features / सुविधाएं</a>
          <a href="#how-it-works">कैसे काम करता है</a>

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
                बाहर निकलें
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
              साइन इन करें / Sign In
            </button>
          )}
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>
      </nav>

      <header className="hero">
        <div className="hero-badge">🤖 AI से चलने वाला खेती सहायक / AI-Powered Agricultural Assistant</div>
        <h1 className="hero-title">
          <span className="hero-hindi">कृषि-सारथी</span>
          <span className="hero-sub">Krishi-Sarthi — आपका खेती साथी</span>
        </h1>
        <p className="hero-desc">
          हिंदी में बोलें, फसल की फोटो खींचें — तुरंत बीमारी पहचानें और इलाज पाएं।
          <br />
          <span className="hero-desc-en">
            Speak in Hindi, snap a photo of your crop — get instant disease diagnosis, treatment advice, and nearby pesticide shops.
          </span>
        </p>
        <div className="hero-buttons">
          <button className="btn-primary" onClick={handleStartDiagnosis}>
            <span className="btn-icon">{user ? '🔬' : '🔑'}</span>
            {user ? 'जाँच शुरू करें / Start Diagnosis' : 'शुरू करें / Sign In'}
          </button>
          <button className="btn-secondary" onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}>
            <span className="btn-icon">📖</span>
            और जानें / Learn More
          </button>
        </div>
        <div className="hero-stats">
          <div className="stat">
            <span className="stat-value">12</span>
            <span className="stat-label">फसल रोग / Crop Diseases</span>
          </div>
          <div className="stat">
            <span className="stat-value">20+</span>
            <span className="stat-label">कीटनाशक दुकानें / Vendors</span>
          </div>
          <div className="stat">
            <span className="stat-value">🎤</span>
            <span className="stat-label">हिंदी आवाज़ / Hindi Voice</span>
          </div>
          <div className="stat">
            <span className="stat-value">&lt;5s</span>
            <span className="stat-label">जाँच समय / Diagnosis</span>
          </div>
        </div>
      </header>

      <section className="features" id="features">
        <h2 className="section-title">सुविधाएं / Key Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🎤</div>
            <h3>आवाज़ से पूछें / Voice Input</h3>
            <p>हिंदी या English में बोलें। AI आपकी बात समझेगा और जवाब देगा।</p>
            <p className="feature-en">Speak in Hindi or English — our AI understands your crop problems.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📸</div>
            <h3>फोटो से जाँच / Image Diagnosis</h3>
            <p>फसल की फोटो भेजें — AI बीमारी पहचान कर इलाज बताएगा।</p>
            <p className="feature-en">Upload a crop photo — AI identifies the disease with treatment advice.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">💊</div>
            <h3>इलाज की सलाह / Treatment Advice</h3>
            <p>सही दवाई, मात्रा, और छिड़काव का तरीका जानें।</p>
            <p className="feature-en">Get precise pesticide recommendations, dosages, and approved treatment plans.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📍</div>
            <h3>नज़दीकी दुकान / Find Shops</h3>
            <p>पास की कीटनाशक दुकानें ढूंढें — फोन नंबर, रास्ता, और कीमत।</p>
            <p className="feature-en">Find nearest pesticide shops with phone numbers, prices, and directions.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>AI चैट सहायक / AI Chat</h3>
            <p>खेती से जुड़ा कोई भी सवाल पूछें — AI जवाब देगा।</p>
            <p className="feature-en">Ask any farming question — the AI agent will answer it for you.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>मंडी भाव / Market Prices</h3>
            <p>आज के मंडी भाव देखें — सब्ज़ी, अनाज, फल।</p>
            <p className="feature-en">Check today's mandi rates for vegetables, grains, and fruits.</p>
          </div>
        </div>
      </section>

      <section className="how-it-works" id="how-it-works">
        <h2 className="section-title">कैसे काम करता है / How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-num">1</div>
            <h3>बोलें या फोटो भेजें</h3>
            <p className="step-hindi">हिंदी में बात करें या फसल की फोटो खींचें</p>
            <p className="step-english">Speak in Hindi or upload a crop photo</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-num">2</div>
            <h3>AI जाँच करेगा</h3>
            <p className="step-hindi">AI आपकी बात सुनेगा और फोटो देखेगा</p>
            <p className="step-english">AI listens to you and analyzes your photo</p>
          </div>
          <div className="step-arrow">→</div>
          <div className="step">
            <div className="step-num">3</div>
            <h3>नतीजा और इलाज</h3>
            <p className="step-hindi">बीमारी का नाम, दवाई, और दुकान का पता</p>
            <p className="step-english">Disease name, medicine, and shop location</p>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <p>Smart India Hackathon के लिए बनाया गया · कृषि-सारथी / Krishi-Sarthi © 2026</p>
      </footer>
    </div>
  )
}
