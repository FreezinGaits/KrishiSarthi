import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthProvider'
import { useTheme } from '../context/ThemeProvider'
import './ComingSoon.css'

export default function ComingSoon() {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const { theme, toggleTheme } = useTheme()

  if (!loading && !user) {
    navigate('/', { replace: true })
    return null
  }
  if (loading) return null

  return (
    <div className="coming-soon-page">
      {/* Background animation */}
      <div className="cs-particles">
        {[...Array(12)].map((_, i) => (
          <span key={i} className="cs-particle" style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 5}s`,
            animationDuration: `${4 + Math.random() * 6}s`,
          }} />
        ))}
      </div>

      <button className="theme-toggle cs-theme-toggle" onClick={toggleTheme} title="Toggle theme">
        {theme === 'light' ? '🌙' : '☀️'}
      </button>

      <div className="cs-container">
        <div className="cs-icon-wrapper">
          <span className="cs-icon">🚧</span>
        </div>

        <h1 className="cs-title">
          <span className="cs-title-hi">जल्द आ रहा है!</span>
          <span className="cs-title-en">Coming Soon!</span>
        </h1>

        <p className="cs-desc-hi">
          प्रीमियम संस्करण पर काम चल रहा है। हम जल्द ही यह सुविधा लेकर आएंगे।
        </p>
        <p className="cs-desc-en">
          We are working hard on the Premium version. Stay tuned for exciting features!
        </p>

        <div className="cs-features-preview">
          <h3>🔮 आने वाली सुविधाएं / Upcoming Features</h3>
          <div className="cs-feature-list">
            <div className="cs-feature">
              <span className="cs-feature-icon">👨‍⚕️</span>
              <span>व्यक्तिगत फसल डॉक्टर / Personal Crop Doctor</span>
            </div>
            <div className="cs-feature">
              <span className="cs-feature-icon">🌦️</span>
              <span>मौसम अलर्ट / Weather Alerts</span>
            </div>
            <div className="cs-feature">
              <span className="cs-feature-icon">📞</span>
              <span>विशेषज्ञ कॉल / Expert Consultation</span>
            </div>
            <div className="cs-feature">
              <span className="cs-feature-icon">🛡️</span>
              <span>फसल बीमा सहायता / Crop Insurance Help</span>
            </div>
          </div>
        </div>

        <button className="cs-btn-free" onClick={() => navigate('/dashboard')}>
          <span>🌱</span> मुफ़्त संस्करण इस्तेमाल करें / Use Free Version
        </button>

        <button className="cs-btn-back" onClick={() => navigate('/choose-plan')}>
          ← वापस जाएं / Go Back
        </button>
      </div>
    </div>
  )
}
