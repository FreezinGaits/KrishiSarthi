import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthProvider'
import { useTheme } from '../context/ThemeProvider'
import './ChoosePlan.css'

export default function ChoosePlan() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const { theme, toggleTheme } = useTheme()

  // If not authenticated, redirect to home
  if (!loading && !user) {
    navigate('/', { replace: true })
    return null
  }
  if (loading) return null

  return (
    <div className="choose-plan-page">
      {/* Background particles */}
      <div className="plan-particles">
        {[...Array(15)].map((_, i) => (
          <span key={i} className="plan-particle" style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 6}s`,
            animationDuration: `${5 + Math.random() * 7}s`,
          }} />
        ))}
      </div>

      {/* Theme toggle */}
      <button className="theme-toggle plan-theme-toggle" onClick={toggleTheme} title="Toggle theme">
        {theme === 'light' ? '🌙' : '☀️'}
      </button>

      <div className="plan-container">
        <div className="plan-welcome">
          <h1>🌾 स्वागत है, {user?.user_metadata?.full_name || 'किसान'}!</h1>
          <p className="plan-welcome-hi">कृषि-सारथी में आपका स्वागत है। अपना प्लान चुनें।</p>
          <p className="plan-welcome-en">Welcome to Krishi-Sarthi. Choose your plan to continue.</p>
        </div>

        <div className="plan-cards">
          {/* Free Version */}
          <div className="plan-card plan-free" onClick={() => navigate('/dashboard')}>
            <div className="plan-badge plan-badge-free">मुफ़्त / FREE</div>
            <div className="plan-icon">🌱</div>
            <h2 className="plan-title">
              <span className="plan-title-hi">मुफ़्त संस्करण</span>
              <span className="plan-title-en">Free Version</span>
            </h2>
            <ul className="plan-features">
              <li>✅ AI फसल रोग पहचान / Disease Detection</li>
              <li>✅ हिंदी में AI चैट / Hindi AI Chat</li>
              <li>✅ आवाज़ से पूछें / Voice Input</li>
              <li>✅ फोटो से जाँच / Image Diagnosis</li>
              <li>✅ नज़दीकी दुकानें / Nearby Shops</li>
              <li>✅ मंडी भाव / Mandi Prices</li>
            </ul>
            <button className="plan-btn plan-btn-free">
              <span>🚀</span> शुरू करें / Get Started
            </button>
          </div>

          {/* Paid Version */}
          <div className="plan-card plan-premium" onClick={() => navigate('/coming-soon')}>
            <div className="plan-badge plan-badge-premium">⭐ प्रीमियम / PREMIUM</div>
            <div className="plan-icon">🌾</div>
            <h2 className="plan-title">
              <span className="plan-title-hi">प्रीमियम संस्करण</span>
              <span className="plan-title-en">Premium Version</span>
            </h2>
            <ul className="plan-features">
              <li>✅ सभी मुफ़्त सुविधाएं / All Free Features</li>
              <li>🔒 व्यक्तिगत फसल डॉक्टर / Personal Crop Doctor</li>
              <li>🔒 फसल बीमा सहायता / Crop Insurance Help</li>
              <li>🔒 मौसम अलर्ट / Weather Alerts</li>
              <li>🔒 विशेषज्ञ कॉल / Expert Consultation</li>
              <li>🔒 उन्नत रिपोर्ट / Advanced Reports</li>
            </ul>
            <div className="plan-price">
              <span className="plan-price-amount">₹99</span>
              <span className="plan-price-period">/महीना (per month)</span>
            </div>
            <button className="plan-btn plan-btn-premium">
              <span>⭐</span> प्रीमियम लें / Go Premium
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
